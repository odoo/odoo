from odoo import fields, models


class L10nAuConfig(models.Model):
    _name = "l10n_au.config"
    _description = "A company's l10n au configuration"
    _inherit = ["mixin.company.config"]

    l10n_au_is_gst_registered = fields.Boolean(
        string="Australia GST registered",
        help="Enable if your company is registered for GST.",
    )
    l10n_au_trading_name = fields.Char(
        string="Trading Name",
        help="The trading name of the company.",
    )
