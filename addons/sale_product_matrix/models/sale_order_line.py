# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import sale


class SaleOrderLine(sale.SaleOrderLine):

    product_add_mode = fields.Selection(related='product_template_id.product_add_mode', depends=['product_template_id'])
