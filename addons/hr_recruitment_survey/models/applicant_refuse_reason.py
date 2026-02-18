from odoo import models


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    def action_refuse_reason_apply(self):
        # when refusing applicants, we want to cancel all their surveys
        refused_applications = self.applicant_ids
        if self.duplicates:
            refused_applications |= self.duplicate_applicant_ids
        refused_applications._cancel_survey_user_inputs()
        return super().action_refuse_reason_apply()
