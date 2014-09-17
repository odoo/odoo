# -*- coding: utf-8 -*-
import uuid
from openerp.osv import orm, fields
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID


class Website(orm.Model):
    _inherit = 'website'

    def _get_pricelist_id(self, cr, uid, ids, field_name, arg, context=None):
        pricelist_id = self.ecommerce_get_pricelist_id(cr, uid, None, context=context)
        return dict.fromkeys(ids, pricelist_id)

    _columns = {
        'pricelist_id': fields.function(
            _get_pricelist_id, type='many2one', obj='product.pricelist')
    }

    # ************************************************************
    # Ecommerce pricelist management
    # ***********************************************************

    def ecommerce_get_pricelist_id(self, cr, uid, ids, context=None):
        if not request.httprequest.session.get('ecommerce_pricelist') or request.httprequest.session.get('ecommerce_pricelist_uid') != uid:
            self._ecommerce_change_pricelist(cr, uid, None, context=context)
        return request.httprequest.session.get('ecommerce_pricelist')

    def _ecommerce_change_pricelist(self, cr, uid, code=None, context=None):
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
        request.httprequest.session['ecommerce_pricelist_uid'] = uid

        order = self.ecommerce_get_current_order(cr, uid, context=context)
        if order:
            values = {'pricelist_id': pricelist_id}
            values.update(order.onchange_pricelist_id(pricelist_id, None)['value'])
            order.write(values)
            for line in order.order_line:
                self._ecommerce_add_product_to_cart(cr, uid, order_line_id=line.id, number=0)

    # ************************************************************
    # Ecommerce quotation management
    # ************************************************************

    def _ecommerce_add_product_to_cart(self, cr, uid, product_id=0, order_line_id=0, number=1, set_number=-1, context=None):
        order = self.ecommerce_get_current_order(cr, uid, context=context)
        if not order:
            order = self.ecommerce_get_new_order(cr, uid, context=context)

        order_line_obj = self.pool.get('sale.order.line')
        order_obj = self.pool.get('sale.order')

        context = dict(context or {}, pricelist=self.ecommerce_get_pricelist_id(cr, uid, None, context=context))

        # set order_line_id and product_id
        if order_line_id:
            order_line = None
            for line in order.order_line:
                if line.id == order_line_id:
                    order_line = line
                    break
            if order_line:
                product_id = order_line.product_id.id
            else:
                order_line_id = None
        else:
            order_line_ids = order_line_obj.search(cr, SUPERUSER_ID,
                [('order_id', '=', order.id), ('product_id', '=', product_id)], context=context)
            if order_line_ids:
                order_line_id = order_line_ids[0]

        if not order_line_id and not product_id:
            return 0

        # values initialisation
        quantity = 0
        values = {}
        order_line_ids = []
        if order_line_id:
            order_line_val = order_line_obj.read(cr, SUPERUSER_ID, [order_line_id], [], context=context)[0]
            if not product_id:
                product_id = order_line_val['product_id'][0]
            if set_number >= 0:
                quantity = set_number
            else:
                quantity = order_line_val['product_uom_qty'] + number
            if quantity < 0:
                quantity = 0
            order_line_ids = [order_line_id]
        else:
            fields = [k for k, v in order_line_obj._columns.items()]
            values = order_line_obj.default_get(cr, SUPERUSER_ID, fields, context=context)
            quantity = 1

        # change and record value
        if quantity:
            vals = order_line_obj._recalculate_product_values(cr, uid, order_line_ids, product_id, fiscal_position=order.fiscal_position.id, context=context)
            values.update(vals)
            values['product_uom_qty'] = quantity
            values['product_id'] = product_id
            values['order_id'] = order.id

            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            values['name'] = "%s: %s" % (product.name, product.variants) if product.variants else product.name
            if values.get('tax_id'):
                values['tax_id'] = [(6, 0, values['tax_id'])]

            order_obj.write(cr, SUPERUSER_ID, [order.id], {'order_line': [(1, order_line_id, values) if order_line_id else (0, 0, values)]}, context=context)

        elif order_line_ids:
            order_line_obj.unlink(cr, SUPERUSER_ID, order_line_ids, context=context)

        order = self.ecommerce_get_current_order(cr, uid, context=context)
        if not order or not order.order_line:
            self._ecommerce_change_pricelist(cr, uid, None, context=context)

        return quantity

    def _ecommerce_get_quotation_values(self, cr, uid, context=None):
        """ Generate the values for a new ecommerce quotation. """
        SaleOrder = self.pool.get('sale.order')
        fields = [k for k, v in SaleOrder._columns.items()]
        values = SaleOrder.default_get(cr, SUPERUSER_ID, fields, context=context)
        if request.httprequest.session.get('ecommerce_pricelist'):
            values['pricelist_id'] = request.httprequest.session['ecommerce_pricelist']
        values['partner_id'] = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        values.update(SaleOrder.onchange_partner_id(cr, SUPERUSER_ID, [], values['partner_id'], context=context)['value'])
        values['website_session_id'] = request.httprequest.session['website_session_id']
        return values

    def _ecommerce_create_quotation(self, cr, uid, context=None):
        """ Create a new quotation used in the ecommerce (event, sale) """
        SaleOrder = self.pool.get('sale.order')
        quotation_values = self._ecommerce_get_quotation_values(cr, uid, context=context)
        quotation_values['user_id'] = False
        return SaleOrder.create(cr, SUPERUSER_ID, quotation_values, context=context)

    def ecommerce_get_new_order(self, cr, uid, context=None):
        """ Create a new quotation for the ecommerce and update the session
        accordingly: website_session_id if not set, ecommerce_order_id """
        SaleOrder = self.pool.get('sale.order')

        # add website_session_id key for access rules
        if not request.httprequest.session.get('website_session_id'):
            request.httprequest.session['website_session_id'] = str(uuid.uuid4())

        order_id = self._ecommerce_create_quotation(cr, uid, context=context)
        request.httprequest.session['ecommerce_order_id'] = order_id
        context = dict(context or {}, pricelist=self.ecommerce_get_pricelist_id(cr, uid, None, context=context))
        return SaleOrder.browse(cr, SUPERUSER_ID, order_id, context=context)

    def ecommerce_get_current_order(self, cr, uid, context=None):
        SaleOrder = self.pool.get('sale.order')
        context = dict(context or {}, pricelist=self.ecommerce_get_pricelist_id(cr, uid, None, context=context))
        order_id = request.httprequest.session.get('ecommerce_order_id')
        if not order_id:
            request.httprequest.session['ecommerce_order_id'] = False
            return False
        if not order_id in SaleOrder.exists(cr, uid, [order_id], context=context):
            request.httprequest.session['ecommerce_order_id'] = False
            return False
        try:
            order = SaleOrder.browse(cr, SUPERUSER_ID, order_id, context=context)
            assert order.website_session_id == request.httprequest.session['website_session_id']
            return order
        except:
            request.httprequest.session['ecommerce_order_id'] = False
            return False

    # ************************************************************
    # Ecommerce transaction management
    # ************************************************************

    def _get_transaction(self, cr, uid, tx_id=None, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        if tx_id:
            tx_ids = transaction_obj.search(cr, uid, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, uid, tx_ids[0], context=context)
        return False

    def ecommerce_get_current_transaction(self, cr, uid, context=None):
        if request.httprequest.session.get('website_sale_transaction_id'):
            tx = self._get_transaction(cr, uid, tx_id=request.httprequest.session['website_sale_transaction_id'], context=context)
            if not tx:
                request.httprequest.session['website_sale_transaction_id'] = False
            return tx
        return False

    def ecommerce_reset(self, cr, uid, context=None):
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
            'website_sale_order': self.ecommerce_get_current_order(cr, uid, context=context),
            'website_sale_transaction': self.ecommerce_get_current_transaction(cr, SUPERUSER_ID, context=context)
        })
        return super(Website, self).preprocess_request(cr, uid, ids, request, context=None)

    def ecommerce_get_product_domain(self):
        return [
            ("sale_ok", "=", True),
            # force search on product.product to use the orm (exclude active, acl,..)
            ("product_variant_ids.id", "!=", False),
        ]
