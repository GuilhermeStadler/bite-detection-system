

# Arquivo principal: define as rotas e trata as interações do usuário com a aplicação web.
from flask import Flask, jsonify, render_template, request, session
from flask_bootstrap import Bootstrap
from markupsafe import escape
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.utils import secure_filename

import os
import json
import logging
import re
import secrets
import tempfile
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlparse

import external_normalizers
import bite_image_gate
import symptom_ai

from db import get_db, init_app as init_db_app

app = Flask(__name__, template_folder='templates')

@app.route("/healthz", methods=["GET"])
def healthz():
    return "OK", 200

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 8 * 1024 * 1024))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', '').lower() in {'1', 'true', 'yes'}

Bootstrap(app)
init_db_app(app)

APP_ROOT = Path(__file__).resolve().parent
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_IMAGE_MIME_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
SAFE_IMAGE_FORMATS = {'PNG', 'JPEG', 'GIF', 'WEBP'}
MAX_IMAGE_BYTES = int(os.environ.get('MAX_IMAGE_BYTES', 5 * 1024 * 1024))
MAX_IMAGE_PIXELS = int(os.environ.get('MAX_IMAGE_PIXELS', 8_000_000))
MAX_IMAGE_DIMENSION = int(os.environ.get('MAX_IMAGE_DIMENSION', 4096))
PRIVATE_UPLOAD_DIR = Path(os.environ.get('PRIVATE_UPLOAD_DIR', APP_ROOT / 'instance' / 'uploads')).resolve()
MODEL_EVALUATION_PATH = os.path.join('models', 'venom_bite_evaluation.json')
FIELD_LIMITS = {
    'question': 1000,
    'report_context': 6000,
    'city': 80,
    'state': 80,
    'bite_time': 80,
    'answered_question_id': 120,
    'asked_questions': 2000,
    'image_analysis_context': 4000,
}
MAX_ASKED_QUESTIONS = 10
REQUIRED_ANALYSIS_MESSAGE = 'Preencha todos os campos obrigatórios antes de iniciar a análise.'
INCONCLUSIVE_IDENTIFICATION_MESSAGE = 'Não foi possível identificar uma espécie com evidência suficiente.'
INVALID_SYMPTOM_TEXT_MESSAGE = 'O texto informado não descreve sintomas, sinais locais ou contexto de picada suficiente.'
INVALID_INPUT_MESSAGE = 'Revise as informações enviadas antes de iniciar a análise.'
MIN_IMAGE_MODEL_OVERALL_ACCURACY = 0.70
RATE_LIMITS = {
    'ask': (20, 60),
    'post': (80, 60),
}
_rate_limit_buckets = defaultdict(deque)
_image_model_evaluation = None


class SecurityValidationError(ValueError):
    status_code = 400

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def is_truthy_env(name):
    return os.environ.get(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


def is_production():
    return os.environ.get('FLASK_ENV') == 'production' or os.environ.get('BITE_DETECTION_ENV') == 'production'


def wants_json_response():
    return request.path == '/ask' or request.accept_mimetypes.best == 'application/json'


def friendly_error(message, status_code=400):
    payload = {'ok': False, 'answer': message, 'error': message}
    if wants_json_response():
        return jsonify(payload), status_code
    return render_template('index.html', security_error=message), status_code


def client_key():
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    return (forwarded_for.split(',')[0].strip() or request.remote_addr or 'local')


def enforce_rate_limit(scope):
    limit, window_seconds = RATE_LIMITS[scope]
    now = time.monotonic()
    key = (scope, client_key())
    bucket = _rate_limit_buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def validate_csrf():
    expected = session.get('_csrf_token')
    supplied = request.headers.get('X-CSRFToken') or request.headers.get('X-CSRF-Token') or request.form.get('_csrf_token')
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        raise SecurityValidationError('Sua sessao expirou. Recarregue a pagina e tente novamente.', 400)


def validate_origin():
    if not is_production():
        return
    origin = request.headers.get('Origin') or request.headers.get('Referer')
    if not origin:
        return
    parsed = urlparse(origin)
    request_host = request.host.split(':')[0]
    if parsed.hostname and parsed.hostname != request_host:
        raise SecurityValidationError('Origem da requisicao nao autorizada.', 400)


def read_text_field(data, name, required=False, allowed_pattern=None):
    value = data.get(name, '')
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise SecurityValidationError('O campo {} precisa ser texto.'.format(name))
    value = value.strip()
    if required and not value:
        raise SecurityValidationError('O campo {} e obrigatorio.'.format(name))
    limit = FIELD_LIMITS[name]
    if len(value) > limit:
        raise SecurityValidationError('O campo {} excede o limite de {} caracteres.'.format(name, limit))
    if allowed_pattern and value and not allowed_pattern(value):
        raise SecurityValidationError('O campo {} contem formato invalido.'.format(name))
    return value


def parse_limited_json(raw_value, max_length, fallback):
    if not raw_value:
        return fallback
    if not isinstance(raw_value, str):
        raise SecurityValidationError('Formato de JSON invalido.')
    if len(raw_value) > max_length:
        raise SecurityValidationError('Dados enviados excedem o limite permitido.')
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError):
        return fallback


