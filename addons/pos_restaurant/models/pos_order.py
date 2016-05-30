# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class pos_order(osv.osv):
    _inherit = 'pos.order'
    _columns = {
        'table_id': fields.many2one('restaurant.table','Table', help='The table where this order was served'),
        'customer_count' : fields.integer('Guests', help='The amount of customers that have been served by this order.'),
    }

    def _order_fields(self, cr, uid, ui_order, context=None):
        fields = super(pos_order,self)._order_fields(cr,uid,ui_order,context)
        fields['table_id']       = ui_order.get('table_id',0)
        fields['customer_count'] = ui_order.get('customer_count',0)
        return fields
