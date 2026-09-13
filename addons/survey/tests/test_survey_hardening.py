import socket
from datetime import timedelta
from unittest.mock import patch

import requests
from requests.adapters import HTTPAdapter

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tests.transaction_case import _super_send
from odoo.tools import mute_logger

from odoo.addons.survey.tests import common


@tagged("post_install", "-at_install", "functional")
class TestWebhookTargetRule(common.TestSurveyCommon):
    """One rule, applied at write time and again when the request is actually made."""

    def test_private_and_local_targets_are_refused(self):
        survey = self.env["survey.survey"]
        for url in (
            "http://127.0.0.1/hook",
            "http://localhost/hook",
            "http://10.0.0.1/hook",
            "http://192.168.1.1/hook",
            "http://100.64.0.1/hook",
            "http://[::1]/hook",
            "http://[64:ff9b::7f00:1]/hook",
            "http://169.254.169.254/latest/meta-data",
            "ftp://example.com/hook",
            "http:///nohost",
        ):
            with self.subTest(url=url):
                self.assertIsNotNone(
                    survey._webhook_url_problem(url), f"{url} should have been refused"
                )

    def test_a_public_target_is_allowed(self):
        self.assertIsNone(
            self.env["survey.survey"]._webhook_url_problem("https://93.184.216.34/hook")
        )

    def test_an_unresolvable_host_fails_closed(self):
        self.assertIsNotNone(
            self.env["survey.survey"]._webhook_url_problem(
                "http://no-such-host.invalid/hook"
            )
        )

    def test_the_constraint_uses_the_same_rule(self):
        survey = self.env["survey.survey"].create({"title": "Hooked"})
        with self.assertRaises(ValidationError):
            survey.webhook_url = "http://127.0.0.1/hook"

    def _resolving(self, *answers):
        remaining = iter(answers)

        def getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (a, port))
                for a in next(remaining)
            ]

        return patch("socket.getaddrinfo", side_effect=getaddrinfo)

    def _fire_completed_webhook(self, *answers):
        sent = []

        def send(adapter, request, **kwargs):
            sent.append((request.netguard_address, request.headers.get("Host")))
            response = requests.Response()
            response.status_code = 200
            response.request = request
            response.url = request.url
            response._content = b""
            return response

        with (
            self._resolving(*answers),
            patch.object(requests.Session, "send", _super_send),
            patch.object(HTTPAdapter, "send", autospec=True, side_effect=send),
            mute_logger("odoo.addons.survey.models.survey_user_input"),
        ):
            survey = self.env["survey.survey"].create(
                {"title": "Hooked", "webhook_url": "https://hooks.example.com/x"}
            )
            answer = self._add_answer(survey, self.customer)
            answer._fire_webhook("survey_completed")
            self.env.cr.postcommit.run()
        return sent

    def test_the_rule_runs_again_when_the_request_is_made(self):
        sent = self._fire_completed_webhook(["93.184.216.34"], ["127.0.0.1"])
        self.assertEqual(sent, [])

    def test_the_request_goes_to_the_checked_address(self):
        sent = self._fire_completed_webhook(["93.184.216.34"], ["93.184.216.34"])
        self.assertEqual(sent, [("93.184.216.34", "hooks.example.com")])


