# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_purchase_add_mode = fields.Selection(related='product_template_id.product_purchase_add_mode', depends=['product_template_id'])
