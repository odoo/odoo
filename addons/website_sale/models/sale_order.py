# -*- coding: utf-8 -*-
import random

from openerp import api, fields, models
from openerp.http import request


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.depends('website_order_line')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(order.website_order_line.filtered(lambda l: (l.product_id and l.product_id.type == 'service')))

    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    cart_quantity = fields.Integer(compute='_compute_cart_info')
    payment_acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', on_delete='set null', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', 'Transaction', on_delete='set null', copy=False)
    only_services = fields.Boolean(compute='_compute_cart_info')

    def _get_errors(self):
        self.ensure_one()
        return []

    def _get_website_data(self):
        self.ensure_one()
        return {
            'partner': self.partner_id.id,
            'order': self
        }

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        for so in self:
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain.append(('id', '=', line_id))
            return self.env['sale.order.line'].sudo().search(domain).ids

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0, line_id=None):
        OrderLine = self.env['sale.order.line'].sudo()
        so = self.env['sale.order'].browse(order_id)
        values = OrderLine.product_id_change(
            pricelist=so.pricelist_id.id,
            product=product_id,
            partner_id=so.partner_id.id,
            fiscal_position=so.fiscal_position.id,
            qty=qty,
        )['value']

        if line_id:
            line = OrderLine.browse(line_id)
            values['name'] = line.name
        else:
            product = self.env['product.product'].browse(product_id)
            values['name'] = product.display_name
            if product.description_sale:
                values['name'] += '\n'+product.description_sale

        values['product_id'] = product_id
        values['order_id'] = self.id
        if not values.get('tax_id'):
            values['tax_id'] = [(6, 0, values['tax_id'])]
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        OrderLine = self.env['sale.order.line'].sudo()
        quantity = 0
        for so in self:
            if not line_id:
                lines = so._cart_find_product_line(product_id, line_id, kwargs=kwargs)
                if lines:
                    line_id = lines[0]
                else:
                    # Create line if no line with product_id can be located
                    values = so._website_product_id_change(so.id, product_id, qty=1)
                    line_id = OrderLine.create(values).id
                    if add_qty:
                        add_qty -= 1

            # compute new quantity
            line = OrderLine.browse(line_id)
            if set_qty:
                quantity = set_qty
            elif add_qty >= 0:
                quantity = line.product_uom_qty + add_qty
            # Remove zero of negative lines
            if quantity <= 0:
                line.unlink()
            else:
                # update line
                values = so._website_product_id_change(so.id, product_id, qty=quantity, line_id=line_id)
                values['product_uom_qty'] = quantity
                line.write(values)
        return {'line_id': line_id, 'quantity': quantity}

    def _cart_accessories(self):
        for order in self:
            s = (order.mapped('website_order_line.product_id.accessory_product_ids') - order.mapped('order_line.product_id')).ids
            product_ids = random.sample(s, min(len(s), 3))
            return self.env['product.product'].browse(product_ids)


class Website(models.Model):
    _inherit = 'website'

    pricelist_id = fields.Many2one('product.pricelist', related='user_id.partner_id.property_product_pricelist', string='Default Pricelist')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Default Currency')

    @api.model
    def sale_product_domain(self, context=None):
        return [("sale_ok", "=", True)]

    @api.multi
    def sale_get_order(self, force_create=False, code=None, update_pricelist=None):
        SaleOrder = self.env['sale.order'].sudo()
        sale_order_id = request.session.get('sale_order_id')
        sale_order = None
        # create so if needed
        if not sale_order_id and (force_create or code):
            # TODO cache partner_id session
            partner = self.env.user.sudo().partner_id

            for w in self:
                values = {
                    'user_id': w.user_id.id,
                    'partner_id': partner.id,
                    'pricelist_id': partner.property_product_pricelist.id,
                    'team_id': self.env.ref['website.salesteam_website_sales'].id,
                }
                sale_order = SaleOrder.create(values)
                values = SaleOrder.onchange_partner_id(part=partner.id)['value']
                sale_order.write(values)
                request.session['sale_order_id'] = sale_order.id
        if sale_order_id:
            # TODO cache partner_id session
            partner = self.env.user.sudo().partner_id

            sale_order = SaleOrder.browse(sale_order_id)
            if not sale_order.exists():
                request.session['sale_order_id'] = None
                return None

            # check for change of pricelist with a coupon
            if code and code != sale_order.pricelist_id.code:
                pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
                request.session['sale_order_code_pricelist_id'] = pricelist.id
                update_pricelist = True

            pricelist_id = request.session.get('sale_order_code_pricelist_id') or partner.property_product_pricelist.id

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
                flag_pricelist = False
                if pricelist_id != sale_order.pricelist_id.id:
                    flag_pricelist = True
                fiscal_position = sale_order.fiscal_position and sale_order.fiscal_position.id or False

                values = sale_order.onchange_partner_id(part=partner.id)['value']
                if values.get('fiscal_position'):
                    order_lines = map(int, sale_order.order_line)
                    values.update(SaleOrder.onchange_fiscal_position([],
                                                                     values['fiscal_position'], [[6, 0, order_lines]])['value'])

                values['partner_id'] = partner.id
                sale_order.write(values)

                if flag_pricelist or values.get('fiscal_position') != fiscal_position:
                    update_pricelist = True

            # update the pricelist
            if update_pricelist:
                values = {'pricelist_id': pricelist_id}
                values.update(sale_order.onchange_pricelist_id(pricelist_id, None)['value'])
                sale_order.write(values)
                for line in sale_order.order_line:
                    sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

            # update browse record
            if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id != partner.id:
                sale_order = SaleOrder.browse(sale_order.id)
        return sale_order

    @api.model
    def sale_get_transaction(self):
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            tx = self.env['payment.transaction'].sudo().search([('id', '=', tx_id), ('state', 'not in', ['cancel'])], limit=1)
            if tx:
                return tx
            else:
                request.session['sale_transaction_id'] = False
        return False

    @api.model
    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'sale_order_code_pricelist_id': False,
        })
