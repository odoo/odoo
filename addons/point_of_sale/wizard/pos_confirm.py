# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api


class PosConfirm(models.TransientModel):
    _name = 'pos.confirm'
    _description = 'Post POS Journal Entries'

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        Order = self.env['pos.order']
        MoveLine = self.env['account.move.line']
        pos_order = Order.search([('state', '=', 'paid')])
        for order in pos_order:
            todo = True
            for line in order.statement_ids:
                if line.statement_id.state != 'confirm':
                    todo = False
                    break
            if todo:
                order.signal_workflow('done')

        # Check if there is orders to reconcile their invoices
        pos_orders = Order.search(
            [('state', '=', 'invoiced'), ('invoice_id.state', '=', 'open')])
        for order in pos_orders:
            invoice = order.invoice_id
            data_lines = [
                x.id for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]
            for st in order.statement_ids:
                for move in st.move_ids:
                    data_lines += [
                        x.id for x in move.line_id if x.account_id.id == invoice.account_id.id]
                    MoveLine.reconcile(data_lines)
        return {}
