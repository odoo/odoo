# -*- coding: utf-8 -*-
import random

from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.addons.web.http import request

class payment_transaction(orm.Model):
    _inherit = 'payment.transaction'

    _columns = {
        # link with the sale order
        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
    }

class sale_order(osv.Model):
    _inherit = "sale.order"

    _columns = {
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
    }

    def _get_website_data(self, cr, uid, order, context):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    # TODO make a function field instead
    def _cart_qty(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            return int(sum(l.product_uom_qty for l in (order.website_order_line or [])))

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            line_id = None
            line_ids = self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, [('order_id', '=', so.id), ('product_id', '=', product_id)], context=context)
            if line_ids:
                line_id = line_ids[0]
            return line_id

    def _cart_update(self, cr, uid, ids, product_id=None, add_qty=None, set_qty=None, context=None):
        """ Add or set product quantity, add_qty can be negative """
        for so in self.browse(cr, uid, ids, context=context):
            sol = self.pool.get('sale.order.line')

            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            line_id = so._cart_find_product_line(product_id)

            # Create line if no line with product_id can be located
            if not line_id:
                values = self.pool['sale.order.line'].product_id_change(cr, SUPERUSER_ID, [],
                    pricelist=so.pricelist_id.id,
                    product=product_id,
                    partner_id=so.partner_id.id,
                    context=context
                )['value']
                values['name'] = "%s: %s" % (product.name, product.variants) if product.variants else product.name
                # Maybe it's better to do this ? create and then link ?
                #order_line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                #self.write(cr, SUPERUSER_ID, [order.id], {'order_line': [(4, order_line_id)]}, context=context)
                so.write({'order_line': (0, 0, values)})
                line_id = so._cart_find_product_line(product_id)

            # compute new quantity
            if set_qty:
                quantity = set_qty
            else:
                quantity = line_id.product_uom_qty + add_qty

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, line_id, context=context)
            else:
                # update line
                values = self.pool['sale.order.line'].product_id_change(cr, SUPERUSER_ID, [],
                    pricelist=so.pricelist_id.id,
                    product=product_id,
                    partner_id=so.partner_id.id,
                    context=context
                )['value']
                values['name'] = "%s: %s" % (product.name, product.variants) if product.variants else product.name
                values['product_uom_qty'] = quantity
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

            return quantity

    def _cart_accessories(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            s = set(j for l in (order.website_order_line or []) for j in (l.product_id.accessory_product_ids or []))
            product_ids = random.sample(s, min(len(s),3))
            return self.pool['product.product'].browse(cr, uid, product_ids, context=context)

class website(orm.Model):
    _inherit = 'website'

    _columns = {
        'pricelist_id': fields.related('user_id','partner_id','property_product_pricelist',
            type='many2one', relation='product.pricelist', string='Default pricelist')
    }

    def sale_product_domain(self, cr, uid, ids, context=None):
        return [("sale_ok", "=", True)]

    def sale_get_order(self, cr, uid, ids, force_create=False, code=None, context=None):
        sale_order_id = request.httprequest.session.get('sale_order_id')
        sale_order = None
        # create so if needed
        if not sale_order_id and (force_create or code):  
            for w in self.browse(cr, uid, ids):
                # TODO cache partner_id session
                partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
                values = {
                    'user_id': w.user_id.id,
                    'partner_id': partner.id,
                    'pricelist_id': partner.property_product_pricelist.id,
                }
                sale_order_id = self.pool['sale.order'].create(cr, SUPERUSER_ID, values, context=context)
                values = self.pool['sale.order'].onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
                self.pool['sale.order'].write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)
                request.httprequest.session['sale_order_id'] = sale_order_id
        if sale_order_id:
            # TODO cache partner_id session
            partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            sale_order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)

            # check for change of pricelist with a coupon
            # TODO cache sale_order.pricelist_id.code in session
            if code and code != sale_order.pricelist_id.code:
                pricelist_ids = self.pool['product.pricelist'].search(cr, SUPERUSER_ID, [('code', '=', code)], context=context)
                if pricelist_ids:
                    pricelist_id = pricelist_ids[0]
                    values = {'pricelist_id': pricelist_id}
                    values.update(order.onchange_pricelist_id(pricelist_id, None)['value'])
                    order.write(values)
                    for line in order.order_line:
                        sale_order._cart_update(cr, uid, order.product_id, add_qty=0)

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id !=  partner.id:
                values = self.pool['sale.order'].onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
                self.pool['sale.order'].write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)
        return sale_order

    def sale_get_transaction(self, cr, uid, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        tx_id = request.httprequest.session.get('payment_transaction_id')
        if tx_id:
            tx_ids = transaction_obj.search(cr, uid, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, uid, tx_ids[0], context=context)
            else:
                request.httprequest.session['payment_transaction_id'] = False
        return False

    def sale_reset(self, cr, uid, context=None):
        request.httprequest.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
        })

    def preprocess_request(self, cr, uid, ids, request, context=None):
        request.context.update({
            'sale_order': self.sale_get_order(cr, uid, ids, context=context),
            #'website_sale_transaction': self.ecommerce_get_current_transaction(cr, uid, context=context)
        })
        return super(website, self).preprocess_request(cr, uid, ids, request, context=None)

# vim:et:
