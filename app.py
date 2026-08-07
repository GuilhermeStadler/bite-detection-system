

# Arquivo principal: define as rotas e trata as interações do usuário com a aplicação web.
from flask import Flask, jsonify, render_template, request
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename

import os
import json
import uuid
import symptom_ai

from db import get_db, init_app as init_db_app

app = Flask(__name__, template_folder='templates')

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

Bootstrap(app)
init_db_app(app)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MODEL_EVALUATION_PATH = os.path.join('models', 'venom_bite_evaluation.json')
_image_model_evaluation = None

def is_allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def load_image_model_evaluation():
    global _image_model_evaluation

    if _image_model_evaluation is not None:
        return _image_model_evaluation

    try:
        with open(MODEL_EVALUATION_PATH, 'r', encoding='utf-8') as evaluation_file:
            evaluation = json.load(evaluation_file)
    except (OSError, ValueError):
        _image_model_evaluation = {}
        return _image_model_evaluation

    per_class = evaluation.get('per_class') or []
    _image_model_evaluation = {
        item.get('class_name'): item
        for item in per_class
        if item.get('class_name')
    }
    return _image_model_evaluation


def get_image_class_reliability(class_name):
    item = load_image_model_evaluation().get(class_name) or {}
    test_images = int(item.get('test_images') or 0)
    accuracy = float(item.get('accuracy') or 0)

    if test_images <= 0:
        return 0.18
    if test_images < 3:
        return max(0.18, accuracy * 0.65)
    return max(0.12, min(0.92, accuracy))


def is_dataset_image_prediction(prediction):
    source = (prediction.get('source') or '').lower()
    return 'dataset' in source


def calibrate_image_confidence(prediction):
    confidence = float(prediction.get('confidence') or 0)
    if is_dataset_image_prediction(prediction):
        return confidence

    reliability = get_image_class_reliability(prediction.get('class_name'))
    return confidence * (0.35 + (0.65 * reliability))


