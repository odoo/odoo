from datetime import timedelta

from odoo import Command, _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        related="job_id.survey_id",
        string="Survey",
        readonly=True,
    )
    response_ids = fields.One2many(
        comodel_name="survey.user_input",
        inverse_name="applicant_id",
        string="Responses",
    )

    def action_print_survey(self):
        self.check_singleton()
        sorted_interviews = self.response_ids.filtered(
            lambda i: i.survey_id == self.survey_id
        ).sorted(lambda i: i.create_date, reverse=True)
        if not sorted_interviews:
            _debug.logic("print_survey", by="blank", applicant=self)
            action = self.survey_id.action_print_survey()
            action["target"] = "new"
            return action

        answered_interviews = sorted_interviews.filtered(lambda i: i.state == "done")
        if answered_interviews:
            _debug.logic("print_survey", by="answered", applicant=self)
            action = self.survey_id.action_print_survey(answer=answered_interviews[0])
            action["target"] = "new"
            return action
        _debug.logic("print_survey", by="latest_unanswered", applicant=self)
        action = self.survey_id.action_print_survey(answer=sorted_interviews[0])
        action["target"] = "new"
        return action

    def action_send_survey(self):
        self.check_singleton()

        if not self.partner_id:
            if not self.partner_name:
                _debug.logic("send_survey_refused", reason="no_name", applicant=self)
                raise UserError(_("Please provide an applicant name."))
            _debug.lifecycle("partner_created_for_survey", applicant=self)
            self.partner_id = (
                self.env["res.partner"]
                .sudo()
                .create(
                    {
                        "is_company": False,
                        "name": self.partner_name,
                        "email": self.email_from,
                        "phone_ids": [Command.set(self.phone_ids.ids)],
                    }
                )
            )

        self.survey_id.check_validity()
        template = self.env.ref(
            "hr_recruitment_survey.mail_template_applicant_interview_invite",
            raise_if_not_found=False,
        )
        local_context = {
            "default_applicant_id": self.id,
            "default_partner_ids": self.partner_id.ids,
            "default_survey_id": self.survey_id.id,
            "default_use_template": bool(template),
            "default_template_id": (template and template.id) or False,
            "default_email_layout_xmlid": "mail.mail_notification_light",
            "default_deadline": fields.Datetime.now() + timedelta(days=15),
        }

        _debug.pipeline(
            "send_survey",
            applicant=self,
            survey=self.survey_id,
            has_template=bool(template),
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Send an interview"),
            "view_mode": "form",
            "res_model": "survey.invite",
            "target": "new",
            "context": local_context,
        }
