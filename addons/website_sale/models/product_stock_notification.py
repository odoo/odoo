# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductStockNotification(models.Model):
    _name = "product.stock.notification"
    _description = "Product Stock Notification"
    _table = "product_stock_notification_rel"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    website_id = fields.Many2one("website", required=True, ondelete="cascade")

    _product_stock_notification_unique = models.Constraint(
        "UNIQUE (product_id, website_id, partner_id)",
        "A stock notification can only exist once per product, website and partner.",
    )
