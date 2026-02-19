# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sruthi MK (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models


class ProductProduct(models.Model):
    """ProductProduct class represents to add purchase histories of
     the product"""
    _inherit = 'product.product'

    po_product_line_ids = fields.One2many('purchase.product.history.line',
                                          'product_history_id',
                                          string='Purchase History',
                                          compute='_compute_po_product_line_ids',
                                          help='Purchased product variant '
                                               'details')

    def _compute_po_product_line_ids(self):
        """Compute the purchase history lines. It will show all purchase order
         details of the particular product in product.template based on the
          limit and status."""
        self.po_product_line_ids = False
        status = self.env['ir.config_parameter'].sudo().get_param(
            'purchase_product_history.status')
        limit = self.env['ir.config_parameter'].sudo().get_param(
            'purchase_product_history.limit')
        if int(limit) >= 0 and status != False:
            state = ''
            if status == 'all':
                state = ('draft', 'sent', 'to approve', 'purchase', 'done',
                         'cancel')
            elif status == 'rfq':
                state = 'draft'
            elif status == 'purchase_order':
                state = ('purchase', 'done')
            order_line = self.env['purchase.order.line'].search([])
            if not limit:
                product_po_order_line = order_line.filtered(
                    lambda
                        l: l.product_id and l.product_id.id == self.id and l.state in state)
            else:
                product_po_order_line = order_line.search(
                    [('product_id', '=', self.id), ('state', 'in', state)],
                    limit=int(limit))
            self.env['purchase.product.history.line'].create([{
                'product_history_id': self.id,
                'order_reference_id': line.order_id.id,
                'description': line.name,
                'price_unit': line.price_unit,
                'product_qty': line.product_qty,
                'price_subtotal': line.price_subtotal,
            } for line in product_po_order_line] if product_po_order_line else [])
