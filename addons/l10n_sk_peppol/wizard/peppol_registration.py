from odoo import api, fields, models


class PeppolRegistration(models.TransientModel):
    _inherit = 'peppol.registration'

    peppol_validation_token = fields.Char(
        compute='_compute_peppol_validation_token',
        inverse='_inverse_peppol_validation_token',
        readonly=False,
    )

    @api.depends('company_id.peppol_validation_token', 'use_parent_connection_selection', 'parent_company_id.peppol_validation_token')
    def _compute_peppol_validation_token(self):
        for wizard in self:
            if token := wizard.company_id.peppol_validation_token:
                wizard.peppol_validation_token = token
            elif wizard.use_parent_connection_selection == 'use_parent':
                wizard.peppol_validation_token = wizard.parent_company_id.peppol_validation_token

    def _inverse_peppol_validation_token(self):
        for wizard in self:
            wizard.company_id.peppol_validation_token = wizard.peppol_validation_token

    def _is_email_required(self):
        return False if self.peppol_eas == '0245' else super()._is_email_required()

    def _get_peppol_registration_data(self):
        return {
            **super()._get_peppol_registration_data(),
            'peppol_validation_token': self.company_id.peppol_validation_token,
        }
