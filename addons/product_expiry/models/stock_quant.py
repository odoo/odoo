# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

import openerp
from openerp.osv import fields, osv


class stock_quant(osv.osv):
    _inherit = 'stock.quant'

    def _get_quants(self, cr, uid, ids, context=None):
        return self.pool.get('stock.quant').search(cr, uid, [('lot_id', 'in', ids)], context=context)

    _columns = {
        'removal_date': fields.related('lot_id', 'removal_date', type='datetime', string='Removal Date',
            store={
                'stock.quant': (lambda self, cr, uid, ids, ctx: ids, ['lot_id'], 20),
                'stock.production.lot': (_get_quants, ['removal_date'], 20),
            }),
    }

    def apply_removal_strategy(self, cr, uid, qty, move, ops=False, domain=None, removal_strategy='fifo', context=None):
        if removal_strategy == 'fefo':
            order = 'removal_date, in_date, id'
            return self._quants_get_order(cr, uid, qty, move, ops=ops, domain=domain, orderby=order, context=context)
        return super(stock_quant, self).apply_removal_strategy(cr, uid, qty, move, ops=ops, domain=domain,
                                                               removal_strategy=removal_strategy, context=context)
