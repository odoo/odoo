from odoo import fields, models


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    def action_refuse_reason_apply(self):
        refused_applications = self.applicant_ids
        if self.duplicates_count and self.duplicates:
            refused_applications |= self.duplicate_applicant_ids

        partner_ids = refused_applications.mapped('partner_id').ids
        survey_inputs = self.env['survey.user_input'].search([
            ('partner_id', 'in', partner_ids),
        ])
        if survey_inputs:
            survey_inputs.write({'deadline': fields.Datetime.now()})
        return super().action_refuse_reason_apply()
