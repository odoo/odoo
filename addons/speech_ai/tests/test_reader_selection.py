from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.speech_ai.tools.readers import _pick_timed_model


@tagged("post_install", "-at_install")
class TestReaderSelection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        endpoint = cls.env["integration.service"].search([("code", "=", "openai")])
        cls.env["credential.credential"].create(
            {"name": "openai", "endpoint_id": endpoint.id, "bearer_token": "K"}
        )

    def test_a_cheaper_model_without_timestamps_is_not_picked_for_cues(self):
        transcribe = self.env.ref("gateway_ml.ai_model_openai_gpt_transcribe")
        whisper = self.env.ref("gateway_ml.ai_model_openai_whisper_1")
        self.assertLess(transcribe.cost_per_audio_minute, whisper.cost_per_audio_minute)
        self.assertEqual(_pick_timed_model(self.env), whisper)
