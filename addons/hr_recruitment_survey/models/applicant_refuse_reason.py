from odoo import models


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    def action_refuse_reason_apply(self):
        refused_applications = self.applicant_ids
        if self.duplicates_count and self.duplicates:
            refused_applications |= self.duplicate_applicant_ids

        for application in refused_applications:
            survey_inputs = self.env['survey.user_input'].search([
                ('partner_id', '=', application.partner_id.id)
            ])
            if survey_inputs:
                survey_inputs.write({'expired': True})

        return super().action_refuse_reason_apply()
