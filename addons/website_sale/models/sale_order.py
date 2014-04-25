# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.addons.web.http import request


class SaleOrder(osv.Model):
    _inherit = "sale.order"

    _columns = {
        'website_session_id': fields.char('Session UUID4'),
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
    }

    def _get_errors(self, cr, uid, order, context=None):
        return []

    def _get_website_data(self, cr, uid, order, context):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    def get_number_of_products(self, cr, uid, ids, context=None):
        order = self.browse(cr, uid, ids[0], context=context)
        return int(sum(l.product_uom_qty for l in (order.website_order_line or [])))


class SaleOrderLine(osv.Model):
    _inherit = "sale.order.line"

    def _recalculate_product_values(self, cr, uid, ids, product_id=0, fiscal_position=False, context=None):
        # TDE FIXME: seems to be defined several times -> fix me ?
        if context is None:
            context = {}
        user_obj = self.pool.get('res.users')

        if ids and not product_id:
            order_line = self.browse(cr, SUPERUSER_ID, ids[0], context=context)
            assert order_line.order_id.website_session_id == request.httprequest.session['website_session_id']
            product_id = product_id or order_line.product_id.id

        return self.product_id_change(
            cr, SUPERUSER_ID, ids,
            pricelist=context.pop('pricelist'),
            product=product_id,
            partner_id=user_obj.browse(cr, SUPERUSER_ID, uid).partner_id.id,
            fiscal_position=fiscal_position,
            context=context
        )['value']
