from odoo import fields, models


class StockConfig(models.Model):
    _inherit = "stock.config"

    lc_journal_id = fields.Many2one(comodel_name="account.journal")
