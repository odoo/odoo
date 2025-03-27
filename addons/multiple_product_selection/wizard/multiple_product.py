# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Saneen K (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models


class MultipleProduct(models.TransientModel):
    """Create new wizard model of product list for selection"""
    _name = "multiple.product"
    _description = 'Multiple Product Selection'

    product_list_ids = fields.Many2many('product.product',
                                        string='Product List',
                                        help="Product list of all the products")

    def action_add_line(self):
        """Function for adding all the products to the order line that are
        selected from the wizard"""
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        line = 'purchase.order.line' if active_model == 'purchase.order' \
            else 'sale.order.line'
        current_id = self.env['purchase.order'].browse(
            active_id) if active_model == 'purchase.order' \
            else self.env['sale.order'].browse(active_id)
        for rec in self.product_list_ids:
            if rec not in current_id.order_line.product_id:
                self.env[line].create({
                    'order_id': active_id,
                    'product_id': rec.id,
                    'price_unit': rec.list_price,
                    'product_uom_qty': 1,
                })
            elif active_model == 'purchase.order':
                current_id.order_line.filtered(
                    lambda self: self.product_id == rec).product_qty += 1
            elif active_model == 'sale.order':
                current_id.order_line.filtered(
                    lambda self: self.product_id == rec).product_uom_qty += 1
