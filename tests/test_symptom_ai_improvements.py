import collections
import unittest

import symptom_ai

from standardized_case_base import STANDARDIZED_CASES


def marker(question_id, answer):
    question = symptom_ai.QUESTION_BY_ID[question_id]
    return symptom_ai.clinical_answer_marker(question, answer)


def top_animals(report):
    return [item["animal"] for item in symptom_ai.analyze_report(report)["species_matches"]]


class SymptomAiImprovementTests(unittest.TestCase):
    def test_yes_answer_maps_to_present(self):
        profile = symptom_ai.extract_structured_clinical_data(marker("bleeding", "sim"))
        self.assertIs(profile["bleeding"]["value"], True)
        self.assertEqual(profile["bleeding"]["status"], "present")

    def test_no_answer_maps_to_absent(self):
        profile = symptom_ai.extract_structured_clinical_data(marker("bleeding", "nao"))
        self.assertIs(profile["bleeding"]["value"], False)
        self.assertEqual(profile["bleeding"]["status"], "absent")

    def test_partial_answer_maps_to_partial(self):
        profile = symptom_ai.extract_structured_clinical_data(marker("blister", "um pouco"))
        self.assertEqual(profile["blister"]["status"], "partial")

    def test_unknown_answer_maps_to_unknown(self):
        profile = symptom_ai.extract_structured_clinical_data(marker("blister", "nao sei"))
        self.assertEqual(profile["blister"]["status"], "unknown")

    def test_not_yet_answer_is_time_uncertain_absence(self):
        profile = symptom_ai.extract_structured_clinical_data(marker("urine_change", "ainda nao"))
        self.assertEqual(profile["urine_change"]["status"], "absent_with_time_uncertainty")

    def test_present_then_negated_reduces_confidence(self):
        text = "Tem sangramento. " + marker("bleeding", "nao")
        profile = symptom_ai.extract_structured_clinical_data(text)
        self.assertIs(profile["bleeding"]["value"], False)
        self.assertTrue(profile["bleeding"].get("conflict"))
        self.assertLess(profile["bleeding"]["confidence"], 0.9)

    def test_negated_then_confirmed_updates_field_with_conflict(self):
        text = "Sem sangramento. " + marker("bleeding", "sim")
        profile = symptom_ai.extract_structured_clinical_data(text)
        self.assertIs(profile["bleeding"]["value"], True)
        self.assertTrue(profile["bleeding"].get("conflict"))

    def test_early_absence_of_late_symptom_is_softened(self):
        report = "Faz 40 minutos, pouca dor no local, ainda nao apareceu urina escura."
        analysis = symptom_ai.analyze_report(report)
        self.assertEqual(analysis["bite_time_analysis"]["bucket"], "VERY_EARLY")
        cascavel = next((item for item in analysis["species_matches"] if item["animal"] == "cascavel"), None)
        self.assertTrue(cascavel is None or cascavel["score"] > -3)

    def test_brown_spider_delayed_worsening(self):
        animals = top_animals("Ha 6 horas, dor comecou fraca e aumentou, pele roxa e bolha no pe em roupa guardada.")
        self.assertIn("aranha_marrom", animals[:2])

    def test_rattlesnake_ptosis_without_bleeding(self):
        animals = top_animals("Ha 4 horas, pouca lesao local, palpebras caidas, visao embacada, fraqueza e sem sangramento.")
        self.assertIn("cascavel", animals[:2])

    def test_jararaca_edema_bruising_bleeding(self):
        animals = top_animals("Mordida em trilha, edema aumentando, hematoma roxo, duas marcas profundas e sangramento.")
        self.assertIn("jararaca", animals[:2])

    def test_armadeira_immediate_pain_sweating_spasms(self):
        animals = top_animals("Dor imediata muito intensa no pe, suor local, tremores e espasmos apos mexer em sapato.")
        self.assertIn("armadeira", animals[:2])

    def test_scorpion_immediate_pain_autonomic(self):
        animals = top_animals("Dor intensa imediata tipo choque no banheiro, suor frio, nausea, vomito e tremores.")
        self.assertIn(animals[0], {"escorpiao_amarelo", "escorpiao_marrom"})

    def test_differential_question_between_jararaca_and_cascavel(self):
        analysis = symptom_ai.analyze_report("Cobra em area rural, pe com pouca marca e fraqueza. Ha 4 horas.")
        payload = symptom_ai.build_triage_question_payload(
            analysis,
            asked_questions=["urgent_breathing_standing", "urgent_systemic_worsening", "urgent_vulnerable_person"],
        )
        self.assertIn(payload["question_id"], {"neuro_ocular", "urine_change", "bleeding", "swelling_progression", "muscle_weakness"})

    def test_differential_question_between_brown_spider_and_armadeira(self):
        analysis = symptom_ai.analyze_report("Picada no pe dentro de casa, dor e queimacao, nao sei se foi aranha.")
        payload = symptom_ai.build_triage_question_payload(
            analysis,
            asked_questions=["urgent_breathing_standing", "urgent_systemic_worsening", "urgent_vulnerable_person"],
        )
        self.assertIn(payload["question_id"], {"immediate_severe_pain", "pain_delayed_worsening", "purple_skin", "blister"})

    def test_answered_question_is_not_repeated(self):
        text = "Dor e inchaco. " + marker("bleeding", "nao")
        analysis = symptom_ai.analyze_report(text)
        payload = symptom_ai.build_triage_question_payload(
            analysis,
            asked_questions=["urgent_breathing_standing", "urgent_systemic_worsening", "urgent_vulnerable_person"],
        )
        self.assertNotEqual(payload["question_id"], "bleeding")

    def test_environment_does_not_overcome_strong_clinical_signs(self):
        animals = top_animals("No quarto em roupa guardada, mas teve duas marcas profundas, edema aumentando e sangramento.")
        self.assertIn("jararaca", animals[:2])

    def test_unknown_time_has_no_time_penalty(self):
        parsed = symptom_ai.parse_bite_time("nao sei")
        self.assertEqual(parsed["bucket"], "UNKNOWN")
        analysis = symptom_ai.analyze_report("Nao sei o tempo. Dor forte imediata e suor intenso.")
        self.assertEqual(analysis["bite_time_analysis"]["bucket"], "UNKNOWN")

    def test_contradictory_information_reduces_field_confidence(self):
        profile = symptom_ai.extract_structured_clinical_data("Tem bolha. " + marker("blister", "acho que nao"))
        self.assertTrue(profile["blister"].get("conflict"))
        self.assertLess(profile["blister"]["confidence"], 0.9)

    def test_urgency_still_has_priority(self):
        analysis = symptom_ai.analyze_report("Dor e inchaco no pe.")
        payload = symptom_ai.build_triage_question_payload(analysis, asked_questions=[])
        self.assertEqual(payload["category"], "urgency")

    def test_standardized_case_metrics_are_available(self):
        top1 = top2 = top3 = 0
        confusions = collections.Counter()
        for case in STANDARDIZED_CASES:
            animals = top_animals(case["report"])
            if animals[:1] == [case["expected_species"]]:
                top1 += 1
            elif animals:
                confusions[(case["expected_species"], animals[0])] += 1
            if case["expected_species"] in animals[:2]:
                top2 += 1
            if case["expected_species"] in animals[:3]:
                top3 += 1

        total = len(STANDARDIZED_CASES)
        self.assertEqual(total, 90)
        self.assertGreaterEqual(top3 / total, 0.45)
        self.metrics = {
            "top1": top1,
            "top2": top2,
            "top3": top3,
            "total": total,
            "confusions": confusions.most_common(5),
        }


if __name__ == "__main__":
    unittest.main()
