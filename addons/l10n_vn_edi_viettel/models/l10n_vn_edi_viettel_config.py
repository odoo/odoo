from odoo import fields, models


class L10nVnEdiViettelConfig(models.Model):
    _name = "l10n_vn_edi_viettel.config"
    _description = "A company's l10n vn edi viettel configuration"
    _inherit = ["mixin.company.config"]

    l10n_vn_edi_username = fields.Char(
        string="SInvoice Username",
        groups="base.group_system",
    )
    l10n_vn_edi_token_expiry = fields.Datetime(
        string="Sinvoice Access Token Expiration Date",
        readonly=True,
        groups="base.group_system",
    )
