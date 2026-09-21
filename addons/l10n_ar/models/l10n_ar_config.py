from odoo import fields, models


class L10nArConfig(models.Model):
    _name = "l10n_ar.config"
    _description = "A company's l10n ar configuration"
    _inherit = ["mixin.company.config"]

    l10n_ar_afip_start_date = fields.Date(string="Activities Start")