def validate_ask_payload(data):
    def is_simple_text(value):
        return all(ch.isprintable() or ch in '\r\n\t' for ch in value)

    return {
        'question': read_text_field(data, 'question', allowed_pattern=is_simple_text),
        'report_context': read_text_field(data, 'report_context', allowed_pattern=is_simple_text),
        'city': read_text_field(data, 'city'),
        'state': read_text_field(data, 'state'),
        'bite_time': read_text_field(data, 'bite_time', allowed_pattern=is_simple_text),
        'answered_question_id': read_text_field(data, 'answered_question_id'),
        'asked_questions_raw': read_text_field(data, 'asked_questions'),
        'image_analysis_context_raw': read_text_field(data, 'image_analysis_context'),
    }


def has_uploaded_image():
    uploaded_file = request.files.get('image')
    return bool(uploaded_file and uploaded_file.filename)


def has_valid_session_image_context(raw_context):
    parsed = parse_limited_json(raw_context, FIELD_LIMITS['image_analysis_context'], None)
    if not isinstance(parsed, dict):
        return False
    context_id = parsed.get('context_id')
    return bool(context_id and session.get('image_analysis_context_id') == context_id)


def is_followup_payload(payload, data):
    return bool(
        payload.get('answered_question_id')
        or parse_question_count(data.get('question_count')) > 0
        or has_valid_session_image_context(payload.get('image_analysis_context_raw'))
    )


def validate_required_analysis_inputs(payload, data):
    missing_text = [
        not payload.get('question'),
        not payload.get('city'),
        not payload.get('state'),
        not payload.get('bite_time'),
    ]
    if any(missing_text):
        raise SecurityValidationError(REQUIRED_ANALYSIS_MESSAGE)

    if is_followup_payload(payload, data):
        if not has_uploaded_image() and not has_valid_session_image_context(payload.get('image_analysis_context_raw')):
            raise SecurityValidationError(REQUIRED_ANALYSIS_MESSAGE)
        return

    if not has_uploaded_image():
        raise SecurityValidationError(REQUIRED_ANALYSIS_MESSAGE)


def safe_external_url(value, allowed_domains=None, allow_any_domain=False):
    raw_value = str(value or '').strip()
    if not raw_value:
        return ''
    if raw_value.startswith('//'):
        raw_value = 'https:' + raw_value
    elif '://' not in raw_value:
        raw_value = 'https://' + raw_value

    parsed = urlparse(raw_value)
    if parsed.scheme != 'https' or not parsed.netloc:
        return ''
    hostname = (parsed.hostname or '').lower()
    if not allow_any_domain:
        allowed = {domain.lower() for domain in (allowed_domains or [])}
        if hostname not in allowed and not any(hostname.endswith('.' + domain) for domain in allowed):
            return ''
    return raw_value


