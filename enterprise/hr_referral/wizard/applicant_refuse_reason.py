from odoo import models, _


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    def action_refuse_reason_apply(self):
        for applicant in self.applicant_ids:
            if applicant.ref_user_id:
                applicant._send_notification(
                    body=_("Sorry, your referral %s has been refused in the recruitment process.", applicant.partner_name),
                    action_value='hr_referral.action_hr_refused_applicant_employee_referral',
                )
        self.applicant_ids.write({'referral_state': 'closed'})
        return super().action_refuse_reason_apply()
