import json
from unittest.mock import patch

import numpy as np

from odoo.exceptions import AccessError, UserError
from odoo.libs.documents import (
    CUES,
    EXPENSIVE,
    RECORDING_MIMETYPES,
    BaseReader,
    Cue,
    register_reader,
    unregister_reader,
)
from odoo.tests import HttpCase, TransactionCase, tagged

from ..tools import embedder
from odoo.addons.base.tests.common import converted_reach
from odoo.addons.speech_voiceprint.models import speech_voiceprint

MODEL = "odoo.addons.speech_voiceprint.models.speech_voiceprint.SpeechVoiceprint"
TWO_VOICES = [
    {"start": 0.0, "end": 5.0, "text": "hola", "speaker": "SPEAKER_0"},
    {"start": 5.0, "end": 12.0, "text": "buenas", "speaker": "SPEAKER_1"},
]


def _unit(seed, dim=8):
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=dim)
    return (vector / np.linalg.norm(vector)).tolist()


class _TwoVoices(BaseReader):
    name = "stub_two_voices"
    mimetypes = RECORDING_MIMETYPES
    yields = (CUES,)
    cost = EXPENSIVE

    def read(self, document):
        return [Cue(c["start"], c["end"], c["text"], c["speaker"]) for c in TWO_VOICES]


