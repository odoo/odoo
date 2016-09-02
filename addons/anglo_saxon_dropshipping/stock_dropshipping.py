# coding: utf-8

from openerp.osv import osv

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    def _anglo_saxon_sale_move_lines(self, cr, uid, i_line, res, context=None):
        salelines = self.pool.get('sale.order.line').search(cr, uid, [('invoice_lines', 'in', [i_line.id])])
        for sale_line in self.pool.get('sale.order.line').browse(cr, uid, salelines, context=context):
            for proc in sale_line.procurement_ids:
                if proc.purchase_line_id:
                    #if the invoice line is related to sale order lines having one of its procurement_ids with a purchase_line_id set, it means that it is a confirmed dropship and in that case we mustn't create the cost of sale line (because the product won't enter the stock)
                    return []
        return super(account_invoice_line, self)._anglo_saxon_sale_move_lines(cr, uid, i_line, res, context=context)