app.jinja_env.globals['csrf_token'] = csrf_token
app.jinja_env.globals['safe_external_url'] = safe_external_url


@app.before_request
def apply_request_guards():
    if request.method == 'POST':
        scope = 'ask' if request.path == '/ask' else 'post'
        if not enforce_rate_limit(scope):
            return friendly_error('Muitas tentativas em pouco tempo. Aguarde um momento e tente novamente.', 429)
        try:
            validate_origin()
            validate_csrf()
        except SecurityValidationError as exc:
            return friendly_error(str(exc), exc.status_code)


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://stackpath.bootstrapcdn.com; "
        "img-src 'self' data: blob: https://i5.walmartimages.com; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response


@app.errorhandler(RequestEntityTooLarge)
def handle_large_request(exc):
    return friendly_error('O arquivo ou formulario enviado e grande demais. Reduza o tamanho e tente novamente.', 413)


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    if isinstance(exc, HTTPException):
        return exc
    app.logger.exception('Erro interno tratado sem expor dados do usuario')
    return friendly_error('Nao foi possivel concluir a analise agora. Tente novamente em instantes.', 500)

def is_allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def remove_private_file(path):
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        app.logger.warning('Falha ao remover upload temporario', exc_info=True)


def validate_image_dimensions(image):
    width, height = image.size
    if width <= 0 or height <= 0:
        raise SecurityValidationError('A imagem enviada parece invalida.')
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise SecurityValidationError('A imagem excede a resolucao maxima permitida.')
    if width * height > MAX_IMAGE_PIXELS:
        raise SecurityValidationError('A imagem tem pixels demais para analise segura.')


def save_uploaded_image(uploaded_file):
    if not uploaded_file or uploaded_file.filename == '':
        return None
    if not is_allowed_image(uploaded_file.filename):
        raise SecurityValidationError('Envie uma imagem PNG, JPG, JPEG, GIF ou WEBP.')
    if uploaded_file.mimetype not in ALLOWED_IMAGE_MIME_TYPES:
        raise SecurityValidationError('O tipo de arquivo enviado nao parece ser uma imagem permitida.')

    uploaded_file.stream.seek(0, os.SEEK_END)
    file_size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    if file_size <= 0:
        raise SecurityValidationError('A imagem enviada esta vazia.')
    if file_size > MAX_IMAGE_BYTES:
        raise SecurityValidationError('A imagem excede o tamanho maximo permitido.', 413)

    PRIVATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = '.jpg'
    private_name = '{}{}'.format(uuid.uuid4().hex, suffix)
    image_path = PRIVATE_UPLOAD_DIR / secure_filename(private_name)

    try:
        with Image.open(uploaded_file.stream) as image:
            image.verify()
        uploaded_file.stream.seek(0)
        with Image.open(uploaded_file.stream) as image:
            if image.format not in SAFE_IMAGE_FORMATS:
                raise SecurityValidationError('Formato de imagem nao permitido.')
            validate_image_dimensions(image)
            sanitized = image.convert('RGB')
            sanitized.save(image_path, format='JPEG', quality=90, optimize=True)
    except SecurityValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise SecurityValidationError('Nao foi possivel validar a imagem enviada.')

    return str(image_path)


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
        'per_class': {
            item.get('class_name'): item
            for item in per_class
            if item.get('class_name')
        },
        'overall_accuracy': float(evaluation.get('overall_accuracy') or 0),
    }
    return _image_model_evaluation


def get_image_class_reliability(class_name):
    item = (load_image_model_evaluation().get('per_class') or {}).get(class_name) or {}
    test_images = int(item.get('test_images') or 0)
    accuracy = float(item.get('accuracy') or 0)

    if test_images <= 0:
        return 0.18
    if test_images < 3:
        return max(0.18, accuracy * 0.65)
    return max(0.12, min(0.92, accuracy))


def image_model_is_identification_grade():
    evaluation = load_image_model_evaluation()
    return float(evaluation.get('overall_accuracy') or 0) >= MIN_IMAGE_MODEL_OVERALL_ACCURACY


