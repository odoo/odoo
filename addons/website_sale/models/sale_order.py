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

    def _cart_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = dict()
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = int(sum(l.product_uom_qty for l in (order.website_order_line or [])))
        return res

    _columns = {
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
        'cart_quantity': fields.function(_cart_qty, type='integer', string='Cart Quantity'),
        'payment_acquirer_id': fields.many2one('payment.acquirer', 'Payment Acquirer', on_delete='set null'),
        'payment_tx_id': fields.many2one('payment.transaction', 'Transaction', on_delete='set null'),
    }

    def _get_errors(self, cr, uid, order, context=None):
        return []

    def _get_website_data(self, cr, uid, order, context):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            order_line_id = None
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain += [('id', '=', line_id)]
            order_line_ids = self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)
            if order_line_ids:
                order_line_id = order_line_ids[0]
            return order_line_id

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, line_id=None, context=None):
        so = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)

        values = self.pool.get('sale.order.line').product_id_change(cr, SUPERUSER_ID, [],
            pricelist=so.pricelist_id.id,
            product=product_id,
            partner_id=so.partner_id.id,
            context=context
        )['value']

        if line_id:
            line = self.pool.get('sale.order.line').browse(cr, SUPERUSER_ID, line_id, context=context)
            values['name'] = line.name
        else:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            values['name'] = product.name_get()[0][1]

        values['product_id'] = product_id
        values['order_id'] = order_id
        if values.get('tax_id') != None:
            values['tax_id'] = [(6, 0, values['tax_id'])]
        return values

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None):
        """ Add or set product quantity, add_qty can be negative """
        sol = self.pool.get('sale.order.line')

        quantity = 0
        for so in self.browse(cr, uid, ids, context=context):
            line_id = so._cart_find_product_line(product_id, line_id, context=context)

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, context=context)
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty != None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id], context=context)
            else:
                # update line
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, line_id, context=context)
                values['product_uom_qty'] = quantity
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

        return quantity

    def _cart_accessories(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            s = set(j.id for l in (order.website_order_line or []) for j in (l.product_id.accessory_product_ids or []))
            s -= set(l.product_id.id for l in order.order_line)
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
        sale_order_obj = self.pool['sale.order']
        sale_order_id = request.session.get('sale_order_id')
        sale_order = None
        # create so if needed
        if not sale_order_id and (force_create or code):  
            # TODO cache partner_id session
            partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id

            for w in self.browse(cr, uid, ids):
                values = {
                    'user_id': w.user_id.id,
                    'partner_id': partner.id,
                    'pricelist_id': partner.property_product_pricelist.id,
                    'section_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'website', 'salesteam_website_sales')[1],
                }
                sale_order_id = sale_order_obj.create(cr, SUPERUSER_ID, values, context=context)
                values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner.id, context=context)['value']
                sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)
                request.session['sale_order_id'] = sale_order_id
        if sale_order_id:
            # TODO cache partner_id session
            partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id

            sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            if not sale_order.exists():
                request.session['sale_order_id'] = None
                return None

            def update_pricelist(pricelist_id):
                values = {'pricelist_id': pricelist_id}
                values.update(sale_order.onchange_pricelist_id(pricelist_id, None)['value'])
                sale_order.write(values)
                for line in sale_order.order_line:
                    sale_order._cart_update(product_id=line.product_id.id, add_qty=0)

            # check for change of pricelist with a coupon
            if code and code != sale_order.pricelist_id.code:
                pricelist_ids = self.pool['product.pricelist'].search(cr, SUPERUSER_ID, [('code', '=', code)], context=context)
                if pricelist_ids:
                    pricelist_id = pricelist_ids[0]
                    request.session['sale_order_code_pricelist_id'] = pricelist_id
                    update_pricelist(pricelist_id)
                request.session['sale_order_code_pricelist_id'] = False

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
                flag_pricelist = False
                pricelist_id = request.session.get('sale_order_code_pricelist_id') or partner.property_product_pricelist.id
                if pricelist_id != sale_order.pricelist_id.id:
                    flag_pricelist = True
                fiscal_position = sale_order.fiscal_position and sale_order.fiscal_position.id or False

                values = sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [sale_order_id], partner.id, context=context)['value']
                order_lines = map(int,sale_order.order_line)
                values.update(sale_order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [],
                    values['fiscal_position'], [[6, 0, order_lines]], context=context)['value'])

                values['partner_id'] = partner.id
                sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

                if flag_pricelist or values.get('fiscal_position') != fiscal_position:
                    update_pricelist(pricelist_id)

            # update browse record
            if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id !=  partner.id:
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order.id, context=context)

        return sale_order

    def sale_get_transaction(self, cr, uid, ids, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            tx_ids = transaction_obj.search(cr, uid, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, uid, tx_ids[0], context=context)
            else:
                request.session['sale_transaction_id'] = False
        return False

    def sale_reset(self, cr, uid, ids, context=None):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'sale_order_code_pricelist_id': False,
        })

# vim:et:
