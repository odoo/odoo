# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, models, _
from odoo.tools.misc import clean_context


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')

    def _get_done_partners_emails(self, existing_answers):
        partners_done, emails_done, answers = super()._get_done_partners_emails(existing_answers)
        if self.applicant_id.response_ids.filtered(lambda res: res.survey_id.id == self.survey_id.id):
            if existing_answers and self.existing_mode == 'resend':
                partners_done |= self.applicant_id.partner_id
        return partners_done, emails_done, answers

    def _send_mail(self, answer):
        mail = super()._send_mail(answer)
        if answer.applicant_id:
            answer.applicant_id.message_post(body=Markup(mail.body_html))
            mail.send()
        return mail

    def action_invite(self):
        self.ensure_one()
        if self.applicant_id:
            survey = self.survey_id.with_context(clean_context(self.env.context))

            if not self.applicant_id.response_ids.filtered(lambda res: res.survey_id.id == self.survey_id.id):
                self.applicant_id.sudo().write({
                    'response_ids': (self.applicant_id.response_ids | survey.sudo()._create_answer(partner=self.applicant_id.partner_id,
                        **self._get_answers_values())).ids
                })

            partner = self.applicant_id.partner_id
            survey_link = survey._get_html_link(title=survey.title)
            partner_link = partner._get_html_link()
            content = _('The survey %(survey_link)s has been sent to %(partner_link)s',
                survey_link=survey_link,
                partner_link=partner_link,
            )
            body = Markup('<p>%s</p>') % content
            self.applicant_id.message_post(body=body)
        return super().action_invite()