def is_dataset_image_prediction(prediction):
    source = (prediction.get('source') or '').lower()
    return 'dataset' in source


def calibrate_image_confidence(prediction):
    confidence = float(prediction.get('confidence') or 0)
    if is_dataset_image_prediction(prediction):
        return confidence

    reliability = get_image_class_reliability(prediction.get('class_name'))
    return confidence * (0.35 + (0.65 * reliability))


def analyze_uploaded_image(uploaded_file):
    image_path = save_uploaded_image(uploaded_file)
    if not image_path:
        return None

    image_analysis = {
        'image_received': True,
        'validity': None,
        'identification_status': 'not_run',
        'class_name': None,
        'class_label': None,
        'error': None,
    }

    try:
        image_validity = bite_image_gate.evaluate_uploaded_image(image_path)
        image_analysis['validity'] = image_validity
        if image_validity.get('status') == 'rejected':
            image_analysis['identification_status'] = 'invalid_image'
            image_analysis['error'] = image_validity.get('message') or bite_image_gate.INVALID_IMAGE_MESSAGE
            return image_analysis

        import model

        predictions = model.get_predictions(image_path, top_k=3)
        class_name = predictions[0]['class_name']
        identification_grade = image_model_is_identification_grade()
        image_analysis['class_name'] = class_name
        image_analysis['class_label'] = model.get_display_name(class_name)
        image_analysis['predictions'] = predictions
        top_confidence = float(predictions[0].get('confidence') or 0)
        second_confidence = float(predictions[1].get('confidence') or 0) if len(predictions) > 1 else 0
        image_analysis['confidence_margin'] = top_confidence - second_confidence
        image_analysis['is_uncertain'] = top_confidence < 0.45 or image_analysis['confidence_margin'] < 0.12
        image_analysis['model_identification_grade'] = identification_grade
        image_analysis['identification_status'] = 'candidate' if not image_analysis['is_uncertain'] and identification_grade else 'inconclusive'
        if not identification_grade:
            image_analysis['rejection_reason'] = 'modelo de espécies ainda não atingiu acurácia mínima para identificação automática'
        elif image_analysis['is_uncertain']:
            image_analysis['rejection_reason'] = 'predição visual sem separação suficiente entre classes'
    except Exception:
        app.logger.exception('Falha tecnica ao classificar imagem privada')
        image_analysis['error'] = 'A imagem foi recebida, mas a classificação visual ficou inconclusiva. A análise continuará usando os sintomas informados.'
        image_analysis['identification_status'] = 'inconclusive'
        image_analysis['rejection_reason'] = 'classificador de espécies indisponível ou falhou durante a execução'
    finally:
        remove_private_file(image_path)

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
    if image_analysis and image_analysis.get('identification_status') in {'invalid_image', 'error'}:
        analysis['species_matches'] = []
        analysis['recommendations'] = symptom_ai.build_recommendations([])
        analysis['identification_status'] = image_analysis.get('identification_status') or 'invalid_image'
        analysis['identification_message'] = image_analysis.get('error') or INCONCLUSIVE_IDENTIFICATION_MESSAGE
        return analysis

    if image_analysis and image_analysis.get('identification_status') != 'candidate':
        if not analysis.get('species_matches'):
            analysis['identification_status'] = image_analysis.get('identification_status') or 'inconclusive'
            analysis['identification_message'] = image_analysis.get('error') or INCONCLUSIVE_IDENTIFICATION_MESSAGE
        return analysis

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
            has_text_evidence = any(
                symptom_ai.has_species_diagnostic_evidence(match)
                for match in species_matches
            )
            if not is_dataset_image_prediction(prediction) and confidence < (0.22 if has_text_evidence else 0.28):
                continue
            if not has_text_evidence and not is_dataset_image_prediction(prediction):
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
    state = request.form.get('state', '')[:80]
    db = get_db()
    counties = db.execute('SELECT county FROM counties WHERE state= ?',(state,)).fetchall()        
    for entry in counties:
        county = escape(entry[0])
        ret += '<option value="{}">{}</option>'.format(county, county)
    return ret

