from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_vn_edi_username = fields.Char(
        string="SInvoice Username",
        groups="base.group_system",
    )
    l10n_vn_edi_password = fields.Char(
        string="Sinvoice Password",
        groups="base.group_system",
    )
    l10n_vn_edi_token = fields.Char(
        string="Sinvoice Access Token",
        readonly=True,
        groups="base.group_system",
    )
    l10n_vn_edi_token_expiry = fields.Datetime(
        string="Sinvoice Access Token Expiration Date",
        readonly=True,
        groups="base.group_system",
    )
