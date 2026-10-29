from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mitid_kyc_status = fields.Selection(related='company_id.mitid_kyc_status')

    def button_deregister_nemhandel_participant(self):
        # Reset the kyc status
        self.company_id.mitid_kyc_status = False
        return super().button_deregister_nemhandel_participant()
