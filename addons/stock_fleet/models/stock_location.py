from odoo import fields, models


class StockLocation(models.Model):
    _inherit = ['stock.location']

    is_a_dock = fields.Boolean("Is a Dock Location")
