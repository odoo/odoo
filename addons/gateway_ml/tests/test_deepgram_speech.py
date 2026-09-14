from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import DeepgramClient, get_client_class
from odoo.addons.integration.tools.exceptions import CommError

_UTTERANCES = {
    "results": {
        "utterances": [
            {"transcript": "hola", "start": 0.0, "end": 0.8, "speaker": 0},
            {"transcript": "  ", "start": 0.8, "end": 0.9, "speaker": 1},
            {"transcript": "adiós", "start": 1.0, "end": 1.5, "speaker": 1},
        ]
    }
}


@tagged("post_install", "-at_install")
class TestDeepgramSpeech(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "deepgram", api_key="K")

    def setUp(self):
        super().setUp()
        self.client = DeepgramClient(self.env)

    def test_transcribe_cues_reads_utterances_with_their_speaker(self):
        with patch.object(
            self.client._client,
            "post",
            return_value={"status_code": 200, "body": _UTTERANCES},
        ) as post:
            cues = self.client.transcribe_cues(
                b"AUDIO", mimetype="audio/ogg", language="es", model="nova-3"
            )

        self.assertEqual(
            cues,
            [
                {
                    "start": 0.0,
                    "end": 0.8,
                    "text": "hola",
                    "speaker": "Speaker 0",
                    "speaker_index": 0,
                    "confidence": 0.0,
                },
                {
                    "start": 1.0,
                    "end": 1.5,
                    "text": "adiós",
                    "speaker": "Speaker 1",
                    "speaker_index": 1,
                    "confidence": 0.0,
                },
            ],
        )
        self.assertEqual(post.call_args.args[0], "/listen")
        params = post.call_args.kwargs["params"]
        self.assertEqual(params["utterances"], "true")
        self.assertEqual(params["language"], "es")
        self.assertEqual(params["model"], "nova-3")
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "audio/ogg")

    def test_transcribe_cues_refuses_an_empty_transcript(self):
        with patch.object(
            self.client._client,
            "post",
            return_value={"status_code": 200, "body": {"results": {}}},
        ):
            with self.assertRaises(CommError):
                self.client.transcribe_cues(b"AUDIO", mimetype="audio/ogg")

    def test_synthesize_posts_speak_and_returns_the_bytes(self):
        with patch.object(
            self.client._client, "post", return_value=Mock(content=b"ID3")
        ) as post:
            audio = self.client.synthesize(
                "hola", mimetype="audio/wav", model="aura-2-celeste-es"
            )

        self.assertEqual(audio, b"ID3")
        self.assertEqual(post.call_args.args[0], "/speak")
        self.assertTrue(post.call_args.kwargs["raw"])
        self.assertEqual(post.call_args.kwargs["json"], {"text": "hola"})
        self.assertEqual(
            post.call_args.kwargs["params"],
            {"model": "aura-2-celeste-es", "encoding": "linear16", "container": "wav"},
        )

    def test_synthesize_refuses_a_format_it_does_not_write(self):
        with patch.object(self.client._client, "post") as post:
            with self.assertRaises(CommError) as caught:
                self.client.synthesize("hola", mimetype="audio/x-nope")
        self.assertIn("audio/x-nope", str(caught.exception))
        post.assert_not_called()

    def test_a_voice_of_another_vendor_falls_back_to_the_model(self):
        with patch.object(
            self.client._client, "post", return_value=Mock(content=b"ID3")
        ) as post:
            self.client.synthesize("hola", voice="alloy", model="aura-2-luna-en")
        self.assertEqual(post.call_args.kwargs["params"]["model"], "aura-2-luna-en")


@tagged("post_install", "-at_install")
class TestEveryModelKindHasItsMethod(TransactionCase):
    METHOD_OF_KIND = {
        "audio": "transcribe_cues",
        "speech": "synthesize",
        "chat": "simple_completion",
        "vision": "vision_completion",
    }

    def test_a_seeded_model_is_served_by_a_client_that_answers_its_kind(self):
        for model in self.env["gateway.ml.model"].search([]):
            method = self.METHOD_OF_KIND.get(model.kind)
            if not method:
                continue
            client_cls = get_client_class(model.provider_id)
            with self.subTest(model=model.code, kind=model.kind):
                self.assertIsNotNone(client_cls)
                self.assertTrue(
                    callable(getattr(client_cls, method, None)),
                    f"{model.code} is a {model.kind} model, so the router "
                    f"can select it for a {method} call, and "
                    f"{client_cls.__name__} has no {method}",
                )