@tagged("post_install", "-at_install")
class TestVoiceprint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Employee = cls.env["hr.employee"]
        cls.aaron = Employee.create(
            {"name": "Aaron Ramírez", "company_id": cls.company.id}
        )
        cls.hugo = Employee.create(
            {"name": "Hugo García", "company_id": cls.company.id}
        )
        cls.vec_aaron, cls.vec_hugo = _unit(1), _unit(2)
        cls.model_name = "wespeaker_en_voxceleb_CAM++.onnx"
        cls.env["ir.config_parameter"].sudo().set_param(
            "speech_voiceprint.model_path", f"/models/{cls.model_name}"
        )
        now = cls.env.cr.now()
        for employee, vector in ((cls.aaron, cls.vec_aaron), (cls.hugo, cls.vec_hugo)):
            cls.env["speech.voiceprint"].create(
                {
                    "employee_id": employee.id,
                    "embedding": vector,
                    "dim": len(vector),
                    "model_name": cls.model_name,
                    "consent_at": now,
                    "enrolled_at": now,
                }
            )
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "call.ogg",
                "mimetype": "audio/ogg",
                "raw": b"not-real-audio",
                "company_id": cls.company.id,
                "transcript_state": "done",
                "transcript_cues": TWO_VOICES,
            }
        )
        cls.env["speech.speaker"]._sync_from_cues(cls.attachment)
        cls.voice0, cls.voice1 = cls.attachment.speaker_ids.sorted("label")

    def _identify(self, by_label):
        starts = {0.0: "SPEAKER_0", 5.0: "SPEAKER_1"}

        def fake_embedding(model_self, samples, spans):
            return by_label.get(starts[spans[0][0]])

        with (
            patch(f"{MODEL}._embedder", return_value=object()),
            patch(f"{MODEL}._decode", return_value=np.zeros(16000)) as decode,
            patch(f"{MODEL}._voice_embedding", fake_embedding),
        ):
            assigned = self.env["speech.voiceprint"]._identify_speakers(self.attachment)
        self.assertLessEqual(decode.call_count, 1, "the audio is decoded once")
        return assigned

    def test_clear_matches_name_the_employees_and_their_contacts(self):
        assigned = self._identify(
            {"SPEAKER_0": self.vec_aaron, "SPEAKER_1": self.vec_hugo}
        )
        self.assertEqual(assigned, 2)
        self.assertEqual(self.voice0.employee_id, self.aaron)
        self.assertEqual(self.voice0.partner_id, self.aaron.partner_id)
        self.assertEqual(self.voice0.name, self.aaron.partner_id.name)
        self.assertAlmostEqual(self.voice0.voice_score, 1.0, places=2)
        self.assertEqual(self.voice1.employee_id, self.hugo)

    def test_an_unclear_voice_stays_anonymous(self):
        between = [
            (a + b) / 2 for a, b in zip(self.vec_aaron, self.vec_hugo, strict=True)
        ]
        self.assertEqual(
            self._identify({"SPEAKER_0": _unit(99), "SPEAKER_1": between}), 0
        )
        self.assertFalse(self.voice0.employee_id)
        self.assertEqual(self.voice0.name, "SPEAKER_0")
        self.assertFalse(self.voice1.employee_id)

    def test_a_person_set_by_hand_is_not_overridden(self):
        customer = self.env["res.partner"].create({"name": "Cliente"})
        self.voice0.partner_id = customer
        self._identify({"SPEAKER_0": self.vec_aaron, "SPEAKER_1": self.vec_hugo})
        self.assertEqual(self.voice0.partner_id, customer)
        self.assertFalse(self.voice0.employee_id)

    def test_no_model_means_no_change(self):
        with patch(f"{MODEL}._embedder", return_value=None):
            self.assertEqual(
                self.env["speech.voiceprint"]._identify_speakers(self.attachment), 0
            )
        self.assertEqual(self.voice0.name, "SPEAKER_0")

    def test_prints_of_another_model_do_not_score(self):
        self.env["speech.voiceprint"].search(
            [("employee_id", "=", self.hugo.id)]
        ).write({"model_name": "older.onnx"})
        self.assertEqual(
            self._identify({"SPEAKER_0": self.vec_aaron, "SPEAKER_1": self.vec_hugo}), 1
        )
        self.assertFalse(self.voice1.employee_id)

    def test_one_print_serves_one_voice_per_recording(self):
        self.env["speech.voiceprint"].search(
            [("employee_id", "=", self.hugo.id)]
        ).write({"active": False})
        self.assertEqual(
            self._identify({"SPEAKER_0": self.vec_aaron, "SPEAKER_1": self.vec_aaron}),
            1,
        )
        self.assertFalse(self.voice1.employee_id)

    def test_identification_follows_a_transcription_on_its_own(self):
        engine = register_reader(_TwoVoices())
        self.addCleanup(unregister_reader, engine)
        recording = self.env["ir.attachment"].create(
            {"name": "new.ogg", "mimetype": "audio/ogg", "raw": b"OggS-new"}
        )
        with (
            patch(f"{MODEL}._embedder", return_value=object()),
            patch(f"{MODEL}._decode", return_value=np.zeros(16000)),
            patch(
                f"{MODEL}._voice_embedding",
                lambda model_self, samples, spans: (
                    self.vec_aaron if spans[0][0] == 0.0 else None
                ),
            ),
            patch("odoo.addons.speech.tools.engines.can_transcribe", return_value=True),
            patch(
                "odoo.addons.speech.models.ir_attachment.can_transcribe",
                return_value=True,
            ),
        ):
            recording._transcribe()
        voice = recording.speaker_ids.filtered(lambda s: s.label == "SPEAKER_0")
        self.assertEqual(voice.employee_id, self.aaron)

    def test_a_recognition_failure_does_not_lose_the_transcript(self):
        engine = register_reader(_TwoVoices())
        self.addCleanup(unregister_reader, engine)
        recording = self.env["ir.attachment"].create(
            {"name": "new.ogg", "mimetype": "audio/ogg", "raw": b"OggS-new"}
        )
        with (
            patch(
                f"{MODEL}._identify_speakers", side_effect=RuntimeError("model crashed")
            ),
            patch(
                "odoo.addons.speech.models.ir_attachment.can_transcribe",
                return_value=True,
            ),
        ):
            recording._transcribe()
        self.assertEqual(recording.transcript_state, "done")
        self.assertEqual(len(recording.speaker_ids), 2)

    def test_enrolment_replaces_and_requires_enough_speech(self):
        Print = self.env["speech.voiceprint"]
        with (
            patch(f"{MODEL}._embedder", return_value=object()),
            patch(f"{MODEL}._embed_audio", return_value=(_unit(3), 4.0)),
            self.assertRaises(UserError),
        ):
            Print._enroll(self.aaron, b"short")
        Print.search([("employee_id", "=", self.aaron.id)]).write({"active": False})
        with (
            patch(f"{MODEL}._embedder", return_value=object()),
            patch(f"{MODEL}._embed_audio", return_value=(_unit(3), 24.0)),
            self.assertRaises(UserError),
        ):
            Print._enroll(self.aaron, b"long-enough")
        Print.with_context(active_test=False).search(
            [("employee_id", "=", self.aaron.id)]
        ).write({"active": True})
        with (
            patch(f"{MODEL}._embedder", return_value=object()),
            patch(f"{MODEL}._embed_audio", return_value=(_unit(3), 24.0)),
        ):
            print_ = Print._enroll(self.aaron, b"long-enough")
        self.assertEqual(print_.embedding, _unit(3))
        self.assertEqual(Print.search_count([("employee_id", "=", self.aaron.id)]), 1)

    def test_slice_spans_keeps_the_longest_speech_first(self):
        samples = np.arange(16000 * 10, dtype=np.float32)
        piece = embedder.slice_spans(samples, [(0, 1), (2, 5), (7, 8)], max_seconds=3)
        self.assertEqual(piece.size, 16000 * 3)
        self.assertEqual(piece[0], 16000 * 2)

    def test_cosine(self):
        self.assertAlmostEqual(embedder.cosine([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(embedder.cosine([1, 0], [0, 1]), 0.0)
        self.assertEqual(embedder.cosine([], [1]), 0.0)

    def test_a_missing_or_unusable_model_is_not_cached(self):
        Print = self.env["speech.voiceprint"]
        self.assertIsNone(Print._embedder())
        with (
            patch(f"{speech_voiceprint.__name__}.Path.is_file", return_value=True),
            patch(
                f"{speech_voiceprint.__name__}.embedder.SpeakerEmbedder",
                side_effect=ValueError("not a model"),
            ),
        ):
            self.assertIsNone(Print._embedder())
        self.assertNotIn(Print._model_path(), speech_voiceprint._EMBEDDERS)

    def test_a_bad_threshold_parameter_falls_back(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "speech_voiceprint.threshold", "0,65"
        )
        self.assertEqual(self.env["speech.voiceprint"]._thresholds(), (0.65, 0.08))

    def test_the_embedding_is_for_system_users_only(self):
        officer = self.env["res.users"].create(
            {
                "name": "Officer",
                "login": "vp_officer",
                "group_ids": [(6, 0, self.env.ref("hr.group_hr_user").ids)],
            }
        )
        print_ = self.env["speech.voiceprint"].search(
            [("employee_id", "=", self.aaron.id)]
        )
        self.assertEqual(
            print_.with_user(officer).read(["employee_id"])[0]["employee_id"][0],
            self.aaron.id,
        )
        with self.assertRaises(AccessError):
            print_.with_user(officer).read(["embedding"])

    def test_an_hr_officer_deletes_a_voiceprint_of_their_company(self):
        officer = self.env["res.users"].create(
            {
                "name": "Deleting Officer",
                "login": "vp_deleting_officer",
                "group_ids": [(6, 0, self.env.ref("hr.group_hr_user").ids)],
            }
        )
        print_ = self.env["speech.voiceprint"].search(
            [("employee_id", "=", self.aaron.id)]
        )
        self.assertEqual(
            converted_reach(self.env, "speech.voiceprint", officer, "unlink") & print_,
            print_,
        )
        print_.with_user(officer).unlink()
        self.assertFalse(print_.exists())


@tagged("post_install", "-at_install")
class TestVoiceprintRoutes(HttpCase):
    def _status(self):
        response = self.url_open(
            "/speech/voiceprint/status",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

    def test_status_needs_an_employee_and_serves_the_phrase(self):
        user = self.env["res.users"].create(
            {
                "name": "vp_user",
                "login": "vp_user",
                "password": "vp_password_12",
                "group_ids": [(6, 0, self.env.ref("base.group_user").ids)],
            }
        )
        self.authenticate(user.login, "vp_password_12")
        self.assertIn("error", self._status())
        self.env["hr.employee"].create({"name": "Member", "user_id": user.id})
        self.env["ir.config_parameter"].sudo().set_param(
            "speech_voiceprint.phrase", "Buenos días, lee esta frase."
        )
        result = self._status()["result"]
        self.assertEqual(result["employee"], "Member")
        self.assertEqual(result["phrase"], "Buenos días, lee esta frase.")
        self.assertFalse(result["enrolled"])
