# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrderTag(models.Model):
    _name = "purchase.order.tag"
    _description = "Purchase Order Tag"

    name = fields.Char(string="Name", required=True, translate=True)
    color = fields.Char(string="Color", default='#3C3C3C')
    purchase_order_ids = fields.Many2many(
        'purchase.order', string='Purchase Orders using this Tag',
    )
