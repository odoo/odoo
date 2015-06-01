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

    def run(self, cr, uid, ids, context=None):
        context = dict(context or {}, procurement_autorun_defer=True)
        res = super(procurement_order, self).run(cr, uid, ids, context=context)

        procurement_ids = self.search(cr, uid, [('move_dest_id.procurement_id', 'in', ids)], order='id', context=context)

        if procurement_ids:
            return self.run(cr, uid, procurement_ids, context=context)
        return res