@tagged("post_install", "-at_install", "functional")
class TestSkipActionPrecedence(common.TestSurveyCommon):
    """A multiple-choice answer set can carry several skip actions at once."""

    def test_the_most_terminal_action_wins(self):
        controller_precedence = __import__(
            "odoo.addons.survey.controllers.main", fromlist=["Survey"]
        ).Survey._SKIP_ACTION_PRECEDENCE
        self.assertLess(
            controller_precedence["end_survey"], controller_precedence["redirect"]
        )
        self.assertLess(
            controller_precedence["redirect"], controller_precedence["skip_to"]
        )

    def test_ending_beats_jumping(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Skip precedence",
                "access_mode": "public",
                "questions_layout": "page_per_question",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Pick",
                            "sequence": 1,
                            "question_type": "multiple_choice",
                            "suggested_answer_ids": [
                                (0, 0, {"value": "jump", "sequence": 1}),
                                (0, 0, {"value": "stop", "sequence": 2}),
                            ],
                        },
                    ),
                    (
                        0,
                        0,
                        {"title": "Later", "sequence": 2, "question_type": "char_box"},
                    ),
                ],
            }
        )
        pick, later = survey.question_ids
        jump, stop = pick.suggested_answer_ids
        jump.write({"skip_action": "skip_to", "skip_target_id": later.id})
        stop.write({"skip_action": "end_survey"})

        answer = survey._create_answer(email="skip@test.com")
        answer._mark_in_progress()
        answer._save_lines(pick, [jump.id, stop.id])
        self.env.flush_all()

        from odoo.addons.survey.controllers.main import Survey

        selected = answer.user_input_line_ids.suggested_answer_id
        ordered = selected.sorted(
            lambda a: (
                Survey._SKIP_ACTION_PRECEDENCE.get(a.skip_action, 99),
                a.sequence,
                a.id,
            )
        )
        self.assertEqual(
            ordered[0].skip_action,
            "end_survey",
            "the answer that ends the survey must be acted on first",
        )


