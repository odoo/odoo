# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import models, fields, api, _
from openerp.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", help="Complete this field if you plan to invoice the shipping based on picking.")
    delivery_price = fields.Float(compute='_compute_delivery_price', string='Estimated Delivery Price')

    @api.one
    @api.depends('carrier_id', 'partner_id', 'order_line')
    def _compute_delivery_price(self):
        if self.carrier_id:
            self.delivery_price = self.carrier_id.compute_delivery_price(self)[0]
        else:
            self.delivery_price = 0.0

    @api.multi
    def delivery_set(self):

        SaleOrderLine = self.env['sale.order.line']
        FiscalPosition = self.env['account.fiscal.position']

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

                taxes = carrier.product_id.taxes_id
                partner = order.partner_id or False
                if partner:
                    FiscalPosition = self.env['account.fiscal.position']
                    account_id = FiscalPosition.map_account(account_id)
                    taxes_ids = FiscalPosition.map_tax(taxes)
                else:
                    taxes_ids = [tx.id for tx in taxes]

                SaleOrderLine.create({
                    'order_id': order.id,
                    'name': order.carrier_id.name,
                    'product_uom_qty': 1,
                    'product_uom': order.carrier_id.product_id.uom_id.id,
                    'product_id': order.carrier_id.product_id.id,
                    'price_unit': order.carrier_id.get_shipping_price_from_so(order)[0],
                    'tax_id': [(6, 0, taxes_ids.ids)],
                    'is_delivery': True
                })

            else:
                # Classic carriers
                super(SaleOrder, self).delivery_set()

    @api.multi
    def _delivery_unset(self):
        SaleOrderLine = self.env['sale.order.line']
        lines = SaleOrderLine.search([('order_id', 'in', self.ids), ('is_delivery', '=', True)])
        lines.unlink()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery")
