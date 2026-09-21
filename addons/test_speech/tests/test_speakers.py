from odoo.exceptions import AccessError
from odoo.libs.documents import Cue, unregister_reader
from odoo.tests import tagged

from .common import SpeechCase, StubTranscription

TWO_VOICES = [
    Cue(0.0, 2.0, "buenos días", "SPEAKER_0"),
    Cue(2.0, 5.0, "le hablo para la visita", "SPEAKER_1"),
    Cue(5.0, 6.0, "claro", "SPEAKER_0"),
]


@tagged("post_install", "-at_install")
class TestSpeakers(SpeechCase):
    def _transcribed(self, cues=TWO_VOICES, name="call.mp3"):
        if getattr(self, "_engine", None):
            unregister_reader(self._engine)
        self._engine = self._register(StubTranscription(cues=cues))
        attachment = self._audio(name=name)
        attachment._transcribe()
        return attachment

    def test_each_voice_of_a_transcript_becomes_a_speaker_with_its_talk(self):
        attachment = self._transcribed()
        speakers = attachment.speaker_ids.sorted("label")
        self.assertEqual(speakers.mapped("label"), ["SPEAKER_0", "SPEAKER_1"])
        first, second = speakers
        self.assertEqual((first.turns, first.talk_time_s), (2, 3.0))
        self.assertEqual((second.turns, second.talk_time_s), (1, 3.0))
        self.assertEqual(second.first_spoke_s, 2.0)
        self.assertEqual(first.name, "SPEAKER_0")

    def test_naming_a_person_survives_a_new_transcript(self):
        attachment = self._transcribed()
        partner = self.env["res.partner"].create({"name": "Víctor"})
        voice = attachment.speaker_ids.filtered(lambda s: s.label == "SPEAKER_1")
        voice.partner_id = partner
        self.assertEqual(voice.name, "Víctor")
        attachment._transcribe()
        self.assertEqual(len(attachment.speaker_ids), 2)
        self.assertEqual(voice.partner_id, partner)

    def test_a_name_typed_by_hand_stays_until_a_person_is_chosen(self):
        voice = self._transcribed().speaker_ids[:1]
        voice.name = "La del rancho"
        self.assertEqual(voice.name, "La del rancho")

    def test_only_an_internal_user_is_the_speakers_user(self):
        voice = self._transcribed().speaker_ids[:1]
        voice.partner_id = self.env.ref("base.user_admin").partner_id
        self.assertEqual(voice.user_id, self.env.ref("base.user_admin"))
        voice.partner_id = self.env["res.partner"].create({"name": "Cliente"})
        self.assertFalse(voice.user_id)

    def test_a_timeline_adds_up_each_persons_talk_across_its_segments(self):
        partner = self.env["res.partner"].create({"name": "Víctor"})
        recording = self._recording()
        first = self._transcribed(name="a.mp3")
        second = self._transcribed(
            cues=[Cue(0.0, 4.0, "otra vez", "SPEAKER_0")], name="b.mp3"
        )
        recording._add_media_segment(first, 0, 6000)
        recording._add_media_segment(second, 6000, 10000)
        (first | second).speaker_ids.filtered(
            lambda s: s.label == "SPEAKER_0"
        ).partner_id = partner
        self.assertEqual(len(recording.timeline_speaker_ids), 3)
        talk = recording._talk_time_by_person()
        self.assertEqual(talk[partner], 7.0)
        self.assertEqual(talk["SPEAKER_1"], 3.0)

    def test_someone_who_cannot_read_the_recording_cannot_read_its_speakers(self):
        attachment = self._transcribed()
        recording = self._recording()
        recording._add_media_segment(attachment, 0, 6000)
        attachment.sudo().write({"res_model": recording._name, "res_id": recording.id})
        portal = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "portal",
                    "login": "speaker_portal",
                    "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
                }
            )
        )
        portal_env = self.env(user=portal, su=False)
        voice = attachment.speaker_ids[:1]
        with self.assertRaises(AccessError):
            voice.with_env(portal_env).read(["name"])
        self.assertFalse(
            portal_env["speech.speaker"].search(
                [("id", "in", attachment.speaker_ids.ids)]
            )
        )
