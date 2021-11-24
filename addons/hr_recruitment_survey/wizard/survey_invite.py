# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    def _get_default_applicant(self):
        if self.env.context.get('active_model') == 'hr.applicant' and 'active_id' in self.env.context:
            return self.env.context.get('active_id')
        else:
            return None

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', default=_get_default_applicant)

    def action_invite(self):
        self.ensure_one()

        if self.applicant_id:
            if not self.applicant_id.response_id:
                response = self.applicant_id.survey_id._create_answer(partner=self.applicant_id.partner_id)
                self.applicant_id.response_id = response.id
            body = _('The survey has been sent to "%s".', self.applicant_id.partner_name)
            self.applicant_id.message_post(body=body)

        return super().action_invite()
