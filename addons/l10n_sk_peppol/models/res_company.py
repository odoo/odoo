from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    peppol_validation_token = fields.Char(
        groups="account.group_account_invoice",
        help="Verification token used to authenticate the user.",
    )

    def _get_connection_params(self, peppol_identifier, public_key, auth_token):
        # EXTENDS account_peppol
        return {
            "peppol_validation_token": self.peppol_validation_token,
            **super()._get_connection_params(peppol_identifier, public_key, auth_token)
        }
