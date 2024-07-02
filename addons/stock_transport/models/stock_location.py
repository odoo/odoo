from odoo import fields, models


class StockPickingBatch(models.Model):
    _inherit = 'stock.location'

    is_a_dock = fields.Boolean("Is a Dock Location")
