from markupsafe import Markup

from odoo import fields, models
from odoo.tools.misc import clean_context


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    applicant_id = fields.Many2one(comodel_name="hr.applicant")

    def _get_done_partners_emails(self, existing_answers):
        partners_done, emails_done, answers = super()._get_done_partners_emails(
            existing_answers
        )
        if self.applicant_id.response_ids.filtered(
            lambda res: res.survey_id.id == self.survey_id.id
        ):
            if existing_answers and self.existing_mode == "resend":
                partners_done |= self.applicant_id.partner_id
        return partners_done, emails_done, answers

    def _send_mails(self, answers):
        mails = super()._send_mails(answers)
        author_env = self.with_context(lang=self.env.user.lang).env
        survey_link = self.survey_id._get_html_link(title=self.survey_id.title)
        for applicant in answers.applicant_id:
            content = author_env._(
                "The survey %(survey_link)s has been sent to %(partner_link)s",
                survey_link=survey_link,
                partner_link=applicant.partner_id._get_html_link(),
            )
            applicant.message_post(body=Markup("<p>%s</p>") % content)
        return mails

    def action_invite(self):
        self.check_singleton()
        if self.applicant_id:
            survey = self.survey_id.with_context(clean_context(self.env.context))

            if not self.applicant_id.response_ids.filtered(
                lambda res: res.survey_id.id == self.survey_id.id
            ):
                self.applicant_id.sudo().write(
                    {
                        "response_ids": (
                            self.applicant_id.response_ids
                            | survey.sudo()._create_answer(
                                partner=self.applicant_id.partner_id,
                                **self._prepare_answer_params(),
                            )
                        ).ids
                    }
                )
        return super().action_invite()
