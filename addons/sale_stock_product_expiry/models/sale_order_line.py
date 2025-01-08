# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    use_expiration_date = fields.Boolean(related='product_id.use_expiration_date')
