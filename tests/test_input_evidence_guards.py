import io
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

import app as app_module
import bite_image_gate
import symptom_ai


def csrf_from(response):
    body = response.get_data(as_text=True)
    marker = 'id="csrfToken" name="_csrf_token" value="'
    start = body.find(marker)
    if start == -1:
        raise AssertionError("CSRF token not found")
    start += len(marker)
    end = body.find('"', start)
    return body[start:end]


class InputEvidenceGuardTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        app_module._rate_limit_buckets.clear()
        self.client = app_module.app.test_client()

    def token(self):
        return csrf_from(self.client.get("/"))

    def post_ask(self, data):
        return self.client.post("/ask", data=data, headers={"X-CSRFToken": self.token()})

    def image_file(self, color=(180, 130, 120), name="upload.jpg"):
        image = Image.new("RGB", (96, 96), color)
        stream = io.BytesIO()
        image.save(stream, format="JPEG")
        stream.seek(0)
        return stream, name

    def valid_payload(self, question="dor intensa, inchaço e vermelhidão no pé"):
        return {
            "question": question,
            "city": "Curitiba",
            "state": "PR",
            "bite_time": "1 hora",
            "image": self.image_file(),
        }

    def valid_image_analysis(self, status="inconclusive"):
        return {
            "image_received": True,
            "validity": {"checked": True, "model_available": True, "status": "passed"},
            "identification_status": status,
            "class_name": None,
            "class_label": None,
        }

    def evaluate_pil_image(self, image, suffix=".jpg"):
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            image.save(handle.name)
            return bite_image_gate.evaluate_uploaded_image(handle.name)

    def skin_image(self, size=(160, 120), base=(196, 142, 118)):
        image = Image.new("RGB", size, base)
        for x in range(size[0]):
            for y in range(size[1]):
                image.putpixel((x, y), (base[0] + (x % 9), base[1] + (y % 7), base[2] + ((x + y) % 5)))
        return image

    def bruised_bite_image(self, size=(160, 120)):
        image = self.skin_image(size)
        draw = ImageDraw.Draw(image, "RGBA")
        center = (size[0] // 2, size[1] // 2)
        draw.ellipse((center[0] - 42, center[1] - 30, center[0] + 42, center[1] + 30), fill=(115, 55, 100, 115))
        draw.ellipse((center[0] - 7, center[1] - 7, center[0] + 7, center[1] + 7), fill=(28, 18, 18, 235))
        return image

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_dark_image_and_invalid_symptoms_report_both_problems(self, analyze_image):
        analyze_image.return_value = {
            "image_received": True,
            "validity": {"checked": True, "status": "rejected"},
            "identification_status": "invalid_image",
            "error": bite_image_gate.INVALID_IMAGE_MESSAGE,
        }
        response = self.post_ask(self.valid_payload(question="peixe"))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["species_matches"], [])
        self.assertEqual(body["analysis"]["identification_status"], "invalid_input")
        self.assertIn("imagem", body["answer"].lower())
        self.assertIn("texto informado", body["answer"].lower())

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_valid_image_with_invalid_symptom_text_is_rejected(self, analyze_image):
        analyze_image.return_value = self.valid_image_analysis(status="candidate")
        response = self.post_ask(self.valid_payload(question="carro"))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["species_matches"], [])
        self.assertIn("texto informado", body["answer"].lower())

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_valid_image_with_repeated_letters_is_rejected(self, analyze_image):
        analyze_image.return_value = self.valid_image_analysis(status="candidate")
        response = self.post_ask(self.valid_payload(question="aaaaaaaaaaaa"))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["species_matches"], [])
        self.assertIn("texto informado", body["answer"].lower())

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    def test_clear_random_image_with_valid_symptoms_is_rejected_when_gate_is_untrained(self):
        image = Image.new("RGB", (96, 96), (40, 120, 210))
        stream = io.BytesIO()
        image.save(stream, format="JPEG")
        stream.seek(0)
        data = self.valid_payload(question="dor intensa e inchaço no pé")
        data["image"] = (stream, "object.jpg")
        response = self.post_ask(data)

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["identification_status"], "invalid_image")
        self.assertEqual(body["analysis"]["species_matches"], [])

    def test_clear_random_image_is_rejected_without_trained_validity_model(self):
        image = Image.new("RGB", (128, 128), (35, 120, 205))
        for x in range(20, 108):
            for y in range(20, 108):
                image.putpixel((x, y), (30, 100 + (x % 50), 180 + (y % 40)))
        result = self.evaluate_pil_image(image)

        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["model_available"])

    def test_room_scene_with_person_fragment_is_rejected(self):
        image = Image.new("RGB", (320, 240), (218, 214, 198))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 70, 90, 145), fill=(20, 45, 55))
        draw.rectangle((230, 20, 315, 220), fill=(82, 60, 48))
        draw.ellipse((135, 195, 185, 250), fill=(105, 80, 62))
        result = self.evaluate_pil_image(image)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["debug"]["blocking_rule"], "scene_without_skin_change")

    def test_skin_without_visible_bite_is_visually_inconclusive(self):
        result = self.evaluate_pil_image(self.skin_image())

        self.assertEqual(result["status"], "inconclusive")
        self.assertFalse(result["model_available"])

    def test_purple_area_with_central_dark_point_passes_visual_gate(self):
        result = self.evaluate_pil_image(self.bruised_bite_image())

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["debug"]["blocking_rule"], "none")
        self.assertGreaterEqual(result["debug"]["visual_change_score"], 0.018)

    def test_discreet_redness_is_at_least_visually_inconclusive(self):
        image = self.skin_image()
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse((58, 38, 102, 82), fill=(180, 70, 62, 62))
        result = self.evaluate_pil_image(image)

        self.assertIn(result["status"], {"passed", "inconclusive"})

    def test_small_mark_on_skin_is_at_least_visually_inconclusive(self):
        image = self.skin_image()
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse((74, 54, 86, 66), fill=(45, 25, 22, 220))
        result = self.evaluate_pil_image(image)

        self.assertIn(result["status"], {"passed", "inconclusive"})

    def test_cropped_possible_bite_passes_visual_gate(self):
        result = self.evaluate_pil_image(self.bruised_bite_image(size=(96, 80)))

        self.assertEqual(result["status"], "passed")

    def test_screenshot_with_affected_region_passes_by_content_not_filename(self):
        screenshot = Image.new("RGB", (360, 220), (28, 28, 32))
        lesion = self.bruised_bite_image(size=(160, 120))
        screenshot.paste(lesion, (80, 48))
        result = self.evaluate_pil_image(screenshot, suffix=".png")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["debug"]["blocking_rule"], "none")

    def test_dark_image_still_rejected(self):
        image = Image.new("RGB", (128, 128), (8, 8, 8))
        result = self.evaluate_pil_image(image)

        self.assertEqual(result["status"], "rejected")

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_informal_text_with_recognized_symptoms_is_accepted(self, analyze_image):
        analyze_image.return_value = self.valid_image_analysis(status="inconclusive")
        response = self.post_ask(self.valid_payload(question="dor de cabeca pklr, dor moderada, queimacao"))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertNotEqual(body["analysis"].get("identification_status"), "invalid_input")
        self.assertIn("dor de cabeça", body["analysis"]["symptoms"])
        self.assertIn("ardor", body["analysis"]["symptoms"])

    def test_unknown_answers_do_not_create_species(self):
        report = (
            "Resposta clinica: question_id=urgent_breathing_standing target_field=breathing_standing "
            "answer=unknown normalized_value=unknown confidence=0. "
            "Cidade: Curitiba. Estado: Parana. Região: Sul. Tempo desde a picada: 1 hora."
        )
        analysis = symptom_ai.analyze_report(report)

        self.assertEqual(analysis["species_matches"], [])

    def test_all_unknown_answers_with_valid_fields_do_not_create_species(self):
        report = (
            "Picada no braço. Cidade: Curitiba. Estado: Parana. Região: Sul. Tempo desde a picada: 1 hora. "
            "Resposta clinica: question_id=urgent_breathing_standing target_field=breathing_standing "
            "answer=unknown normalized_value=unknown confidence=0. "
            "Resposta clinica: question_id=urgent_systemic_worsening target_field=systemic_symptoms "
            "answer=unknown normalized_value=unknown confidence=0. "
            "Resposta clinica: question_id=bleeding target_field=bleeding "
            "answer=unknown normalized_value=unknown confidence=0."
        )
        analysis = symptom_ai.analyze_report(report)

        self.assertEqual(analysis["species_matches"], [])

    def test_location_and_time_alone_do_not_create_species(self):
        analysis = symptom_ai.analyze_report("Cidade: Curitiba. Estado: Parana. Região: Sul. Tempo desde a picada: 1 hora.")

        self.assertEqual(analysis["symptoms"], [])
        self.assertEqual(analysis["species_matches"], [])

    def test_region_does_not_appear_as_considered_sign(self):
        analysis = symptom_ai.analyze_report("Região Sul. Cidade Curitiba. Estado PR. Dor intensa e inchaço no pé.")

        for match in analysis["species_matches"]:
            reasons = match.get("reasons") or []
            self.assertFalse(any("região" in reason.lower() for reason in reasons))

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_complete_true_case_still_continues(self, analyze_image):
        analyze_image.return_value = self.valid_image_analysis(status="inconclusive")
        response = self.post_ask(self.valid_payload(
            question="mordida no pé, dor forte, inchaço aumentando, pele roxa e sangramento"
        ))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["analysis"]["species_matches"])
        self.assertIn(body["analysis"]["species_matches"][0]["animal"], {"jararaca", "surucucu"})

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_image_model_error_does_not_block_valid_text(self, analyze_image):
        analyze_image.return_value = {
            "image_received": True,
            "identification_status": "inconclusive",
            "error": "A imagem foi recebida, mas a classificação visual ficou inconclusiva.",
        }
        response = self.post_ask(self.valid_payload(
            question="mordida no pé, dor forte, inchaço aumentando, pele roxa e sangramento"
        ))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["analysis"]["species_matches"])
        self.assertNotEqual(body["analysis"].get("identification_status"), "invalid_input")

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    @patch("app.analyze_uploaded_image")
    def test_image_model_error_with_invalid_text_is_rejected_by_text_guard(self, analyze_image):
        analyze_image.return_value = {
            "image_received": True,
            "identification_status": "inconclusive",
            "error": "A imagem foi recebida, mas a classificação visual ficou inconclusiva.",
        }
        response = self.post_ask(self.valid_payload(question="peixe"))

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["species_matches"], [])
        self.assertEqual(body["analysis"]["identification_status"], "invalid_input")
        self.assertIn("texto informado", body["answer"].lower())


if __name__ == "__main__":
    unittest.main()
