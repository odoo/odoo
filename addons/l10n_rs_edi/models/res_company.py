from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_rs_edi_api_key": "l10n_rs_edi_api_key",
    }

    l10n_rs_edi_api_key = fields.Char(
        string="eFaktura API Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
    )
    l10n_rs_edi_demo_env = fields.Boolean(
        string="Use Demo Environment",
        default=True,
    )