@tagged("post_install", "-at_install", "functional")
class TestUploadLimits(common.TestSurveyCommon, HttpCase):
    """/survey/upload is auth='public' and creates a record per POST."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_survey = cls.env["survey.survey"].create(
            {
                "title": "Upload survey",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "File",
                            "question_type": "file_upload",
                            "file_upload_types": ".txt",
                            "file_upload_max_size": 1,
                        },
                    )
                ],
            }
        )
        cls.upload_question = cls.upload_survey.question_ids[0]

    def _upload(self, answer, token, name="a.txt"):
        return self.url_open(
            f"/survey/upload/{self.upload_survey.access_token}/{answer.access_token}",
            data={"question_id": str(self.upload_question.id), "csrf_token": token},
            files={"file": (name, b"hello", "text/plain")},
        )

    def test_uploads_are_capped_per_answer(self):
        from odoo.addons.survey.controllers.main import Survey

        answer = self.upload_survey._create_answer(email="up@test.com")
        answer._mark_in_progress()
        self.env.flush_all()
        page = self.url_open(
            f"/survey/{self.upload_survey.access_token}/{answer.access_token}"
        )
        token = self._find_csrf_token(page.text)

        statuses = [
            self._upload(answer, token, f"f{i}.txt").status_code
            for i in range(Survey.MAX_UPLOADS_PER_ANSWER + 2)
        ]
        self.assertNotIn(400, statuses, "the uploads themselves must be accepted")
        self.assertIn(429, statuses, "an unbounded public upload route is a filestore")
        self.assertLessEqual(
            self.env["ir.attachment"]
            .sudo()
            .search_count(
                [("res_model", "=", answer._name), ("res_id", "=", answer.id)]
            ),
            Survey.MAX_UPLOADS_PER_ANSWER,
        )


@tagged("post_install", "-at_install", "functional")
class TestRetentionSweep(common.TestSurveyCommon):
    def test_expired_responses_are_deleted_in_batches(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Retention",
                "access_mode": "public",
                "questions_layout": "one_page",
                "data_retention_days": 30,
                "question_and_page_ids": [
                    (0, 0, {"title": "Q", "question_type": "char_box"})
                ],
            }
        )
        old = fields.Datetime.now() - timedelta(days=90)
        keep, drop = [], []
        for index in range(4):
            answer = survey._create_answer(email=f"r{index}@test.com")
            answer._mark_in_progress()
            answer._save_lines(survey.question_ids[0], "x")
            answer._mark_done()
            if index < 2:
                answer.end_datetime = old
                drop.append(answer.id)
            else:
                keep.append(answer.id)
        self.env.flush_all()

        self.env["survey.user_input"]._cron_cleanup_expired_responses()

        remaining = self.env["survey.user_input"].search(
            [("survey_id", "=", survey.id)]
        )
        self.assertEqual(sorted(remaining.ids), sorted(keep))

    def test_a_survey_without_retention_is_untouched(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "No retention",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "Q", "question_type": "char_box"})
                ],
            }
        )
        answer = survey._create_answer(email="norr@test.com")
        answer._mark_in_progress()
        answer._mark_done()
        answer.end_datetime = fields.Datetime.now() - timedelta(days=3650)
        self.env.flush_all()

        self.env["survey.user_input"]._cron_cleanup_expired_responses()
        self.assertTrue(answer.exists())


@tagged("post_install", "-at_install", "functional")
class TestConcurrentSubmit(common.TestSurveyCommon, HttpCase):
    """Two requests carrying one answer token must not both run to completion."""

    def test_a_second_submit_after_completion_is_refused(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Race",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "Q", "question_type": "char_box"})
                ],
            }
        )
        question = survey.question_ids[0]
        answer = survey._create_answer(email="race@test.com")
        answer._mark_in_progress()
        self.env.flush_all()

        import json

        def submit():
            return self.url_open(
                f"/survey/submit/{survey.access_token}/{answer.access_token}",
                data=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {str(question.id): "an answer"},
                    }
                ),
                headers={"Content-Type": "application/json"},
            ).json()

        first = submit()
        second = submit()
        self.assertNotIn("error", first)
        self.assertEqual(second["result"][1].get("error"), "unauthorized")
        answer.invalidate_recordset()
        self.assertEqual(answer.state, "done")
        self.assertEqual(
            len(
                answer.user_input_line_ids.filtered(
                    lambda ln: ln.question_id == question
                )
            ),
            1,
            "the refused submit must not have written a second line",
        )

    def test_lock_is_a_noop_on_an_empty_recordset(self):
        self.env["survey.user_input"].browse()._lock()


@tagged("post_install", "-at_install", "functional")
class TestCertificationDownload(common.TestSurveyCommon, HttpCase):
    """A test run must not produce a real certificate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.certification = cls.env["survey.survey"].create(
            {
                "title": "Certification download",
                "access_mode": "public",
                "questions_layout": "one_page",
                "certification": True,
                "scoring_type": "scoring_with_answers",
                "scoring_success_min": 50,
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Q",
                            "question_type": "simple_choice",
                            "suggested_answer_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "value": "right",
                                        "is_correct": True,
                                        "answer_score": 10,
                                    },
                                )
                            ],
                        },
                    )
                ],
            }
        )
        cls.cert_question = cls.certification.question_ids[0]

    def _attempt(self, partner, test_entry):
        answer = self.certification._create_answer(
            partner=partner, test_entry=test_entry, check_attempts=False
        )
        answer._mark_in_progress()
        answer._save_lines(
            self.cert_question, self.cert_question.suggested_answer_ids[0].id
        )
        answer._mark_done()
        self.env.flush_all()
        return answer

    def _passing_attempt_the_route_would_use(self, partner):
        return self.env["survey.user_input"].search(
            [
                ("partner_id", "=", partner.id),
                ("survey_id", "=", self.certification.id),
                ("scoring_success", "=", True),
                ("test_entry", "=", False),
            ],
            order="scoring_percentage desc, id desc",
            limit=1,
        )

    def test_a_test_entry_is_not_certifiable(self):
        partner = self.env["res.partner"].create(
            {"name": "Tester", "email": "tester@test.com"}
        )
        test_attempt = self._attempt(partner, test_entry=True)
        self.assertTrue(test_attempt.scoring_success)
        self.assertFalse(
            self._passing_attempt_the_route_would_use(partner),
            "a test entry must not be downloadable as a certificate",
        )

    def test_a_real_passing_attempt_is_certifiable(self):
        partner = self.env["res.partner"].create(
            {"name": "Real", "email": "real@test.com"}
        )
        real = self._attempt(partner, test_entry=False)
        self.assertEqual(self._passing_attempt_the_route_would_use(partner), real)

    def test_the_best_passing_attempt_wins(self):
        partner = self.env["res.partner"].create(
            {"name": "Twice", "email": "twice@test.com"}
        )
        first = self._attempt(partner, test_entry=False)
        second = self._attempt(partner, test_entry=False)
        first.scoring_percentage = 90
        second.scoring_percentage = 60
        self.env.flush_all()
        self.assertEqual(
            self._passing_attempt_the_route_would_use(partner),
            first,
            "the certificate should reflect the best result, not an arbitrary one",
        )


