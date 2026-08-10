from odoo import fields, models


class PeppolRegistration(models.TransientModel):
    _inherit = 'peppol.registration'

    peppol_validation_token = fields.Char(compute='_compute_peppol_validation_token', readonly=False)

    def _compute_peppol_validation_token(self):
        for wizard in self:
            if token := wizard.company_id.peppol_validation_token:
                wizard.peppol_validation_token = token
            elif wizard.use_parent_connection_selection == 'use_parent':
                wizard.peppol_validation_token = wizard.parent_company_id.peppol_validation_token

    def _is_email_required(self):
        return False if self.peppol_eas == '0245' else super()._is_email_required()

    def _get_peppol_registration_data(self):
        return {
            **super()._get_peppol_registration_data(),
            'peppol_validation_token': self.company_id.peppol_validation_token,
        }