def build_ai_response(analysis):
    species_matches = analysis.get('species_matches') or []
    recommendations = analysis.get('recommendations') or []
    symptoms = analysis.get('symptoms') or []
    image_analysis = analysis.get('image_analysis') or {}

    lines = []
    lines.append("Análise inicial da IA")
    if analysis.get('identification_status') in {'invalid_image', 'invalid_input', 'error'}:
        lines.append(analysis.get('identification_message') or bite_image_gate.INVALID_IMAGE_MESSAGE)
        lines.append("")
        lines.append("Aviso: isso é apenas apoio inicial e não substitui avaliação médica.")
        return "\n".join(lines)

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
        lines.append(analysis.get('identification_message') or "Análise inconclusiva: não encontrei uma espécie provável com evidência suficiente.")

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
    parsed = parse_limited_json(raw_value, FIELD_LIMITS['image_analysis_context'], None)
    if parsed is None:
        return None

    if not isinstance(parsed, dict):
        return None
    context_id = parsed.get('context_id')
    if not context_id or session.get('image_analysis_context_id') != context_id:
        return None

    session_context = session.get('image_analysis_context')
    if isinstance(session_context, dict):
        return session_context

    return None


def store_image_analysis_context(image_analysis):
    if not image_analysis:
        return image_analysis

    context_id = uuid.uuid4().hex
    image_analysis['context_id'] = context_id
    session['image_analysis_context_id'] = context_id
    session['image_analysis_context'] = image_analysis
    return image_analysis


def clear_image_analysis_context():
    session.pop('image_analysis_context_id', None)
    session.pop('image_analysis_context', None)


def parse_asked_questions(raw_value):
    parsed = parse_limited_json(raw_value, FIELD_LIMITS['asked_questions'], [])

    if not isinstance(parsed, list):
        return []

    questions = [str(item).strip()[:120] for item in parsed[:MAX_ASKED_QUESTIONS] if str(item).strip()]
    return questions


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


def is_triage_answer_payload(answered_question_id, answer_text):
    if not answered_question_id:
        return False
    if answered_question_id in symptom_ai.QUESTION_BY_ID or symptom_ai.get_species_triage_question(answered_question_id):
        parsed = symptom_ai.normalize_answer(answer_text)
        return parsed.get('answer') in {
            'yes',
            'no',
            'partial',
            'uncertain',
            'probably_yes',
            'probably_no',
            'not_yet',
            'unknown',
        }
    return False


