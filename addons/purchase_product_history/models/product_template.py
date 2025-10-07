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


class ProductTemplate(models.Model):
    """Product template class for adding purchase history of the product."""
    _inherit = 'product.template'
    _description = 'Product template'

    po_history_line_ids = fields.One2many('purchase.template.history.line',
                                          'history_id',
                                          string='Purchase history',
                                          compute='_compute_po_history_line_ids',
                                          help='Purchased product details')

    def _compute_po_history_line_ids(self):
        """Compute the purchase history lines. It will show all purchase order
         details of the particular product in product.product based on the
          limit and status."""
        self.po_history_line_ids = False
        status = self.env['ir.config_parameter'].sudo().get_param(
            'purchase_product_history.status')
        limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'purchase_product_history.limit'))
        if limit < 0 or not status:
            return
        state = ''
        if status == 'all':
            state = (
                'draft', 'sent', 'to approve', 'purchase', 'done', 'cancel')
        elif status == 'rfq':
            state = ('draft',)
        elif status == 'purchase_order':
            state = ('purchase', 'done')
        order_line = self.env['purchase.order.line'].search([
            ('product_id', 'in', self.product_variant_ids.ids),
            ('state', 'in', state)
        ], limit=(None if limit == 0 else limit))
        self.env['purchase.template.history.line'].create([
            {
                'history_id': self.id,
                'order_reference_id': rec.order_id.id,
                'description': rec.name,
                'price_unit': rec.price_unit,
                'product_qty': rec.product_qty,
                'price_subtotal': rec.price_subtotal
            } for rec in order_line
        ])
