from odoo import fields, models


class L10nTwEdiEcpayConfig(models.Model):
    _name = "l10n_tw_edi_ecpay.config"
    _description = "A company's l10n tw edi ecpay configuration"
    _inherit = ["mixin.company.config"]

    l10n_tw_edi_ecpay_staging_mode = fields.Boolean(
        string="Staging mode",
        groups="base.group_system",
    )
    l10n_tw_edi_ecpay_merchant_id = fields.Char(
        string="MerchantID",
        groups="base.group_system",
    )
    l10n_tw_edi_ecpay_hashkey = fields.Char(
        string="Hashkey",
        groups="base.group_system",
    )
    l10n_tw_edi_ecpay_hashIV = fields.Char(
        string="HashIV",
        groups="base.group_system",
    )
