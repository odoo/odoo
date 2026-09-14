from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import connect
from odoo.addons.gateway_ml.tools import MlRequest, MlRouter
from odoo.addons.gateway_ml.tools.ai_clients import (
    DeepgramClient,
    OpenAICompatibleClient,
)
from odoo.addons.integration.tools.exceptions import CommError


@tagged("post_install", "-at_install")
class TestRouterRun(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.openai = cls.env.ref("gateway_ml.ai_provider_openai")
        cls.deepgram = cls.env.ref("gateway_ml.ai_provider_deepgram")
        for provider in cls.env["gateway.ml.provider"].search([]):
            if provider not in (cls.openai, cls.deepgram):
                provider.action_archive()
        connect(cls.env, cls.openai)
        connect(cls.env, cls.deepgram)
        cls.router = MlRouter(cls.env)

    def _run(self, operation, request, **kwargs):
        client = Mock(
            simple_completion=Mock(return_value="an answer"),
            vision_completion=Mock(return_value="a picture"),
            transcribe=Mock(return_value="hola"),
            transcribe_cues=Mock(return_value=[{"start": 0, "end": 1, "text": "hola"}]),
            synthesize=Mock(return_value=b"ID3"),
        )
        with patch.object(MlRouter, "_get_client", return_value=client):
            return self.router.run(operation, request, **kwargs), client

    def test_a_chat_is_sent_as_a_completion_on_a_chat_model(self):
        result, client = self._run("chat", MlRequest(prompt="q", temperature=0.1))

        self.assertEqual(result.text, "an answer")
        self.assertEqual(result.model.kind, "chat")
        client.simple_completion.assert_called_once_with(
            "q", model=result.model.code, temperature=0.1
        )
        client.vision_completion.assert_not_called()

    def test_a_chat_with_an_image_needs_a_model_that_sees(self):
        result, client = self._run(
            "chat", MlRequest(prompt="what?", images=(("QUJD", "image/png"),))
        )

        self.assertEqual(result.text, "a picture")
        self.assertTrue(result.model.has_vision)
        self.assertEqual(
            client.vision_completion.call_args.kwargs["media_type"], "image/png"
        )

    def test_a_timed_transcription_carries_the_vocabulary_and_speakers(self):
        result, client = self._run(
            "transcribe_timed",
            MlRequest(
                audio=b"AUDIO",
                mimetype="audio/ogg",
                language="es",
                vocabulary=("tarima", "romana"),
                speakers=True,
            ),
        )

        self.assertEqual(result.cues[0]["text"], "hola")
        self.assertTrue(result.model.has_timestamps)
        kwargs = client.transcribe_cues.call_args.kwargs
        self.assertEqual(kwargs["vocabulary"], ("tarima", "romana"))
        self.assertTrue(kwargs["speakers"])
        self.assertEqual(kwargs["language"], "es")

    def test_a_named_provider_runs_its_default_model(self):
        result, _client = self._run(
            "transcribe", MlRequest(audio=b"AUDIO"), provider=self.deepgram
        )

        self.assertEqual(result.model, self.deepgram.default_model_id)
        self.assertEqual(result.text, "hola")

    def test_synthesis_returns_the_audio(self):
        result, client = self._run(
            "synthesize", MlRequest(text="hola", mimetype="audio/flac")
        )

        self.assertEqual(result.audio, b"ID3")
        self.assertEqual(client.synthesize.call_args.kwargs["mimetype"], "audio/flac")

    def test_no_usable_model_is_a_named_error(self):
        self.deepgram.action_archive()
        with self.assertRaises(CommError) as caught:
            self._run("transcribe", MlRequest(audio=b"A"), provider=self.deepgram)
        self.assertIn("transcribe", str(caught.exception))

    def test_an_unknown_operation_is_refused(self):
        with self.assertRaises(ValueError):
            self.router.run("dream", MlRequest())


@tagged("post_install", "-at_install")
class TestTranscriptionVocabulary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connect(cls.env, cls.env.ref("gateway_ml.ai_provider_openai"))
        connect(cls.env, cls.env.ref("gateway_ml.ai_provider_deepgram"))

    def test_deepgram_sends_the_vocabulary_as_keyterms_and_asks_for_speakers(self):
        client = DeepgramClient(self.env)
        body = {
            "results": {
                "utterances": [
                    {"start": 0, "end": 1, "transcript": "hola", "speaker": 0}
                ]
            }
        }
        with patch.object(client._client, "post", return_value={"body": body}) as post:
            client.transcribe_cues(
                b"AUDIO", vocabulary=("tarima",), speakers=True, model="nova-3"
            )
        params = post.call_args.kwargs["params"]
        self.assertEqual(params["keyterm"], ["tarima"])
        self.assertEqual(params["diarize"], "true")

    def test_deepgram_reads_plain_text_from_the_channel(self):
        client = DeepgramClient(self.env)
        body = {"results": {"channels": [{"alternatives": [{"transcript": " hola "}]}]}}
        with patch.object(client._client, "post", return_value={"body": body}):
            self.assertEqual(client.transcribe(b"AUDIO", model="nova-3"), "hola")

    def test_whisper_takes_the_vocabulary_as_its_spelling_prompt(self):
        client = OpenAICompatibleClient(self.env, endpoint_code="openai")
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": "hola"}
        ) as post:
            client.transcribe(b"AUDIO", "a.ogg", vocabulary=("tarima", "romana"))
        self.assertEqual(post.call_args.kwargs["data"]["prompt"], "tarima, romana")
