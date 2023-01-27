# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    applicant_ids = fields.One2many('hr.applicant', 'response_id', string='Applicant')

    def _mark_done(self):
        odoobot = self.env.ref('base.partner_root')
        for user_input in self:
            if user_input.applicant_ids:
                body = _('The applicant "%s" has finished the survey.', user_input.applicant_ids[:1].partner_name)
                user_input.applicant_ids.message_post(body=body, author_id=odoobot.id)
        return super()._mark_done()
