"""
Q-Commerce Model Genişletmeleri

sale.order ve stock.picking modellerini genişlet.
"""

from odoo import api, fields, models


class SaleOrderQCommerceInherit(models.Model):
    """sale.order - Q-Commerce Genişletmesi"""

    _inherit = "sale.order"

    qcommerce_order_id = fields.Many2one("qcommerce.order", "Hızlı Teslimat Siparişi")
    qcommerce_delivered_date = fields.Datetime("Hızlı Teslimat Teslimat Tarihi")


class StockPickingQCommerceInherit(models.Model):
    """stock.picking - Q-Commerce Genişletmesi"""

    _inherit = "stock.picking"

    qcommerce_order_id = fields.Many2one("qcommerce.order", "Hızlı Teslimat Siparişi")
