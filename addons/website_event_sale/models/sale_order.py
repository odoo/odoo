# -*- coding: utf-8 -*-
from openerp.osv import osv
from openerp import SUPERUSER_ID
from openerp.addons.web.http import request


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def _recalculate_product_values(self, cr, uid, ids, product_id=0, fiscal_position=False, context=None):
        if not ids:
            return super(sale_order_line, self)._recalculate_product_values(cr, uid, ids, product_id, fiscal_position=fiscal_position, context=context)

        order_line = self.browse(cr, SUPERUSER_ID, ids[0], context=context)
        assert order_line.order_id.website_session_id == request.httprequest.session['website_session_id']

        product = product_id and self.pool.get('product.product').browse(cr, uid, product_id, context=context) or order_line.product_id
        res = super(sale_order_line, self)._recalculate_product_values(cr, uid, ids, product.id, fiscal_position=fiscal_position, context=context)
        if product.event_type_id and order_line.event_ticket_id and order_line.event_ticket_id.price != product.lst_price:
            res.update({'price_unit': order_line.event_ticket_id.price})

        return res
