# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    eway_bill_number = fields.Char("EWay Bill", copy=False)
    shiprocket_orders = fields.Char(
        string="Shiprocket Order(s)",
        copy=False, readonly=True,
        help="Store shiprocket order(s) in a (+) separated string, used in cancelling the order."
    )