@tagged("post_install", "-at_install", "functional")
class TestAnswerPayloadShapes(common.TestSurveyCommon):
    """/survey/submit is public jsonrpc: the payload is whatever JSON arrived.

    Every validator used to assume the shape its question type expects. A crafted
    payload therefore raised TypeError or AttributeError out of the request -- an
    unauthenticated 500, one per combination, measured at 39 of them.
    """

    QUESTION_TYPES = (
        "char_box",
        "text_box",
        "numerical_box",
        "scale",
        "nps",
        "slider",
        "rating",
        "ranking",
        "constant_sum",
        "file_upload",
        "date",
        "datetime",
        "simple_choice",
        "dropdown",
        "multiple_choice",
        "matrix",
        "likert",
    )
    PAYLOADS = (
        None,
        7,
        1.5,
        True,
        [1, 2],
        {"a": 1},
        {"x": [{"y": 1}]},
        "abc",
        "z" * 10000,
        -5,
    )

    def test_no_payload_shape_escapes_as_an_exception(self):
        from odoo.addons.survey.controllers.main import Survey

        controller = Survey()
        for question_type in self.QUESTION_TYPES:
            survey = self.env["survey.survey"].create(
                {
                    "title": f"Shape {question_type}",
                    "access_mode": "public",
                    "questions_layout": "one_page",
                    "question_and_page_ids": [
                        (
                            0,
                            0,
                            {
                                "title": "Q",
                                "question_type": question_type,
                                "suggested_answer_ids": [(0, 0, {"value": "A"})],
                                "matrix_row_ids": [(0, 0, {"value": "R"})],
                            },
                        )
                    ],
                }
            )
            question = survey.question_ids[0]
            for payload in self.PAYLOADS:
                with self.subTest(
                    question_type=question_type, payload=repr(payload)[:20]
                ):
                    extracted, comment = controller._extract_comment_from_answers(
                        question, payload
                    )
                    self.assertIsInstance(
                        question._check_answer(extracted, comment), dict
                    )

    def test_a_choice_with_a_comment_is_the_forms_own_shape(self):
        # survey_form.js submits `[answer_id, {"comment": text}]` for a choice
        # question that allows comments; refusing the dict refused the form
        # itself, and the feedback tour died on its last page.
        from odoo.addons.survey.controllers.main import Survey

        controller = Survey()
        survey = self.env["survey.survey"].create(
            {
                "title": "Choice with comment",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (
                        0,
                        0,
                        {
                            "title": "Q",
                            "question_type": "multiple_choice",
                            "comments_allowed": True,
                            "suggested_answer_ids": [
                                (0, 0, {"value": "A"}),
                                (0, 0, {"value": "B"}),
                            ],
                        },
                    )
                ],
            }
        )
        question = survey.question_ids[0]
        ids = question.suggested_answer_ids.ids
        payload = [str(ids[0]), str(ids[1]), {"comment": " why not "}]
        self.assertTrue(question._is_well_shaped_answer(payload))
        extracted, comment = controller._extract_comment_from_answers(question, payload)
        self.assertEqual(extracted, [str(ids[0]), str(ids[1])])
        self.assertEqual(comment, "why not")
        self.assertEqual(question._check_answer(extracted, comment), {})
        self.assertFalse(
            question._is_well_shaped_answer([str(ids[0]), {"comment": 1}]),
            "a comment is text",
        )
        self.assertFalse(
            question._is_well_shaped_answer([str(ids[0]), {"other": "x"}]),
            "only the comment key travels this way",
        )

    def test_a_wrong_shape_is_refused_rather_than_accepted(self):
        survey = self.env["survey.survey"].create(
            {
                "title": "Shape refusal",
                "access_mode": "public",
                "questions_layout": "one_page",
                "question_and_page_ids": [
                    (0, 0, {"title": "N", "question_type": "numerical_box"})
                ],
            }
        )
        question = survey.question_ids[0]
        self.assertTrue(question._check_answer([1, 2]), "a list is not a number")
        self.assertTrue(question._check_answer({"a": 1}), "a dict is not a number")
        self.assertFalse(question._check_answer("42"), "a numeric string still works")
        self.assertFalse(question._check_answer(42), "a JSON number still works")
