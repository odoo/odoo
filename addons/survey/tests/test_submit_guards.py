from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.survey.tests import common


@tagged("post_install", "-at_install")
class TestSubmitGuards(common.TestSurveyCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = cls.env["survey.survey"].create(
            {
                "title": "Guarded survey",
                "access_mode": "public",
                "users_login_required": False,
            }
        )
        cls.page = cls.env["survey.question"].create(
            {
                "title": "Page one",
                "survey_id": cls.form.id,
                "is_page": True,
                "sequence": 1,
            }
        )
        cls.question = cls.env["survey.question"].create(
            {
                "title": "Say something",
                "survey_id": cls.form.id,
                "question_type": "char_box",
                "sequence": 2,
                "constr_mandatory": True,
                "constr_error_msg": "Answer required",
            }
        )

    def _answer(self):
        return self.env["survey.user_input"].create({"survey_id": self.form.id})

    def _submit(self, answer, payload):
        response = self._access_submit(self.form, answer.access_token, payload)
        return response.json().get("result")

    def _payload(self, value="hello"):
        return self._format_submission_data(self.question, value, {})

    def test_valid_submission_stores_the_answer(self):
        answer = self._answer()
        self._submit(answer, self._payload("hola"))
        line = answer.user_input_line_ids.filtered(
            lambda line: line.question_id == self.question
        )
        self.assertEqual(line.value_char_box, "hola")

    def test_missing_mandatory_answer_is_refused(self):
        answer = self._answer()
        result = self._submit(answer, self._payload(""))
        self.assertEqual(result[1]["error"], "validation")
        self.assertIn(str(self.question.id), result[1]["fields"])

    def test_finished_answer_cannot_be_submitted_again(self):
        answer = self._answer()
        answer.state = "done"
        result = self._submit(answer, self._payload())
        self.assertEqual(result[1]["error"], "unauthorized")

    def test_unknown_answer_token_is_refused(self):
        response = self._access_submit(self.form, "not-a-real-token", self._payload())
        result = response.json().get("result")
        self.assertIn("error", result[1])

    def test_submission_after_the_time_limit_is_refused(self):
        self.form.write({"is_time_limited": True, "time_limit": 1})
        answer = self._answer()
        answer.start_datetime = fields.Datetime.now() - timedelta(minutes=30)
        result = self._submit(answer, self._payload())
        self.assertEqual(result[1]["error"], "unauthorized")

    def test_submission_inside_the_grace_period_is_accepted(self):
        self.form.write({"is_time_limited": True, "time_limit": 30})
        answer = self._answer()
        answer.start_datetime = fields.Datetime.now() - timedelta(minutes=1)
        self._submit(answer, self._payload("in time"))
        line = answer.user_input_line_ids.filtered(
            lambda line: line.question_id == self.question
        )
        self.assertEqual(line.value_char_box, "in time")

    def test_time_limit_helper_ignores_untimed_surveys(self):
        from odoo.addons.survey.controllers.main import Survey

        answer = self._answer()
        self.assertFalse(Survey()._is_time_limit_exceeded(self.form, answer))
