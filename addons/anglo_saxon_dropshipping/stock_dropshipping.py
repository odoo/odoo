# coding: utf-8

from openerp.osv import osv


class stock_quant(osv.osv):
    _inherit = "stock.quant"

    def _account_entry_move(self, cr, uid, quants, move, context=None):
        if context is None:
            context = {}

        #checks to see if we need to create accounting entries
        if move.product_id.valuation != 'real_time':
            return super(stock_quant, self)._account_entry_move(cr, uid, quants, move, context=context)
        for q in quants:
            if q.owner_id:
                #if the quant isn't owned by the company, we don't make any valuation entry
                return super(stock_quant, self)._account_entry_move(cr, uid, quants, move, context=context)
            if q.qty <= 0:
                #we don't make any stock valuation for negative quants because the valuation is already made for the counterpart.
                #At that time the valuation will be made at the product cost price and afterward there will be new accounting entries
                #to make the adjustments when we know the real cost price.
                return super(stock_quant, self)._account_entry_move(cr, uid, quants, move, context=context)

        if move.location_id.usage == 'supplier' and move.location_dest_id.usage == 'customer':
            #Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            ctx = context.copy()
            ctx['force_company'] = move.company_id.id
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=ctx)
            return self._create_account_move_line(cr, uid, quants, move, acc_src, acc_dest, journal_id, context=ctx)

        return super(stock_quant, self)._account_entry_move(cr, uid, quants, move, context=context)
