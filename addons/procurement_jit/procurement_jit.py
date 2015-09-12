# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.osv import osv

class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def create(self, cr, uid, vals, context=None):
        context = context or {}
        procurement_id = super(procurement_order, self).create(cr, uid, vals, context=context)
        self.run(cr, uid, [procurement_id], context=context)
        return procurement_id

    def run(self, cr, uid, ids, autocommit=False, context=None):
        res = super(procurement_order, self).run(cr, uid, ids, autocommit=autocommit, context=context)
        procurement_ids = self.search(cr, uid, [('move_dest_id.procurement_id', 'in', ids)], order='id', context=context)
        if procurement_ids:
            result = self.run(cr, uid, procurement_ids, autocommit=autocommit, context=context)
            return result
        return res

class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_confirm(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_confirm(cr, uid, ids, context=context or {})
        super(stock_move, self).action_assign(cr, uid, ids, context=context or {})
        return res
