# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields


class pos_discount(osv.osv_memory):
    _name = 'pos.discount'
    _description = 'Add a Global Discount'
    _columns = {
        'discount': fields.float('Discount (%)', required=True, digits=(16,2)),
    }
    _defaults = {
        'discount': 5,
    }

    def apply_discount(self, cr, uid, ids, context=None):
        """
         To give the discount of  product and check the.

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : nothing
        """
        order_ref = self.pool.get('pos.order')
        order_line_ref = self.pool.get('pos.order.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]
        for order in order_ref.browse(cr, uid, record_id, context=context):
            order_line_ref.write(cr, uid, [x.id for x in order.lines], {'discount':this.discount}, context=context)
        return {}
