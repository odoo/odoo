# -*- coding: utf-8 -*-
import uuid
from openerp.osv import orm, fields
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID


class Website(orm.Model):
    _inherit = 'website'

    def _get_pricelist(self, cr, uid, ids, field_name, arg, context=None):
        # FIXME: oh god kill me now
        pricelist_id = self.get_pricelist_id(cr, uid, ids, context=context)
        return dict.fromkeys(
            ids, self.pool['product.pricelist'].browse(
                cr, uid, pricelist_id, context=context))

    _columns = {
        'pricelist_id': fields.function(
            _get_pricelist, type='many2one', obj='product.pricelist')
    }

    def _get_order(self, cr, uid, order_id=None, context=None):
        order_obj = self.pool.get('sale.order')
        # check if order allready exists and have access
        if order_id:
            if not order_id in order_obj.exists(cr, uid, [order_id], context=context):
                return False
            try:
                order = order_obj.browse(cr, uid, order_id, context=context)
                if order:
                    return order
            except:
                return False

        fields = [k for k, v in order_obj._columns.items()]
        order_value = order_obj.default_get(cr, SUPERUSER_ID, fields, context=context)
        if request.httprequest.session.get('ecommerce_pricelist'):
            order_value['pricelist_id'] = request.httprequest.session['ecommerce_pricelist']
        order_value['partner_id'] = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        order_value.update(order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], order_value['partner_id'], context=context)['value'])

        # add website_session_id key for access rules
        if not request.httprequest.session.get('website_session_id'):
            request.httprequest.session['website_session_id'] = str(uuid.uuid4())

        order_value["website_session_id"] = request.httprequest.session['website_session_id']
        order_id = order_obj.create(cr, SUPERUSER_ID, order_value, context=context)
        order = order_obj.browse(cr, SUPERUSER_ID, order_id, context=context)
        request.httprequest.session['ecommerce_order_id'] = order.id

        return order_obj.browse(cr, uid, order_id,
                                context=dict(request.context, pricelist=order.pricelist_id.id))

    def get_current_order(self, cr, uid, context=None):
        if request.httprequest.session.get('ecommerce_order_id'):
            order = self._get_order(cr, uid, order_id=request.httprequest.session['ecommerce_order_id'], context=context)
            if not order:
                request.httprequest.session['ecommerce_order_id'] = False
            return order
        return False

    def _get_transaction(self, cr, uid, tx_id=None, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        if tx_id:
            tx_ids = transaction_obj.search(cr, uid, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, uid, tx_ids[0], context=context)
        return False

    def get_current_transaction(self, cr, uid, context=None):
        if request.httprequest.session.get('website_sale_transaction_id'):
            tx = self._get_transaction(cr, uid, tx_id=request.httprequest.session['website_sale_transaction_id'], context=context)
            if not tx:
                request.httprequest.session['website_sale_transaction_id'] = False
            return tx
        return False

    def sale_reset_order(self, cr, uid, context=None):
        request.httprequest.session.update({
            'ecommerce_order_id': False,
            'ecommerce_pricelist': False,
            'website_sale_transaction_id': False,
        })
        request.context.update({
            'website_sale_order': False,
            'website_sale_transaction': False,
        })

    def preprocess_request(self, cr, uid, ids, request, context=None):
        request.context.update({
            'website_sale_order': self.get_current_order(cr, uid, context=context),
            'website_sale_transaction': self.get_current_transaction(cr, uid, context=context)
        })
        return super(Website, self).preprocess_request(cr, uid, ids, request, context=None)

    def get_pricelist_id(self, cr, uid, ids, context=None):
        if not request.httprequest.session.get('ecommerce_pricelist'):
            self.change_pricelist_id(cr, uid, ids, None, context=context)
        return request.httprequest.session.get('ecommerce_pricelist')

    def change_pricelist_id(self, cr, uid, ids, code, context=None):
        request.httprequest.session.setdefault('ecommerce_pricelist', False)

        pricelist_id = False
        if code:
            pricelist_obj = self.pool.get('product.pricelist')
            pricelist_ids = pricelist_obj.search(cr, SUPERUSER_ID, [('code', '=', code)], context=context)
            if pricelist_ids:
                pricelist_id = pricelist_ids[0]

        if not pricelist_id:
            partner_id = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context).partner_id.id
            pricelist_id = self.pool.get('sale.order').onchange_partner_id(cr, SUPERUSER_ID, [], partner_id, context=context)['value']['pricelist_id']

        request.httprequest.session['ecommerce_pricelist'] = pricelist_id

        order = self.get_current_order(cr, uid, context=context)
        if order:
            values = {'pricelist_id': pricelist_id}
            values.update(order.onchange_pricelist_id(pricelist_id, None)['value'])
            order.write(values)
            for line in order.order_line:
                self.add_product_to_cart(order_line_id=line.id, number=0)
