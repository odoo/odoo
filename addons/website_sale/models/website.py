# -*- coding: utf-8 -*-
from openerp.osv import orm, fields
from openerp.addons.web import http


class Website(orm.Model):
    _inherit = 'website'

    def _get_pricelist(self, cr, uid, ids, field_name, arg, context=None):
        # FIXME: oh god kill me now
        pricelist_id = http.request.httprequest.session['ecommerce_pricelist']
        return dict.fromkeys(
            ids, self.pool['product.pricelist'].browse(
                cr, uid, pricelist_id, context=context))

    _columns = {
        'pricelist_id': fields.function(
            _get_pricelist, type='many2one', obj='product.pricelist')
    }


class PaymentTransaction(orm.Model):
    _inherit = 'payment.transaction'

    _columns = {
        # link with the sale order
        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
    }
