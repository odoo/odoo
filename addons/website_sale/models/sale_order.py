# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random

from odoo import api, models, fields, _
from odoo.http import request
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    cart_quantity = fields.Integer(compute='_compute_cart_info', string='Cart Quantity')
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')

    @api.multi
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = not bool(order.website_order_line.filtered(lambda line: line.product_id.type not in ('service', 'digital')))

    @api.model
    def _get_errors(self, order):
        return []

    @api.model
    def _get_website_data(self, order):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        for so in self:
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain += [('id', '=', line_id)]
            return self.env['sale.order.line'].sudo().search(domain).ids

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.update({
            'lang': order.partner_id.lang,
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.env['product.product'].with_context(product_context).browse(product_id)

        values = {
            'product_id': product_id,
            'name': product.display_name,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': product.price,
        }
        if product.description_sale:
            values['name'] += '\n %s' % (product.description_sale)
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()

        quantity = 0
        order_line = False
        for so in self:
            if so.state != 'draft':
                request.session['sale_order_id'] = None
                raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
            if line_id is not False:
                line_ids = so._cart_find_product_line(product_id, line_id, **kwargs)
                if line_ids:
                    order_line = SaleOrderLineSudo.browse(line_ids[0])

            # Create line if no line with product_id can be located
            if not order_line:
                values = self._website_product_id_change(so.id, product_id, qty=1)
                order_line = SaleOrderLineSudo.create(values)
                order_line._compute_tax_id()
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty is not None:
                quantity = order_line.product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                order_line.unlink()
            else:
                # update line
                values = self._website_product_id_change(so.id, product_id, qty=quantity)
                order_line.write(values)

        return {'line_id': order_line.id, 'quantity': quantity}

    def _cart_accessories(self):
        for order in self:
            accessory_products = order.website_order_line.mapped('product_id.accessory_product_ids').filtered(lambda product: product.website_published)
            accessory_products -= order.website_order_line.mapped('product_id')
            return random.sample(accessory_products, min(len(accessory_products), 3))
