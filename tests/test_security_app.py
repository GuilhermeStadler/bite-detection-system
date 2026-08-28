import io
import re
import unittest
from unittest.mock import patch

from PIL import Image

import app as app_module


def csrf_from(response):
    body = response.get_data(as_text=True)
    match = re.search(r'id="csrfToken" name="_csrf_token" value="([^"]+)"', body)
    if not match:
        raise AssertionError("CSRF token not found")
    return match.group(1)


class SecurityAppTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
        app_module._rate_limit_buckets.clear()
        self.client = app_module.app.test_client()

    def token(self):
        return csrf_from(self.client.get("/"))

    def post_ask(self, data, token=None):
        headers = {}
        if token:
            headers["X-CSRFToken"] = token
        return self.client.post("/ask", data=data, headers=headers)

    def valid_payload(self, **overrides):
        payload = {
            "question": "dor e inchaco no pe",
            "city": "Campinas",
            "state": "SP",
            "bite_time": "30 minutos",
        }
        payload.update(overrides)
        return payload

    def image_file(self, name="bite.jpg"):
        image = Image.new("RGB", (80, 80), (180, 130, 120))
        stream = io.BytesIO()
        image.save(stream, format="JPEG")
        stream.seek(0)
        return stream, name

    def test_security_headers_are_set(self):
        response = self.client.get("/")

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_csrf_is_required_for_ask(self):
        response = self.post_ask({"question": "dor e inchaco"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("sessao expirou", response.get_json()["answer"].lower())

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    def test_question_length_limit_returns_400(self):
        response = self.post_ask({"question": "a" * 1001}, token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("excede o limite", response.get_json()["answer"])

    def test_invalid_upload_returns_friendly_error(self):
        data = self.valid_payload()
        data["image"] = (io.BytesIO(b"not an image"), "fake.jpg")
        response = self.post_ask(
            data,
            token=self.token(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Traceback", response.get_data(as_text=True))

    @patch("external_normalizers.normalize_user_text_with_gemini", lambda value: value)
    def test_rate_limit_returns_429(self):
        original_limit = app_module.RATE_LIMITS["ask"]
        app_module.RATE_LIMITS["ask"] = (2, 60)
        token = self.token()
        try:
            for _ in range(2):
                response = self.post_ask({"question": "dor e inchaco"}, token=token)
                self.assertNotEqual(response.status_code, 429)

            response = self.post_ask({"question": "dor e inchaco"}, token=token)
            self.assertEqual(response.status_code, 429)
            self.assertIn("muitas tentativas", response.get_json()["answer"].lower())
        finally:
            app_module.RATE_LIMITS["ask"] = original_limit
            app_module._rate_limit_buckets.clear()

    def test_missing_symptoms_blocks_analysis(self):
        response = self.post_ask(self.valid_payload(question=""), token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Preencha todos os campos obrigatórios", response.get_json()["answer"])

    def test_missing_city_blocks_analysis(self):
        response = self.post_ask(self.valid_payload(city=""), token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Preencha todos os campos obrigatórios", response.get_json()["answer"])

    def test_missing_state_blocks_analysis(self):
        response = self.post_ask(self.valid_payload(state=""), token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Preencha todos os campos obrigatórios", response.get_json()["answer"])

    def test_missing_bite_time_blocks_analysis(self):
        response = self.post_ask(self.valid_payload(bite_time=""), token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Preencha todos os campos obrigatórios", response.get_json()["answer"])

    def test_missing_image_blocks_backend_request(self):
        response = self.post_ask(self.valid_payload(), token=self.token())

        self.assertEqual(response.status_code, 400)
        self.assertIn("Preencha todos os campos obrigatórios", response.get_json()["answer"])

    @patch("app.bite_image_gate.evaluate_uploaded_image")
    def test_rejected_image_does_not_reach_species_classifier(self, gate):
        gate.return_value = {
            "checked": True,
            "model_available": True,
            "status": "rejected",
            "reason": "teste",
            "message": app_module.bite_image_gate.INVALID_IMAGE_MESSAGE,
        }
        data = self.valid_payload()
        data["image"] = self.image_file()

        response = self.post_ask(data, token=self.token())

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["needs_more_info"])
        self.assertEqual(body["analysis"]["identification_status"], "invalid_image")
        self.assertEqual(body["analysis"]["species_matches"], [])

    def test_inconclusive_image_is_not_converted_to_species(self):
        analysis = {"species_matches": [], "recommendations": []}
        image_analysis = {
            "image_received": True,
            "identification_status": "inconclusive",
            "class_name": "aranha_marrom",
            "class_label": "Aranha-marrom",
        }

        result = app_module.apply_image_evidence(analysis, image_analysis)

        self.assertEqual(result["species_matches"], [])
        self.assertEqual(result["identification_status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
