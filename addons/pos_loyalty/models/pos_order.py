# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class pos_order(osv.osv):
    _inherit = 'pos.order'

    _columns = {
        'loyalty_points': fields.float('Loyalty Points', help='The amount of Loyalty points the customer won or lost with this order'),
    }

    def _order_fields(self, cr, uid, ui_order, context=None):
        fields = super(pos_order, self)._order_fields(cr, uid, ui_order, context)
        fields['loyalty_points'] = ui_order.get('loyalty_points', 0)
        return fields

    def create_from_ui(self, cr, uid, orders, context=None):
        ids = super(pos_order, self).create_from_ui(cr, uid, orders, context=context)
        for order in orders:
            if order['data']['loyalty_points'] != 0 and order['data']['partner_id']:
                partner = self.pool.get('res.partner').browse(cr, uid, order['data']['partner_id'], context=context)
                partner.write({'loyalty_points': partner['loyalty_points'] + order['data']['loyalty_points']})

        return ids
