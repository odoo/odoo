# -*- coding: utf-8 -*-
import random
import openerp

from openerp import SUPERUSER_ID, tools
import openerp.addons.decimal_precision as dp
from openerp.osv import osv, orm, fields
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.exceptions import UserError


class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_info(self, cr, uid, ids, field_name, arg, context=None):
        res = dict()
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'cart_quantity': int(sum(l.product_uom_qty for l in (order.website_order_line or []))),
                'only_services': all(l.product_id and l.product_id.type in ('service', 'digital') for l in order.website_order_line)
            }
        return res

    _columns = {
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
        'cart_quantity': fields.function(_cart_info, type='integer', string='Cart Quantity', multi='_cart_info'),
        'payment_acquirer_id': fields.many2one('payment.acquirer', 'Payment Acquirer', on_delete='set null', copy=False),
        'payment_tx_id': fields.many2one('payment.transaction', 'Transaction', on_delete='set null', copy=False),
        'only_services': fields.function(_cart_info, type='boolean', string='Only Services', multi='_cart_info'),
    }

    def _get_errors(self, cr, uid, order, context=None):
        return []

    def _get_website_data(self, cr, uid, order, context):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, **kwargs):
        for so in self.browse(cr, uid, ids, context=context):
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain += [('id', '=', line_id)]
            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, context=None):
        context = dict(context or {})
        order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)
        product_context = context.copy()
        product_context.update({
            'lang': order.partner_id.lang,
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.pool['product.product'].browse(cr, uid, product_id, context=product_context)

        values = {
            'product_id': product_id,
            'name': product.display_name,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': product.price,
        }
        if product.description_sale:
            values['name'] += '\n' + product.description_sale
        return values

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        sol = self.pool.get('sale.order.line')

        quantity = 0
        for so in self.browse(cr, uid, ids, context=context):
            if so.state != 'draft':
                request.session['sale_order_id'] = None
                raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
            if line_id is not False:
                line_ids = so._cart_find_product_line(product_id, line_id, context=context, **kwargs)
                if line_ids:
                    line_id = line_ids[0]

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=1, context=context)
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                sol._compute_tax_id(cr, SUPERUSER_ID, [line_id], context=context)
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty is not None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id], context=context)
            else:
                # update line
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=quantity, context=context)
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

        return {'line_id': line_id, 'quantity': quantity}

    def _cart_accessories(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            s = set(j.id for l in (order.website_order_line or []) for j in (l.product_id.accessory_product_ids or []) if j.website_published)
            s -= set(l.product_id.id for l in order.order_line)
            product_ids = random.sample(s, min(len(s), 3))
            return self.pool['product.product'].browse(cr, uid, product_ids, context=context)
