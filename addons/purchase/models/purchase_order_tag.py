# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class PurchaseOrderTag(models.Model):
    _name = "purchase.order.tag"
    _description = "Purchase Order Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string="Name", required=True, translate=True)
    color = fields.Integer(string="Color", default=_get_default_color)
    purchase_order_ids = fields.Many2many(
        'purchase.order', string='Purchase Orders using this Tag',
    )

    _name_uniq = models.Constraint(
        'unique (name)',
        'Tag name already exists!',
    )
