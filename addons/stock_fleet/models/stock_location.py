from odoo import fields, models
from odoo.addons import stock


class StockLocation(stock.StockLocation):

    is_a_dock = fields.Boolean("Is a Dock Location")
