# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random

from odoo import api, models, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    cart_quantity = fields.Integer(compute='_compute_cart_info', string='Cart Quantity')
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')
    can_directly_mark_as_paid = fields.Boolean(compute='_compute_can_directly_mark_as_paid',
        string="Can be directly marked as paid", store=True,
        help="""Checked if the sales order can directly be marked as paid, i.e. if the quotation
                is sent or confirmed and if the payment acquire is of the type transfer or manual""")

    @api.depends('state', 'payment_tx_id', 'payment_tx_id.state',
                 'payment_acquirer_id', 'payment_acquirer_id.provider')
    def _compute_can_directly_mark_as_paid(self):
        for order in self:
            order.can_directly_mark_as_paid = order.state in ['sent', 'sale'] and order.payment_tx_id.state != 'done' and order.payment_acquirer_id.provider in ['transfer', 'manual']

    @api.multi
    @api.depends('website_order_line.product_uom_qty', 'website_order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(l.product_id.type in ('service', 'digital') for l in order.website_order_line)

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id)

        # split lines with the same product if it has untracked attributes
        if product and product.mapped('attribute_line_ids').filtered(lambda r: not r.attribute_id.create_variant) and not line_id:
            return self.env['sale.order.line']

        domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        return self.env['sale.order.line'].sudo().search(domain)

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.env['product.product'].with_context(product_context).browse(product_id)
        pu = product.price
        if order.pricelist_id and order.partner_id:
            order_line = order._cart_find_product_line(product.id)
            if order_line:
                pu = self.env['account.tax']._fix_tax_included_price(pu, product.taxes_id, order_line[0].tax_id)

        return {
            'product_id': product_id,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': pu,
        }

    @api.multi
    def _get_line_description(self, order_id, product_id, attributes=None):
        if not attributes:
            attributes = {}

        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product = self.env['product.product'].with_context(product_context).browse(product_id)

        name = product.display_name

        # add untracked attributes in the name
        untracked_attributes = []
        for k, v in pycompat.items(attributes):
            # attribute should be like 'attribute-48-1' where 48 is the product_id, 1 is the attribute_id and v is the attribute value
            attribute_value = self.env['product.attribute.value'].sudo().browse(int(v))
            if attribute_value and not attribute_value.attribute_id.create_variant:
                untracked_attributes.append(attribute_value.name)
        if untracked_attributes:
            name += '\n%s' % (', '.join(untracked_attributes))

        if product.description_sale:
            name += '\n%s' % (product.description_sale)

        return name

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, attributes=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status'))
        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # Create line if no line with product_id can be located
        if not order_line:
            values = self._website_product_id_change(self.id, product_id, qty=1)
            values['name'] = self._get_line_description(self.id, product_id, attributes=attributes)
            order_line = SaleOrderLineSudo.create(values)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
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
            values = self._website_product_id_change(self.id, product_id, qty=quantity)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context = dict(self.env.context)
                product_context.setdefault('lang', order.partner_id.lang)
                product_context.update({
                    'partner': order.partner_id.id,
                    'quantity': quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                })
                product = self.env['product.product'].with_context(product_context).browse(product_id)
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price(
                    order_line._get_display_price(product),
                    order_line.product_id.taxes_id,
                    order_line.tax_id
                )

            order_line.write(values)

        return {'line_id': order_line.id, 'quantity': quantity}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            accessory_products = order.website_order_line.mapped('product_id.accessory_product_ids').filtered(lambda product: product.website_published)
            accessory_products -= order.website_order_line.mapped('product_id')
            return random.sample(accessory_products, len(accessory_products))

    def action_mark_as_paid(self):
        """ Mark directly a sales order as paid if:
                - State: Quotation Sent, or sales order
                - Provider: wire transfer or manual config
            The transaction is marked as done
            The invoice may be generated and marked as paid if configured in the website settings
            """
        self.ensure_one()
        if self.can_directly_mark_as_paid:
            self.action_confirm()
            if self.env['ir.config_parameter'].sudo().get_param('website_sale.automatic_invoice', default=False):
                self.payment_tx_id._generate_and_pay_invoice(self.payment_tx_id, self.payment_acquirer_id.provider)
            self.payment_tx_id.state = 'done'
        else:
            raise ValidationError(_("The quote should be sent and the payment acquirer type should be manual or wire transfer"))


class ResCountry(models.Model):
    _inherit = 'res.country'

    def get_website_sale_countries(self, mode='billing'):
        return self.sudo().search([])

    def get_website_sale_states(self, mode='billing'):
        return self.sudo().state_ids


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', string='Last Online Sales Order')
