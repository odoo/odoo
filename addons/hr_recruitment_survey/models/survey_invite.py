# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', default=lambda self: self.env.context.get('active_id', None))

    def action_invite(self):
        self.ensure_one()

        if not self.applicant_id.response_id:
            response = self.applicant_id.survey_id._create_answer(partner=self.applicant_id.partner_id)
            self.applicant_id.response_id = response.id

        body = _('The survey has been sent to "%s".', self.applicant_id.partner_name)
        self.applicant_id.message_post(body=body)

        return super().action_invite()


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    applicant_id = fields.One2many('hr.applicant', 'response_id', string='Applicant')

    def _mark_done(self):
        odoobot = self.env.ref('base.partner_root')
        for user_input in self:
            if user_input.applicant_id:
                body = _('The applicant "%s" has finished the survey.', user_input.applicant_id.partner_name)
                user_input.applicant_id.message_post(body=body, author_id=odoobot.id)
        return super()._mark_done()
