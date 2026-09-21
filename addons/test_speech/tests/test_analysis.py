from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError
from odoo.libs.documents import Cue, unregister_reader
from odoo.tests import tagged

from .common import SpeechCase, StubTranscription
from odoo.addons.gateway_ml.tools import MlResult
from odoo.addons.speech_analysis.tools.schema import MOMENT_KINDS, PURPOSE

ROUTER = "odoo.addons.extract_ai.models.ai_extractors.get_router"

FIRST = [
    Cue(0.0, 2.0, "buenos días", "SPEAKER_0"),
    Cue(2.0, 5.0, "le mando la cotización el viernes", "SPEAKER_1"),
]
SECOND = [Cue(1.0, 3.0, "¿y el flete quién lo paga?", "SPEAKER_0")]

ANSWER = {
    "summary": "Víctor promised the quote by Friday; freight is open.",
    "topics": [{"name": "Quote"}, {"name": "Freight"}],
    "commitments": [
        {
            "what": "Send the quote",
            "who": "Víctor",
            "due": "2026-09-25",
            "at": "00:02",
        }
    ],
    "questions": [
        {
            "question": "Who pays the freight?",
            "asked_by": "SPEAKER_0/2",
            "answered": False,
            "answer": None,
            "at": "01:01",
        }
    ],
    "moments": [
        {"kind": "next_step", "quote": "le mando la cotización", "at": "[00:02]"},
        {"kind": "gossip", "quote": "dropped: not a kind", "at": "00:03"},
    ],
    "speakers": [
        {
            "speaker": "Víctor",
            "sentiment": "Positive",
            "engagement": "high",
            "interruptions": 1,
            "questions_asked": 0,
        }
    ],
}


@tagged("post_install", "-at_install")
class TestSpeechAnalysis(SpeechCase):
    def setUp(self):
        super().setUp()
        self.meeting = self.env["speech.test.meeting"].create({"name": "Visita"})
        self.victor = self.env["res.partner"].create({"name": "Víctor"})

    def _add(self, cues, start_ms, name):
        if getattr(self, "_engine", None):
            unregister_reader(self._engine)
        self._engine = self._register(StubTranscription(cues=cues))
        attachment = self._audio(name=name)
        self.meeting._add_media_segment(attachment, start_ms, start_ms + 10_000)
        attachment._transcribe()
        return attachment

    def _two_segments(self):
        first = self._add(FIRST, 0, "a.mp3")
        first.speaker_ids.filtered(
            lambda s: s.label == "SPEAKER_1"
        ).partner_id = self.victor
        self._add(SECOND, 60_000, "b.mp3")

    def _analyse(self, answer=ANSWER):
        router = MagicMock()
        router.select_model.return_value = MagicMock(code="a-model")
        router.run.return_value = MlResult(model=None, data=answer)
        with patch(ROUTER, return_value=router):
            self.meeting._extract_document()
        return router

    def test_the_transcript_names_each_voice_and_places_it_on_the_timeline(self):
        self._two_segments()

        text, voices = self.meeting._analysis_transcript()

        self.assertEqual(
            text.splitlines(),
            [
                "[00:00] SPEAKER_0/1: buenos días",
                "[00:02] Víctor: le mando la cotización el viernes",
                "[01:01] SPEAKER_0/2: ¿y el flete quién lo paga?",
            ],
        )
        self.assertEqual(voices["Víctor"].partner_id, self.victor)

    def test_the_analysis_is_asked_under_its_sensitive_purpose(self):
        self._two_segments()

        router = self._analyse()

        request = router.run.call_args.args[1]
        self.assertEqual(request.purpose, PURPOSE)
        self.assertIn("[mm:ss]", request.system)
        self.assertIn("Víctor: le mando", request.prompt)
        self.assertIn("moments", request.response_schema["properties"])
        self.assertEqual(
            router.run.call_args.kwargs["company_id"], self.meeting.company_id.id
        )
        purpose = self.env.ref("speech_analysis.purpose_speech_analysis")
        self.assertTrue(purpose.sensitive)

    def test_what_was_found_is_kept_against_the_speaker_who_said_it(self):
        self._two_segments()

        self._analyse()

        self.assertEqual(self.meeting.extract_state, "done")
        self.assertIn("quote by Friday", self.meeting.analysis_summary)
        self.assertEqual(self.meeting.analysis_topics, "Quote\nFreight")
        commitment = self.meeting.commitment_ids
        self.assertEqual(commitment.name, "Send the quote")
        self.assertEqual(commitment.partner_id, self.victor)
        self.assertEqual(str(commitment.due_date), "2026-09-25")
        self.assertEqual(commitment.at_s, 2.0)
        question = self.meeting.question_ids
        self.assertEqual(question.speaker_id.label, "SPEAKER_0")
        self.assertEqual(question.at_s, 61.0)
        self.assertFalse(question.answered)
        self.assertEqual(self.meeting.moment_ids.mapped("kind"), ["next_step"])
        rated = self.meeting.timeline_speaker_ids.filtered("partner_id")
        self.assertEqual((rated.sentiment, rated.engagement), ("positive", "high"))
        self.assertEqual(rated.interruptions, 1)

    def test_a_new_analysis_replaces_the_last(self):
        self._two_segments()
        self._analyse()

        self._analyse({"summary": "Nothing agreed.", "commitments": [], "speakers": []})

        self.assertFalse(self.meeting.commitment_ids)
        self.assertFalse(self.meeting.moment_ids)
        self.assertFalse(self.meeting.timeline_speaker_ids.filtered("sentiment"))

    def test_a_finished_recording_queues_its_analysis(self):
        with patch.object(
            type(self.meeting), "_extract_later", autospec=True
        ) as queued:
            self._two_segments()
        self.assertTrue(queued.called)

    def test_a_recording_still_running_is_not_analysed_yet(self):
        self.meeting.finished = False
        with patch.object(
            type(self.meeting), "_extract_later", autospec=True
        ) as queued:
            self._two_segments()
        queued.assert_not_called()

    def test_nothing_to_read_means_no_source(self):
        self.assertIsNone(self.meeting._get_extract_source())

    def test_whoever_cannot_read_the_owner_cannot_read_its_findings(self):
        self._two_segments()
        self._analyse()
        stranger = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "stranger",
                    "login": "speech_analysis_stranger",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        commitment = self.meeting.commitment_ids
        with self.assertRaises(AccessError):
            commitment.with_user(stranger).read(["name"])
        self.assertFalse(self.env["speech.commitment"].with_user(stranger).search([]))

    def test_the_moment_kinds_are_the_ones_the_schema_offers(self):
        kinds = [
            value
            for value, _label in self.env["speech.moment"]._fields["kind"].selection
        ]

        self.assertEqual(tuple(kinds), MOMENT_KINDS)
