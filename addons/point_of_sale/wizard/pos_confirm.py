# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models


class PosConfirm(models.TransientModel):
    _name = 'pos.confirm'
    _description = 'Post POS Journal Entries'

    def action_confirm(self):
        PosOrder = self.env['pos.order']
        AccountMoveLine = self.env['account.move.line']
        pos_orders = PosOrder.search([('state', '=', 'paid')])
        for order in pos_orders:
            todo = True
            for line in order.statement_ids:
                if line.statement_id.state != 'confirm':
                    todo = False
                    break
            if todo:
                order.signal_workflow('done')

        # Check if there is orders to reconcile their invoices
        pos_orders = PosOrder.search([('state', '=', 'invoiced'), ('invoice_id.state', '=', 'open')])
        for order in pos_orders:
            data_lines = [x.id for x in order.invoice_id.move_id.line_id if x.account_id.id == order.invoice_id.account_id.id]
            for st in order.statement_ids:
                for move in st.move_ids:
                    data_lines += [x.id for x in move.line_id if x.account_id.id == order.invoice_id.account_id.id]
                    AccountMoveLine.reconcile(data_lines)
        return {}
