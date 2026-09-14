from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import credential_for
from odoo.addons.gateway_ml.tools.ai_clients import OpenAICompatibleClient
from odoo.addons.gateway_ml.tools.wire_formats import (
    get_whisper_form,
    read_whisper_transcript,
)
from odoo.addons.integration.tools.exceptions import CommError


@tagged("post_install", "-at_install")
class TestWhisperFormAndReader(TransactionCase):
    def test_the_form_always_asks_for_text(self):
        form = get_whisper_form("whisper-1", language="es")
        self.assertEqual(form["response_format"], "text")
        self.assertEqual(form["model"], "whisper-1")
        self.assertEqual(form["language"], "es")
        self.assertNotIn("prompt", form, "an absent hint must not be sent empty")

    def test_gpt_transcribe_is_asked_for_json_and_a_language_list(self):
        form = get_whisper_form("gpt-transcribe", language="es")
        self.assertEqual(form["response_format"], "json")
        self.assertEqual(form["languages[]"], "es")
        self.assertNotIn("language", form)

    def test_gpt_transcribe_cannot_be_asked_for_segments(self):
        with self.assertRaises(ValueError):
            get_whisper_form("gpt-transcribe", response_format="verbose_json")

    def test_the_form_carries_a_vocabulary_hint(self):
        self.assertEqual(
            get_whisper_form("whisper-1", prompt="tarima, romana")["prompt"],
            "tarima, romana",
        )

    def test_the_reader_names_why_a_response_is_unusable(self):
        for payload, expected in (
            (None, "no response"),
            ({"segments": []}, "expected text"),
            ("   ", "empty transcript"),
        ):
            with self.subTest(payload=payload):
                text, problem = read_whisper_transcript(payload)
                self.assertIsNone(text)
                self.assertIn(expected, problem)

    def test_the_reader_strips_and_returns(self):
        for payload in ("  hola mundo \n", {"text": "  hola mundo \n"}):
            with self.subTest(payload=payload):
                text, problem = read_whisper_transcript(payload)
                self.assertEqual(text, "hola mundo")
                self.assertIsNone(problem)


@tagged("post_install", "-at_install")
class TestOpenAICompatibleTranscribe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credential_for(cls.env, "openai", bearer_token="K")

    def _client(self, code="openai"):
        return OpenAICompatibleClient(self.env, endpoint_code=code)

    def test_it_posts_the_transcribe_operation(self):
        client = self._client()
        sent = {}

        def fake_post(path, **kwargs):
            sent["path"] = path
            sent.update(kwargs)
            return {"status_code": 200, "body": {"text": "hola mundo"}}

        with patch.object(client._client, "post", side_effect=fake_post):
            result = client.transcribe(b"AUDIO", "note.ogg", language="es")

        transcribe = self.env.ref("gateway_ml.ai_provider_openai")._service_for(
            "transcribe"
        )
        self.assertEqual(result, "hola mundo")
        self.assertEqual(sent["path"], transcribe.path)
        self.assertEqual(sent["data"]["model"], "gpt-transcribe")
        self.assertEqual(sent["data"]["model"], transcribe.model_id.code)
        self.assertEqual(sent["data"]["response_format"], "json")
        self.assertEqual(sent["data"]["languages[]"], "es")
        self.assertEqual(sent["files"]["file"][0], "note.ogg")
        self.assertEqual(
            sent["files"]["file"][2], "audio/ogg", "the mime type is sniffed"
        )

    def test_without_a_language_the_vendor_detects_it(self):
        client = self._client()
        with patch.object(
            client._client,
            "post",
            return_value={"status_code": 200, "body": {"text": "hi"}},
        ) as post:
            client.transcribe(b"AUDIO", "note.ogg")
        self.assertNotIn("language", post.call_args.kwargs["data"])
        self.assertNotIn("languages[]", post.call_args.kwargs["data"])

    def test_timed_transcription_runs_on_whisper(self):
        client = self._client()
        body = {
            "text": "hola mundo",
            "segments": [{"start": 0.0, "end": 1.5, "text": " hola mundo"}],
        }
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": body}
        ) as post:
            spans = client.transcribe_cues(b"AUDIO", "note.ogg", language="es")
        data = post.call_args.kwargs["data"]
        self.assertEqual(
            data["model"],
            self.env.ref("gateway_ml.ai_provider_openai")
            ._service_for("transcribe_timed")
            .model_id.code,
        )
        self.assertEqual(data["response_format"], "verbose_json")
        self.assertEqual(data["language"], "es")
        self.assertEqual(spans[0]["end"], 1.5)

    def test_timed_transcription_is_refused_on_an_untimed_model(self):
        client = self._client()
        with patch.object(client._client, "post") as post:
            with self.assertRaises(CommError) as caught:
                client.transcribe_cues(b"AUDIO", "note.ogg", model="gpt-transcribe")
        post.assert_not_called()
        self.assertIn("no segment timestamps", str(caught.exception))

    def test_an_unusable_response_raises_rather_than_returning_none(self):
        client = self._client()
        with patch.object(
            client._client, "post", return_value={"status_code": 200, "body": ""}
        ):
            with self.assertRaises(CommError) as caught:
                client.transcribe(b"AUDIO", "note.ogg")
        self.assertIn("no usable transcript", str(caught.exception))

    def test_empty_audio_is_refused_before_the_request(self):
        client = self._client()
        with patch.object(client._client, "post") as post:
            with self.assertRaises(CommError):
                client.transcribe(b"", "note.ogg")
        post.assert_not_called()

    def test_a_vendor_without_an_audio_wire_says_so(self):
        credential_for(self.env, "deepseek", bearer_token="K")
        client = self._client("deepseek")
        with self.assertRaises(CommError) as caught:
            client.transcribe(b"AUDIO", "note.ogg")
        self.assertIn("offers no transcribe operation", str(caught.exception))

    def test_groq_transcribes_on_its_own_endpoint(self):
        credential_for(self.env, "groq", bearer_token="K")
        client = self._client("groq")
        with patch.object(
            client._client,
            "post",
            return_value={"status_code": 200, "body": "transcrito"},
        ) as post:
            self.assertEqual(client.transcribe(b"AUDIO", "n.ogg"), "transcrito")
        self.assertEqual(
            post.call_args.kwargs["data"]["model"],
            self.env.ref("gateway_ml.ai_provider_groq")
            ._service_for("transcribe")
            .model_id.code,
        )