def validate_symptom_text_semantics(text, answered_question_id=''):
    normalized = symptom_ai.normalize_text(text or '')
    if is_triage_answer_payload(answered_question_id, text):
        return {'valid': True, 'reason': 'resposta de triagem reconhecida'}

    if not normalized:
        return {'valid': False, 'reason': 'texto vazio'}

    compact = re.sub(r'[^a-z0-9]+', '', normalized)
    if len(compact) >= 4 and re.fullmatch(r'(.)\1{3,}', compact):
        return {'valid': False, 'reason': 'texto repetitivo sem significado clinico'}
    if len(compact) >= 6 and re.fullmatch(r'([a-z0-9]{1,3})\1{2,}', compact):
        return {'valid': False, 'reason': 'texto repetitivo sem significado clinico'}

    invalid_single_terms = {
        'teste',
        'test',
        'asdf',
        'qwerty',
        'peixe',
        'carro',
        'casa',
        'foto',
        'imagem',
    }
    if normalized in invalid_single_terms:
        return {'valid': False, 'reason': 'texto sem relacao com sintomas ou picada'}

    tokens = re.findall(r'[a-z0-9]+', normalized)
    if tokens and len(tokens) <= 2 and normalized not in {'dor', 'coceira', 'inchaco', 'vermelhidao', 'ardencia', 'queimacao'}:
        if not symptom_ai.extract_symptoms(normalized):
            return {'valid': False, 'reason': 'texto curto sem sinal clinico reconhecivel'}

    symptoms = symptom_ai.extract_symptoms(normalized)
    if symptoms:
        return {'valid': True, 'reason': 'sintomas reconhecidos'}

    clinical_profile = symptom_ai.extract_structured_clinical_data(normalized)
    diagnostic_fields = [
        field
        for field, entry in clinical_profile.items()
        if field not in {'time_since_bite', 'time_period', 'bite_location'}
        and float((entry or {}).get('confidence') or 0) >= 0.55
        and (entry or {}).get('status') != 'unknown'
    ]
    if diagnostic_fields:
        return {'valid': True, 'reason': 'dados clinicos reconhecidos'}

    related_terms = [
        'dor',
        'doendo',
        'coceira',
        'inchaco',
        'inchado',
        'vermelho',
        'vermelha',
        'vermelhidao',
        'ardencia',
        'queimacao',
        'roxo',
        'arroxeado',
        'bolha',
        'sangramento',
        'febre',
        'nausea',
        'vomito',
        'tontura',
        'fraqueza',
        'falta de ar',
        'picada',
        'mordida',
        'ferroada',
        'ferida',
        'lesao',
        'marca',
        'marcas',
        'pele',
        'braco',
        'braço',
        'mao',
        'mão',
        'perna',
        'pe',
        'pé',
        'coxa',
        'dedo',
        'rosto',
        'tronco',
        'cobra',
        'aranha',
        'escorpiao',
        'escorpião',
    ]
    if any(term in normalized for term in related_terms):
        return {'valid': True, 'reason': 'contexto de picada reconhecido'}

    return {'valid': False, 'reason': 'sem sintomas, sinais locais ou contexto de picada'}


def combine_validation_messages(messages):
    clean_messages = [message for message in messages if message]
    if not clean_messages:
        return INVALID_INPUT_MESSAGE
    return ' '.join(dict.fromkeys(clean_messages))


def normalize_free_text(value):
    try:
        return external_normalizers.normalize_user_text_with_gemini(value)
    except Exception:
        return value


def replace_last_text(value, old, new):
    if not value or not old or old == new:
        return value

    head, found, tail = value.rpartition(old)
    if not found:
        return value
    return "{}{}{}".format(head, new, tail)


def normalize_location(city, state):
    if not city:
        fallback = {}
        if state:
            fallback['state'] = state
            fallback['uf'] = state if len(state) == 2 else ''
            fallback['region'] = ''
        return fallback

    try:
        location = external_normalizers.normalize_ibge_location(city, state)
    except Exception:
        location = None
    if location:
        return location

    fallback = {}
    if city:
        fallback['city'] = city
    if state:
        fallback['state'] = state
        fallback['uf'] = state if len(state) == 2 else ''
        fallback['region'] = ''
    return fallback


def apply_input_metadata(analysis, original_texts, normalized_texts, location):
    analysis['input_normalization'] = {
        'question_original': original_texts.get('question', ''),
        'question_normalized': normalized_texts.get('question', ''),
        'report_context_original': original_texts.get('report_context', ''),
        'report_context_normalized': normalized_texts.get('report_context', ''),
    }

    if location:
        if location.get('city'):
            analysis['city'] = location['city']
        if location.get('state'):
            analysis['state'] = location['state']
        if location.get('uf'):
            analysis['uf'] = location['uf']
        if location.get('region'):
            analysis['region'] = location['region']
        analysis['location_normalization'] = {
            'city': location.get('city', ''),
            'state': location.get('state', ''),
            'uf': location.get('uf', ''),
            'region': location.get('region', ''),
        }

    return analysis


