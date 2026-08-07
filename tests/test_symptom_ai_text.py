import unittest

import symptom_ai


SAMPLE_REPORT = (
    "Encontrei uma pequena marca na coxa durante a manhã. "
    "A dor era fraca, mas agora está mais intensa. "
    "A pele ficou arroxeada e apareceu uma bolha pequena. "
    "Estou me sentindo cansado."
)


class SymptomAiTextTests(unittest.TestCase):
    def test_required_report_extraction(self):
        profile = symptom_ai.extract_structured_clinical_data(SAMPLE_REPORT)

        self.assertEqual(profile["bite_location"]["value"], "coxa")
        self.assertEqual(profile["time_period"]["value"], "manhã")
        self.assertEqual(profile["initial_pain"]["value"], "fraca")
        self.assertEqual(profile["pain_progression"]["value"], "aumentando")
        self.assertIs(profile["purple_skin"]["value"], True)
        self.assertIs(profile["blister"]["value"], True)
        self.assertIs(profile["fatigue"]["value"], True)

    def test_informal_language_extraction(self):
        text = "Ficou roxo, esta queimando, me deu moleza e nao consigo respirar direito."
        profile = symptom_ai.extract_structured_clinical_data(text)

        self.assertIs(profile["purple_skin"]["value"], True)
        self.assertIs(profile["burning"]["value"], True)
        self.assertIs(profile["weakness"]["value"], True)
        self.assertIs(profile["shortness_of_breath"]["value"], True)

    def test_semantic_deduplication_blocks_answered_fields(self):
        analysis = symptom_ai.analyze_report(SAMPLE_REPORT)
        payload = symptom_ai.build_triage_question_payload(analysis, asked_questions=[])
        ignored = {
            item["question_id"]
            for item in analysis["question_selection_log"]["ignored_answered"]
        }

        self.assertEqual(payload["category"], "urgency")
        self.assertIn("pain_delayed_worsening", ignored)
        self.assertIn("purple_skin", ignored)
        self.assertIn("blister", ignored)
        self.assertNotIn(payload["target_field"], {"pain_progression", "purple_skin", "blister", "bite_location", "fatigue"})

    def test_swelling_progression_equivalent_questions_are_blocked(self):
        text = "O inchaco esta subindo pela perna."
        analysis = symptom_ai.analyze_report(text)
        payload = symptom_ai.build_triage_question_payload(
            analysis,
            asked_questions=["urgent_breathing_standing", "urgent_systemic_worsening", "urgent_vulnerable_person"],
        )

        self.assertNotEqual(payload["question_id"], "swelling_progression")
        self.assertTrue(symptom_ai.clinical_field_answered(analysis["clinical_profile"], "swelling_progression"))

    def test_negative_answer_penalty_is_moderate(self):
        species = {"animal": "armadeira"}
        marker = "Resposta clinica: question_id=immediate_severe_pain target_field=pain_onset answer=no normalized_value=false confidence=0.75."
        score = symptom_ai.score_question_answer_markers(marker, species, [])

        self.assertGreater(score, -6)
        self.assertLess(score, 0)

    def test_unknown_answer_does_not_change_score(self):
        species = {"animal": "armadeira"}
        marker = "Resposta clinica: question_id=immediate_severe_pain target_field=pain_onset answer=unknown normalized_value=unknown confidence=0."

        self.assertEqual(symptom_ai.score_question_answer_markers(marker, species, []), 0)

    def test_question_selection_changes_with_ranking(self):
        asked_urgency = ["urgent_breathing_standing", "urgent_systemic_worsening", "urgent_vulnerable_person"]
        spider_analysis = {
            "clinical_profile": {},
            "species_matches": [
                {"animal": "aranha_marrom", "score": 20},
                {"animal": "jararaca", "score": 18},
                {"animal": "surucucu", "score": 12},
            ],
        }
        neuro_analysis = {
            "clinical_profile": {"pain_onset": {"value": "imediato", "confidence": 0.8}},
            "species_matches": [
                {"animal": "viuva_negra", "score": 20},
                {"animal": "armadeira", "score": 18},
                {"animal": "escorpiao_amarelo", "score": 17},
            ],
        }

        spider_question = symptom_ai.build_triage_question_payload(spider_analysis, asked_questions=asked_urgency)
        neuro_question = symptom_ai.build_triage_question_payload(neuro_analysis, asked_questions=asked_urgency)

        self.assertNotEqual(spider_question["question_id"], neuro_question["question_id"])

    def test_urgency_questions_have_priority(self):
        analysis = symptom_ai.analyze_report("Dor e inchaco no pe.")
        payload = symptom_ai.build_triage_question_payload(analysis, asked_questions=[])

        self.assertEqual(payload["category"], "urgency")

    def test_early_stop_when_case_is_detailed_and_already_screened(self):
        analysis = symptom_ai.analyze_report(
            SAMPLE_REPORT + " Nao tive falta de ar, vomitos, sangramento ou urina escura. Sou adulto sem alergias."
        )
        payload = symptom_ai.build_triage_question_payload(
            analysis,
            asked_questions=[
                "urgent_breathing_standing",
                "urgent_systemic_worsening",
                "urgent_vulnerable_person",
                "bleeding",
            ],
        )

        self.assertIsNone(payload)
        self.assertIn("parada antecipada", analysis["question_selection_log"]["reason"])

    def test_no_duplicate_count_for_same_symptom_from_description_and_answer(self):
        text = SAMPLE_REPORT + " Resposta clinica: question_id=blister target_field=blister answer=yes normalized_value=true confidence=0.85."
        profile = symptom_ai.extract_structured_clinical_data(text)
        clues = symptom_ai.infer_clues_from_profile(profile)

        self.assertEqual(list(clues).count("blister"), 1)

    def test_selection_log_contains_ranking_candidates_and_ignored_items(self):
        analysis = symptom_ai.analyze_report(SAMPLE_REPORT)
        symptom_ai.build_triage_question_payload(analysis, asked_questions=[])
        log = analysis["question_selection_log"]

        self.assertTrue(log["current_ranking"])
        self.assertTrue(log["compared_species"])
        self.assertTrue(log["candidates"])
        self.assertTrue(log["ignored_answered"])
        self.assertIsNotNone(log["chosen"])


if __name__ == "__main__":
    unittest.main()
