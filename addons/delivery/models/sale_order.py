# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (c) 2015 Odoo S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_price = fields.Float(string='Estimated Delivery Price', compute='_compute_delivery_price', store=True)

    @api.depends('carrier_id', 'partner_id', 'order_line')
    def _compute_delivery_price(self):
        for order in self:
            if order.state != 'draft':
                # we do not want to recompute the shipping price of an already validated/done SO
                continue
            elif order.carrier_id.delivery_type != 'grid' and not order.order_line:
                # prevent SOAP call to external shipping provider when SO has no lines yet
                continue
            else:
                order.delivery_price = order.carrier_id.with_context(order_id=order.id).price

    @api.multi
    def delivery_set(self):

        SaleOrderLine = self.env['sale.order.line']

        # Remove delivery products from the sale order
        self._delivery_unset()

        for order in self:
            if order.carrier_id and order.carrier_id.delivery_type != 'grid':
                # Shipping providers are used when delivery_type is other than 'grid'

                if order.state not in ('draft', 'sent'):
                    raise UserError(_('The order state have to be draft to add delivery lines.'))

                carrier = order.carrier_id
                account_id = carrier.product_id.property_account_income.id
                if not account_id:
                    account_id = carrier.product_id.categ_id.property_account_income_categ.id

                # Apply fiscal position
                taxes = carrier.product_id.taxes_id
                taxes_ids = taxes.ids
                if order.partner_id and order.fiscal_position_id:
                    account_id = order.fiscal_position_id.map_account(account_id)
                    taxes_ids = order.fiscal_position_id.map_tax(taxes).ids

                SaleOrderLine.create({
                    'order_id': order.id,
                    'name': order.carrier_id.name,
                    'product_uom_qty': 1,
                    'product_uom': order.carrier_id.product_id.uom_id.id,
                    'product_id': order.carrier_id.product_id.id,
                    'price_unit': order.carrier_id.get_shipping_price_from_so(order)[0],
                    'tax_id': [(6, 0, taxes_ids)],
                    'is_delivery': True
                })

            else:
                # Classic grid-based carriers
                super(SaleOrder, self).delivery_set()
