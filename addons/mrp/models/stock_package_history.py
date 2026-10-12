from odoo import fields, models


class StockPackageHistory(models.Model):
    _inherit = 'stock.package.history'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', index=True)
