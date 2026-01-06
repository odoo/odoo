"""
Marketplace Inherits - Odoo modellerin marketplace entegrasyonları
"""

from odoo import fields, models


class SaleOrder(models.Model):
    """Extend sale.order with marketplace data"""

    _inherit = "sale.order"

    marketplace_order_id = fields.Many2one(
        "marketplace.order", "Pazaryeri Siparişi", ondelete="set null"
    )


class AccountMove(models.Model):
    """Extend account.move with marketplace data"""

    _inherit = "account.move"

    marketplace_order_id = fields.Many2one(
        "marketplace.order", "Pazaryeri Siparişi", ondelete="set null"
    )


class StockPicking(models.Model):
    """Extend stock.picking with marketplace data"""

    _inherit = "stock.picking"

    marketplace_order_id = fields.Many2one(
        "marketplace.order", "Pazaryeri Siparişi", ondelete="set null"
    )
