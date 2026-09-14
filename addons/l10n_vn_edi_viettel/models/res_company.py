from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_vn_edi_password": "l10n_vn_edi_password",
        "l10n_vn_edi_token": "l10n_vn_edi_token",
    }

    l10n_vn_edi_username = fields.Char(
        string="SInvoice Username",
        groups="base.group_system",
    )
    l10n_vn_edi_password = fields.Char(
        string="Sinvoice Password",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )
    l10n_vn_edi_token = fields.Char(
        string="Sinvoice Access Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        readonly=True,
        groups="base.group_system",
    )
    l10n_vn_edi_token_expiry = fields.Datetime(
        string="Sinvoice Access Token Expiration Date",
        readonly=True,
        groups="base.group_system",
    )
