from odoo import fields, models


class L10nSkConfig(models.Model):
    _name = "l10n_sk.config"
    _description = "A company's l10n sk configuration"
    _inherit = ["mixin.company.config"]

    trade_registry = fields.Char()
    income_tax_id = fields.Char(string="Income Tax ID")
