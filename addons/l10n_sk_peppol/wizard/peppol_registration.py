from odoo import fields, models


class PeppolRegistration(models.TransientModel):
    _inherit = 'peppol.registration'

    peppol_validation_token = fields.Char(related='company_id.peppol_validation_token', readonly=False)

    def _is_email_required(self):
        return False if self.peppol_eas == '0245' else super()._is_email_required()

    def _is_phone_required(self):
        return False if self.peppol_eas == '0245' else super()._is_phone_required()

    def _get_peppol_registration_data(self):
        return {
            **super()._get_peppol_registration_data(),
            'peppol_validation_token': self.company_id.peppol_validation_token,
        }