def save_uploaded_image(uploaded_file):
    if not uploaded_file or uploaded_file.filename == '' or not is_allowed_image(uploaded_file.filename):
        return None

    upload_dir = os.path.join('static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = secure_filename(uploaded_file.filename)
    unique_name = '{}_{}'.format(uuid.uuid4().hex[:12], safe_name)
    image_path = os.path.join(upload_dir, unique_name)
    uploaded_file.save(image_path)
    return image_path


def analyze_uploaded_image(uploaded_file):
    image_path = save_uploaded_image(uploaded_file)
    if not image_path:
        return None

    image_analysis = {
        'image_path': image_path.replace(os.sep, '/'),
        'class_name': None,
        'class_label': None,
        'error': None,
    }

    try:
        import model

        predictions = model.get_predictions(image_path, top_k=3)
        class_name = predictions[0]['class_name']
        image_analysis['class_name'] = class_name
        image_analysis['class_label'] = model.get_display_name(class_name)
        image_analysis['predictions'] = predictions
        top_confidence = float(predictions[0].get('confidence') or 0)
        second_confidence = float(predictions[1].get('confidence') or 0) if len(predictions) > 1 else 0
        image_analysis['confidence_margin'] = top_confidence - second_confidence
        image_analysis['is_uncertain'] = top_confidence < 0.45 or image_analysis['confidence_margin'] < 0.12
    except Exception as exc:
        image_analysis['error'] = 'Não foi possível classificar a imagem agora: {}'.format(exc)

    return image_analysis


def build_species_match_from_image(class_name, confidence=1.0):
    for species in symptom_ai.load_species_knowledge():
        if species.get('animal') != class_name:
            continue

        confidence_percent = int(round(float(confidence or 0) * 100))
        return {
            'display_name': species.get('display_name', ''),
            'animal': species.get('animal', ''),
            'popular_name': species.get('popular_name', ''),
            'category': species.get('category', ''),
            'severity': species.get('severity', ''),
            'risk_level': species.get('risk_level', ''),
            'guidance': species.get('guidance', ''),
            'dont_do': species.get('dont_do', ''),
            'alert_signs': ', '.join(species.get('alert_signs', [])),
            'symptom_onset': species.get('symptom_onset', ''),
            'visual_profile': species.get('visual_profile', {}),
            'affected_regions': ', '.join(species.get('affected_regions', [])),
            'accident_sites': ', '.join(species.get('accident_sites', [])),
            'regions': ', '.join(species.get('regions', [])),
            'environment': ', '.join(species.get('environment', [])),
            'symptoms_reference': ', '.join(species.get('symptoms', [])),
            'score': 8,
            'matched_features': ['imagem integrada'],
            'reasons': ['classificacao por imagem: {}%'.format(confidence_percent)],
            'reason_text': 'classificacao por imagem: {}%'.format(confidence_percent),
            'probability': confidence_percent,
            'image_confidence': confidence_percent,
        }

    return None


def apply_image_evidence(analysis, image_analysis):
    if not image_analysis or not image_analysis.get('class_name'):
        return analysis

    predictions = image_analysis.get('predictions') or [
        {'class_name': image_analysis['class_name'], 'confidence': 1.0}
    ]
    species_matches = analysis.get('species_matches') or []

    is_uncertain = bool(image_analysis.get('is_uncertain'))
    confidence_margin = float(image_analysis.get('confidence_margin') or 0)

    for rank, prediction in enumerate(predictions):
        class_name = prediction.get('class_name')
        raw_confidence = float(prediction.get('confidence') or 0)
        confidence = calibrate_image_confidence(prediction)
        prediction['calibrated_confidence'] = confidence
        if rank > 0 and confidence < 0.08:
            continue

        if rank == 0 and confidence < 0.12 and not is_dataset_image_prediction(prediction):
            continue

        image_weight_scale = 8 if is_dataset_image_prediction(prediction) else 5
        image_weight = max(1, int(round(confidence * image_weight_scale)))
        if rank > 0:
            image_weight = max(1, image_weight - rank)
        if is_uncertain or confidence_margin < 0.12:
            image_weight = max(1, image_weight // 2)
        matched = False

        for match in species_matches:
            if match.get('animal') == class_name:
                matched = True
                match['score'] = match.get('score', 0) + image_weight
                reasons = match.get('reasons') or []
                reasons.append('classificacao por imagem: {}%'.format(int(round(raw_confidence * 100))))
                match['reasons'] = list(dict.fromkeys(reasons))
                match['reason_text'] = ', '.join(match['reasons'])
                match['image_confidence'] = int(round(raw_confidence * 100))
                match['image_calibrated_confidence'] = int(round(confidence * 100))
                break

        if not matched:
            has_text_evidence = bool(analysis.get('symptoms')) or bool(analysis.get('bite_location'))
            if not is_dataset_image_prediction(prediction) and confidence < (0.22 if has_text_evidence else 0.28):
                continue
            image_match = build_species_match_from_image(class_name, confidence)
            if image_match:
                image_match['score'] = image_weight
                image_match['image_confidence'] = int(round(raw_confidence * 100))
                image_match['image_calibrated_confidence'] = int(round(confidence * 100))
                species_matches.append(image_match)

    species_matches.sort(key=lambda item: (-item.get('score', 0), item.get('display_name', '')))
    top_matches = species_matches[:5]

    if top_matches:
        weighted_scores = [max(1, item.get('score', 1)) ** 3 for item in top_matches]
        total_weight = sum(weighted_scores)
        probabilities = [int(round((score / total_weight) * 100)) for score in weighted_scores]
        diff = 100 - sum(probabilities)
        if probabilities:
            probabilities[0] += diff
        for index, item in enumerate(top_matches):
            item['probability'] = max(0, probabilities[index])

    analysis['species_matches'] = top_matches
    analysis['recommendations'] = symptom_ai.build_recommendations(top_matches)
    return analysis


# Rota usada pelo Ajax para atualizar os municípios de acordo com o estado.
@app.route('/state', methods=['POST'])
def state():
    ret = ''
    state = request.form['state']
    db = get_db()
    counties = db.execute('SELECT county FROM counties WHERE state= ?',(state,)).fetchall()        
    for entry in counties:
        ret += '<option value="{}">{}</option>'.format(entry[0],entry[0])
    return ret

def build_ai_response(analysis):
    species_matches = analysis.get('species_matches') or []
    recommendations = analysis.get('recommendations') or []
    symptoms = analysis.get('symptoms') or []
    image_analysis = analysis.get('image_analysis') or {}

    lines = []
    lines.append("Análise inicial da IA")
    recognized = []
    if symptoms:
        recognized.append("sintomas: {}".format(", ".join(symptoms)))
    if analysis.get('city'):
        recognized.append("cidade: {}".format(analysis['city']))
    if analysis.get('state'):
        recognized.append("estado: {}".format(analysis['state']))
    if analysis.get('region'):
        recognized.append("região: {}".format(analysis['region']))
    if analysis.get('bite_location'):
        recognized.append("local da picada: {}".format(analysis['bite_location']))

    if recognized:
        lines.append("Foi identificado " + "; ".join(recognized) + ".")
    elif image_analysis and image_analysis.get('class_label'):
        lines.append("Análise baseada somente na imagem enviada. Para aumentar a precisão, informe também sintomas, local da picada, cidade, estado e tempo desde o ocorrido.")
    else:
        lines.append("Não consegui reconhecer todos os dados principais. Descreva sintomas, local da picada, cidade, estado e há quanto tempo aconteceu.")

    if analysis.get('urgent_triage'):
        lines.append("")
        lines.append("Atenção: seu relato tem sinal de alerta. Procure atendimento médico imediatamente.")

    if species_matches:
        lines.append("")
        lines.append("Possibilidades mais compatíveis:")
        for match in species_matches[:3]:
            reason_text = match.get('reason_text') or "sinais descritos"
            lines.append(
                "- {}: maior compatibilidade dentro do sistema, gravidade {}, risco {}, por causa de {}.".format(
                    match.get('popular_name'),
                    match.get('severity'),
                    match.get('risk_level') or 'não informado',
                    reason_text,
                )
            )
            if match.get('alert_signs'):
                lines.append("  Sinais de alerta: {}.".format(match.get('alert_signs')))
    else:
        lines.append("")
        lines.append("Não encontrei uma espécie provável com confiança usando apenas esse relato.")

    if recommendations:
        lines.append("")
        lines.append("O que fazer agora:")
        for recommendation in recommendations:
            lines.append("- {}".format(recommendation))

    lines.append("")
    lines.append("Aviso: isso é apenas apoio inicial e não substitui avaliação médica.")
    return "\n".join(lines)


def build_triage_response(question):
    return "Pergunta da IA:\n{}".format(question)


def parse_question_count(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_image_analysis_context(raw_value):
    if not raw_value:
        return None

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return None

    return parsed if isinstance(parsed, dict) else None


def parse_asked_questions(raw_value):
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    return [str(item).strip() for item in parsed if str(item).strip()]


def is_refusal_answer(value):
    normalized = symptom_ai.normalize_text(value or "")
    refusal_terms = [
        "nao quero responder",
        "n quero responder",
        "nao vou responder",
        "nao sei responder",
        "nao sei",
        "sem resposta",
        "quero pular",
        "pular",
    ]
    return any(term in normalized for term in refusal_terms)


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or request.form
    question = (data.get('question') or '').strip()
    report_context = (data.get('report_context') or '').strip()
    city = (data.get('city') or '').strip()
    state = (data.get('state') or '').strip()
    bite_time = (data.get('bite_time') or '').strip()
    answered_question_id = (data.get('answered_question_id') or '').strip()
    question_count = parse_question_count(data.get('question_count'))
    asked_questions = parse_asked_questions(data.get('asked_questions'))
    image_analysis = analyze_uploaded_image(request.files.get('image'))
    if not image_analysis:
        image_analysis = parse_image_analysis_context(data.get('image_analysis_context'))

    report_parts = [report_context or question]
    interpreted_answer = symptom_ai.describe_triage_answer(answered_question_id, question)
    if interpreted_answer:
        report_parts.append(interpreted_answer)
    if city:
        report_parts.append("Cidade: {}".format(city))
    if state:
        report_parts.append("Estado: {}".format(state))
    if bite_time:
        report_parts.append("Tempo desde a picada: {}".format(bite_time))

    report_text = ". ".join(part for part in report_parts if part)
    if not report_text and not image_analysis:
        return jsonify({
            'ok': False,
            'answer': 'Digite uma pergunta, descreva os sintomas ou envie uma imagem para eu analisar.',
        }), 400

    analysis = symptom_ai.analyze_report(report_text)
    analysis = apply_image_evidence(analysis, image_analysis)
    analysis['image_analysis'] = image_analysis
    analysis['asked_questions'] = asked_questions
    if is_refusal_answer(question):
        question_count = 5
    triage_payload = symptom_ai.build_triage_question_payload(
        analysis,
        question_count=question_count,
        max_questions=5,
        asked_questions=asked_questions,
    )

    if triage_payload:
        triage_question = triage_payload['text']
        return jsonify({
            'ok': True,
            'needs_more_info': True,
            'answer': build_triage_response(triage_question),
            'triage_question': triage_question,
            'triage_question_id': triage_payload.get('id'),
            'triage_options': triage_payload.get('options', []),
            'triage_answer_type': triage_payload.get('answer_type'),
            'question_count': question_count + 1,
            'analysis': analysis,
        })

    return jsonify({
        'ok': True,
        'needs_more_info': False,
        'answer': build_ai_response(analysis),
        'analysis': analysis,
    })


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        report_text = request.form.get('report_text', '').strip()
        if report_text:
            analysis = symptom_ai.analyze_report(report_text)
            return render_template('result.html', analysis=analysis)

        uploaded_file = request.files.get('file')
        state = request.form.get('state')
        county = request.form.get('county')

        if uploaded_file and uploaded_file.filename != '':
            import model

            image_path = save_uploaded_image(uploaded_file)
            if not image_path:
                return render_template('index.html')
            class_name = model.get_prediction(image_path)
            result = {
                'class_name': class_name,
                'image_path': image_path.replace(os.sep, '/'),
            }

            db = get_db()
            companies = db.execute('SELECT * FROM companies WHERE state=? AND county= ?',(state,county,)).fetchall()
            situations_categories = db.execute('SELECT situation,category FROM bug_category WHERE bug= ?',(class_name,)).fetchall()
            info = db.execute('SELECT * FROM info WHERE bug = ?',(class_name,)).fetchall()

            conditions = []
            for row in situations_categories:
                category = row[1]
                product = db.execute('SELECT * FROM products WHERE category = ? ORDER BY RANDOM() LIMIT 1',(category,)).fetchall()
                conditions.append([row[0],category,product])

            return render_template('result.html', info=info, result=result, companies=companies, conditions=conditions)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug = True)
