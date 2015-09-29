# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class pos_confirm(osv.osv_memory):
    _name = 'pos.confirm'
    _description = 'Post POS Journal Entries'

    def action_confirm(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('pos.order')
        ids = order_obj.search(cr, uid, [('state','=','paid')], context=context)
        for order in order_obj.browse(cr, uid, ids, context=context):
            todo = True
            for line in order.statement_ids:
                if line.statement_id.state != 'confirm':
                    todo = False
                    break
            if todo:
                order.signal_workflow('done')

        # Check if there is orders to reconcile their invoices
        ids = order_obj.search(cr, uid, [('state','=','invoiced'),('invoice_id.state','=','open')], context=context)
        for order in order_obj.browse(cr, uid, ids, context=context):
            invoice = order.invoice_id
            data_lines = [x.id for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]
            for st in order.statement_ids:
                for move in st.move_ids:
                    data_lines += [x.id for x in move.line_id if x.account_id.id == invoice.account_id.id]
                    self.pool.get('account.move.line').reconcile(cr, uid, data_lines, context=context)
        return {}
