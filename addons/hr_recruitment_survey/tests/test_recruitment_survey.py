from markupsafe import Markup

from odoo.exceptions import AccessError
from odoo.modules.module import get_module_path, load_script
from odoo.tests import Form, common, tagged
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("security")
class TestRecruitmentSurvey(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.hr_recruitment_manager = mail_new_test_user(
            cls.env,
            name="Gustave Doré",
            login="hr_recruitment_manager",
            email="hr_recruitment.manager@example.com",
            groups="hr_recruitment.group_hr_recruitment_manager",
        )
        cls.hr_recruitment_user = mail_new_test_user(
            cls.env,
            name="Lukas Peeters",
            login="hr_recruitment_user",
            email="hr_recruitment.user@example.com",
            groups="hr_recruitment.group_hr_recruitment_user",
        )
        cls.hr_recruitment_interviewer = mail_new_test_user(
            cls.env,
            name="Eglantine Ask",
            login="hr_recruitment_interviewer",
            email="hr_recruitment.interviewer@example.com",
            groups="hr_recruitment.group_hr_recruitment_interviewer",
        )

        cls.department_admins = cls.env["hr.department"].create({"name": "Admins"})
        cls.survey_sysadmin, cls.survey_custom = cls.env["survey.survey"].create(
            [
                {
                    "title": "Questions for Sysadmin job offer",
                    "survey_type": "recruitment",
                },
                {
                    "title": "Survey of type custom for security tests purpose",
                    "survey_type": "custom",
                },
            ]
        )
        cls.question_ft = cls.env["survey.question"].create(
            {
                "title": "Test Free Text",
                "survey_id": cls.survey_sysadmin.id,
                "sequence": 2,
                "question_type": "text_box",
            }
        )
        cls.job = cls.env["hr.job"].create(
            {
                "name": "Technical worker",
                "survey_id": cls.survey_sysadmin.id,
                "description": None,
            }
        )
        cls.job_applicant = cls.env["hr.applicant"].create(
            {
                "partner_name": "Jane Doe",
                "email_from": "customer@example.com",
                "department_id": cls.department_admins.id,
                "job_id": cls.job.id,
            }
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_send_survey(self):
        Answer = self.env["survey.user_input"]
        invite_recruitment = self._prepare_invite(
            self.survey_sysadmin, self.job_applicant
        )
        invite_recruitment.action_invite()

        self.assertEqual(invite_recruitment.applicant_id, self.job_applicant)
        self.assertNotEqual(self.job_applicant.response_ids.ids, False)
        answers = Answer.search([("survey_id", "=", self.survey_sysadmin.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(self.job_applicant.response_ids, answers)
        self.assertSetEqual(
            set(answers.mapped("email")), {self.job_applicant.email_from}
        )

        invite_recruitment.with_user(self.hr_recruitment_manager).action_invite()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_manager).read(["title"])

        # Officer: unrestricted access to recruitment surveys, no interviewer gate.
        invite_recruitment.with_user(self.hr_recruitment_user).action_invite()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_user).read(["title"])

        # Interviewer: gated on being set as interviewer, on the job or the applicant.
        user = self.hr_recruitment_interviewer
        with self.assertRaises(AccessError):
            invite_recruitment.with_user(user).action_invite()
        self.job.interviewer_ids = user
        invite_recruitment.with_user(user).action_invite()
        self.job.interviewer_ids = False
        with self.assertRaises(AccessError):
            invite_recruitment.with_user(user).action_invite()
        self.job_applicant.interviewer_ids = user
        invite_recruitment.with_user(user).action_invite()

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_print_survey(self):
        action_print = self.job_applicant.action_print_survey()
        self.assertEqual(action_print["type"], "ir.actions.act_url")
        self.job_applicant.response_ids = self.env["survey.user_input"].create(
            {"survey_id": self.survey_sysadmin.id}
        )
        action_print_with_response = self.job_applicant.action_print_survey()
        self.assertIn(
            self.job_applicant.response_ids.access_token,
            action_print_with_response["url"],
        )

        with self.assertRaises(AccessError):
            self.job_applicant.with_user(
                self.hr_recruitment_interviewer
            ).action_print_survey()
        self.job_applicant.with_user(self.hr_recruitment_manager).action_print_survey()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(
                self.hr_recruitment_manager
            ).action_print_survey()

        # Officer: unrestricted access to recruitment surveys, no interviewer gate.
        self.job_applicant.with_user(self.hr_recruitment_user).action_print_survey()

    def test_invitation_link_stays_out_of_the_applicant_thread(self):
        invite = self._prepare_invite(self.survey_sysadmin, self.job_applicant)
        invite.action_invite()
        answer = self.job_applicant.response_ids
        self.assertTrue(answer.access_token)

        messages = (
            self.env["mail.message"]
            .with_user(self.hr_recruitment_user)
            .search(
                [
                    ("model", "=", self.job_applicant._name),
                    ("res_id", "=", self.job_applicant.id),
                ]
            )
        )
        for message in messages:
            self.assertNotIn(answer.access_token, str(message.body))
        summaries = messages.filtered(
            lambda message: self.survey_sysadmin.title in str(message.body)
        )
        self.assertEqual(len(summaries), 1)

        mails = self.env["mail.mail"].sudo().search([("subject", "!=", False)])
        self.assertTrue(
            mails.filtered(lambda mail: answer.access_token in str(mail.body_html))
        )

    def test_migration_moves_posted_invitations_out_of_the_thread(self):
        script = load_script(
            f"{get_module_path('hr_recruitment_survey')}/migrations/1.1/post-migrate.py",
            "hr_recruitment_survey_1_1_post_migrate",
        )
        leaked = self.job_applicant.message_post(
            body=Markup('<p><a href="%s">Start</a></p>')
            % "https://example.com/survey/start/x?answer_token=secret",
        )
        summary = self.job_applicant.message_post(body="The survey has been sent")
        self.env.flush_all()

        script.migrate(self.env.cr, "19.0.1.0")
        self.env.invalidate_all()

        self.assertEqual(leaked.message_type, "user_notification")
        self.assertEqual(summary.message_type, "notification")

    def test_new_survey_sets_recruitment_type(self):
        action = self.job.with_user(self.hr_recruitment_manager).action_new_survey()
        survey = self.env["survey.survey"].browse(action["res_id"])
        self.assertEqual(survey.survey_type, "recruitment")

    def _prepare_invite(self, survey, applicant):
        survey.write({"access_mode": "public", "users_login_required": False})
        return Form.from_action(self.env, applicant.action_send_survey()).save()
