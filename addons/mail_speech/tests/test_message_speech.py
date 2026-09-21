from markupsafe import Markup

from odoo.exceptions import UserError
from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    RECORDING_MIMETYPES,
    TEXT,
    BaseReader,
    BaseWriter,
    Cue,
    get_writers,
    register_reader,
    register_writer,
    unregister_reader,
    unregister_writer,
)
from odoo.tests import tagged

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail_speech.tools.speech import READ_ALOUD_MAX_CHARS


class StubTranscription(BaseReader):
    name = "stub_message_transcription"
    mimetypes = RECORDING_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE

    def read(self, document):
        return [Cue(0.0, 2.0, "left you a note", "")]


class StubSpeech(BaseWriter):
    name = "stub_message_speech"
    mimetype = "audio/mpeg"
    consumes = TEXT

    def __init__(self):
        self.spoken = []

    def write(self, value, **options):
        self.spoken.append(value)
        return b"ID3-spoken"


@tagged("post_install", "-at_install")
class TestMessageSpeech(MailCommon):
    def setUp(self):
        super().setUp()
        self.channel = self.env["discuss.channel"]._create_channel(
            name="Notes", group_id=None
        )

    def _with_transcription(self):
        engine = register_reader(StubTranscription())
        self.addCleanup(unregister_reader, engine)
        return engine

    def _with_speech(self):
        displaced = get_writers("audio/mpeg", TEXT)
        for other in displaced:
            unregister_writer(other)
        engine = register_writer(StubSpeech())

        def restore():
            unregister_writer(engine)
            for other in displaced:
                register_writer(other)

        self.addCleanup(restore)
        return engine

    def _voice_message(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "Voice.mp3", "mimetype": "audio/mpeg", "raw": b"voice"}
        )
        self.env["discuss.voice.metadata"].create({"attachment_id": attachment.id})
        message = self.channel.message_post(
            body="", message_type="comment", attachment_ids=[attachment.id]
        )
        return message, attachment

    def test_a_voice_message_can_be_transcribed_like_any_recording(self):
        self._with_transcription()
        _message, attachment = self._voice_message()
        self.assertTrue(attachment.can_transcribe)
        attachment._transcribe()
        self.assertEqual(attachment.speech_transcript, "left you a note")

    def test_the_client_is_told_what_a_voice_message_says(self):
        self._with_transcription()
        message, attachment = self._voice_message()
        fields = attachment._to_store_defaults(None)
        self.assertIn("speech_transcript", fields)
        self.assertIn("speech_state", fields)
        self.assertIn("can_transcribe", fields)
        self.assertTrue(attachment._speech_messages() >= message)

    def test_transcribing_a_voice_message_notifies_its_conversation(self):
        self._with_transcription()
        message, attachment = self._voice_message()
        attachment._transcribe()
        self.assertEqual(attachment.speech_state, "done")
        self.assertIn(message, attachment._speech_messages())

    def test_a_message_is_read_aloud_and_the_audio_is_attached_to_it(self):
        engine = self._with_speech()
        message = self.channel.message_post(
            body=Markup("<p>The invoice went out on Tuesday.</p>"),
            message_type="comment",
        )
        attachment = message.action_read_aloud()
        self.assertEqual(engine.spoken, ["The invoice went out on Tuesday."])
        self.assertEqual(attachment.raw, b"ID3-spoken")
        self.assertIn(attachment, message.attachment_ids)
        self.assertEqual(attachment.res_model, "mail.message")
        self.assertEqual(attachment.res_id, message.id)

    def test_reading_aloud_strips_the_markup_rather_than_speaking_it(self):
        engine = self._with_speech()
        message = self.channel.message_post(
            body=Markup("<p>Hello <strong>there</strong></p>"), message_type="comment"
        )
        message.action_read_aloud()
        self.assertNotIn("<", engine.spoken[0])
        self.assertIn("there", engine.spoken[0])

    def test_an_empty_message_is_refused_rather_than_billed(self):
        engine = self._with_speech()
        message = self.channel.message_post(
            body=Markup("<p><br></p>"), message_type="comment"
        )
        with self.assertRaises(UserError):
            message.action_read_aloud()
        self.assertEqual(engine.spoken, [])

    def test_a_message_too_long_to_speak_is_refused_with_its_length(self):
        engine = self._with_speech()
        message = self.channel.message_post(
            body=Markup("<p>%s</p>") % ("word " * (READ_ALOUD_MAX_CHARS // 2)),
            message_type="comment",
        )
        with self.assertRaises(UserError):
            message.action_read_aloud()
        self.assertEqual(engine.spoken, [])

    def test_reading_aloud_without_an_engine_is_refused(self):
        message = self.channel.message_post(
            body=Markup("<p>hello</p>"), message_type="comment"
        )
        with self.assertRaises(UserError):
            message.action_read_aloud()
