# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    applicant_id = fields.One2many('hr.applicant', 'response_id', string='Applicant')

    def _mark_done(self):
        for user_input in self:
            if user_input.applicant_id:
                user_input.applicant_id._message_log(body=_('The applicant "%s" has finished the survey.', user_input.applicant_id.partner_name))
        return super()._mark_done()
