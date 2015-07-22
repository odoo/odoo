# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.osv import osv

class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def create(self, cr, uid, vals, context=None):
        context = context or {}
        procurement_id = super(procurement_order, self).create(cr, uid, vals, context=context)
        if not context.get('procurement_autorun_defer'):
            self.run(cr, uid, [procurement_id], context=context)
            self.check(cr, uid, [procurement_id], context=context)
        return procurement_id

    def run(self, cr, uid, ids, autocommit=False, context=None):
        context = dict(context or {}, procurement_autorun_defer=True)
        res = super(procurement_order, self).run(cr, uid, ids, autocommit=autocommit, context=context)

        procurement_ids = self.search(cr, uid, [('move_dest_id.procurement_id', 'in', ids)], order='id', context=context)

        if procurement_ids:
            return self.run(cr, uid, procurement_ids, autocommit=autocommit, context=context)
        return res

class stock_move(osv.osv):
    _inherit = "stock.move"

    def _create_procurements(self, cr, uid, moves, context=None):
        res = super(stock_move, self)._create_procurements(cr, uid, moves, context=dict(context or {}, procurement_autorun_defer=True))
        self.pool['procurement.order'].run(cr, uid, res, context=context)
        return res