@app.route('/ask', methods=['POST'])
def ask():
    request_started_at = time.perf_counter()
    external_normalizers.reset_stats()
    timings = {
        'gemini_normalization': 0.0,
        'ibge_normalization': 0.0,
        'symptom_ai': 0.0,
        'total': 0.0,
    }

    try:
        data = request.get_json(silent=True) or request.form
        payload = validate_ask_payload(data)
        validate_required_analysis_inputs(payload, data)
        question = payload['question']
        report_context = payload['report_context']
        city = payload['city']
        state = payload['state']
        bite_time = payload['bite_time']
        answered_question_id = payload['answered_question_id']
        question_count = parse_question_count(data.get('question_count'))
        asked_questions = parse_asked_questions(payload['asked_questions_raw'])
        image_analysis = analyze_uploaded_image(request.files.get('image'))
        if not image_analysis:
            image_analysis = parse_image_analysis_context(payload['image_analysis_context_raw'])
        else:
            image_analysis = store_image_analysis_context(image_analysis)
    except SecurityValidationError as exc:
        return friendly_error(str(exc), exc.status_code)

    started_at = time.perf_counter()
    normalized_question = normalize_free_text(question)
    timings['gemini_normalization'] = time.perf_counter() - started_at
    text_validation = validate_symptom_text_semantics(normalized_question, answered_question_id)
    blocking_image_status = image_analysis and image_analysis.get('identification_status') == 'invalid_image'
    if blocking_image_status or not text_validation.get('valid'):
        validation_messages = []
        if blocking_image_status:
            validation_messages.append(image_analysis.get('error') or image_analysis.get('identification_message') or bite_image_gate.INVALID_IMAGE_MESSAGE)
        if not text_validation.get('valid'):
            validation_messages.append(INVALID_SYMPTOM_TEXT_MESSAGE)
        identification_message = combine_validation_messages(validation_messages)
        identification_status = 'invalid_input'
        if blocking_image_status and text_validation.get('valid'):
            identification_status = image_analysis.get('identification_status') or 'invalid_image'
        analysis = {
            'report_text': '',
            'symptoms': [],
            'city': city,
            'state': state,
            'region': '',
            'bite_location': '',
            'species_matches': [],
            'recommendations': symptom_ai.build_recommendations([]),
            'image_analysis': image_analysis,
            'identification_status': identification_status,
            'identification_message': identification_message,
            'text_validation': text_validation,
            'asked_questions': asked_questions,
        }
        clear_image_analysis_context()
        return jsonify({
            'ok': True,
            'needs_more_info': False,
            'answer': build_ai_response(analysis),
            'analysis': analysis,
        })

    normalized_report_context = replace_last_text(report_context, question, normalized_question)

    started_at = time.perf_counter()
    location = normalize_location(city, state)
    timings['ibge_normalization'] = time.perf_counter() - started_at

    report_parts = [normalized_report_context or normalized_question]
    interpreted_answer = symptom_ai.describe_triage_answer(answered_question_id, normalized_question)
    if interpreted_answer:
        report_parts.append(interpreted_answer)
    if location.get('city'):
        report_parts.append("Cidade: {}".format(location['city']))
    if location.get('state'):
        report_parts.append("Estado: {}".format(location['state']))
    if location.get('uf'):
        report_parts.append("UF: {}".format(location['uf']))
    if location.get('region'):
        report_parts.append("Região: {}".format(location['region']))
    if bite_time:
        report_parts.append("Tempo desde a picada: {}".format(bite_time))

    report_text = ". ".join(part for part in report_parts if part)
    if not report_text and not image_analysis:
        return jsonify({
            'ok': False,
            'answer': 'Digite uma pergunta, descreva os sintomas ou envie uma imagem para eu analisar.',
        }), 400

    started_at = time.perf_counter()
    analysis = symptom_ai.analyze_report(report_text)
    timings['symptom_ai'] = time.perf_counter() - started_at
    analysis = apply_input_metadata(
        analysis,
        {'question': question, 'report_context': report_context},
        {'question': normalized_question, 'report_context': normalized_report_context},
        location,
    )
    analysis = apply_image_evidence(analysis, image_analysis)
    analysis['image_analysis'] = image_analysis
    analysis['asked_questions'] = asked_questions
    timings['total'] = time.perf_counter() - request_started_at
    stats = external_normalizers.get_stats()
    analysis['performance'] = {
        'gemini_normalization_seconds': round(timings['gemini_normalization'], 4),
        'ibge_normalization_seconds': round(timings['ibge_normalization'], 4),
        'symptom_ai_seconds': round(timings['symptom_ai'], 4),
        'total_ask_seconds': round(timings['total'], 4),
        'gemini_calls': stats.get('gemini_calls', 0),
        'ibge_calls': stats.get('ibge_calls', 0),
    }
    app.logger.info(
        "Timing /ask: Gemini normalization: %.3fs (%s calls); IBGE normalization: %.3fs (%s calls); symptom_ai: %.3fs; total /ask: %.3fs",
        timings['gemini_normalization'],
        stats.get('gemini_calls', 0),
        timings['ibge_normalization'],
        stats.get('ibge_calls', 0),
        timings['symptom_ai'],
        timings['total'],
    )
    if is_refusal_answer(normalized_question):
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

    clear_image_analysis_context()
    return jsonify({
        'ok': True,
        'needs_more_info': False,
        'answer': build_ai_response(analysis),
        'analysis': analysis,
    })


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            report_text = read_text_field(request.form, 'question') if 'report_text' not in request.form else request.form.get('report_text', '').strip()
            if len(report_text) > FIELD_LIMITS['question']:
                raise SecurityValidationError('O relato excede o limite de {} caracteres.'.format(FIELD_LIMITS['question']))
            legacy_payload = {
                'question': report_text,
                'city': request.form.get('city') or request.form.get('county') or '',
                'state': request.form.get('state') or '',
                'bite_time': request.form.get('bite_time') or '',
                'answered_question_id': '',
                'image_analysis_context_raw': '',
            }
            if not all([legacy_payload['question'], legacy_payload['city'], legacy_payload['state'], legacy_payload['bite_time']]):
                raise SecurityValidationError(REQUIRED_ANALYSIS_MESSAGE)
            legacy_upload = request.files.get('file') or request.files.get('image')
            if not legacy_upload or not legacy_upload.filename:
                raise SecurityValidationError(REQUIRED_ANALYSIS_MESSAGE)
        except SecurityValidationError as exc:
            return friendly_error(str(exc), exc.status_code)
        if report_text and not legacy_upload:
            report_text = normalize_free_text(report_text)
            analysis = symptom_ai.analyze_report(report_text)
            return render_template('result.html', analysis=analysis)

        uploaded_file = legacy_upload
        state = request.form.get('state')
        county = request.form.get('county')

        if uploaded_file and uploaded_file.filename != '':
            image_path = None
            try:
                image_path = save_uploaded_image(uploaded_file)
                if not image_path:
                    return render_template('index.html')
                image_validity = bite_image_gate.evaluate_uploaded_image(image_path)
                if image_validity.get('status') == 'rejected':
                    analysis = {
                        'report_text': '',
                        'symptoms': [],
                        'city': legacy_payload['city'],
                        'state': legacy_payload['state'],
                        'region': '',
                        'bite_location': '',
                        'species_matches': [],
                        'recommendations': symptom_ai.build_recommendations([]),
                        'image_analysis': {
                            'image_received': True,
                            'validity': image_validity,
                            'identification_status': 'invalid_image',
                            'error': image_validity.get('message') or bite_image_gate.INVALID_IMAGE_MESSAGE,
                        },
                        'identification_status': 'invalid_image',
                        'identification_message': image_validity.get('message') or bite_image_gate.INVALID_IMAGE_MESSAGE,
                    }
                    return render_template('result.html', analysis=analysis)
                import model

                class_name = model.get_prediction(image_path)
            except SecurityValidationError as exc:
                return friendly_error(str(exc), exc.status_code)
            except Exception:
                app.logger.exception('Falha tecnica ao classificar upload legado')
                return friendly_error('A imagem foi recebida, mas a classificação visual ficou inconclusiva. Tente uma nova análise descrevendo os sintomas com mais detalhes.', 400)
            finally:
                remove_private_file(image_path)
            result = {
                'class_name': class_name,
                'image_received': True,
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
    app.run(debug=is_truthy_env('FLASK_DEBUG'))
