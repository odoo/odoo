# -*- coding: utf-8 -*-

from openerp import api, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def get_move_lines_for_reconciliation_widget(self, st_line_id):
        """ If there is/are open invoice/s for this sale order, return their reconciliable move lines
            for the bank statement reconciliation widget, formatted as a list of dicts.
        """
        lines = self.invoice_ids.mapped('move_id').mapped('line_ids')
        # TOCHECK, simply use l.account_id.internal_type == 'receivable'
        lines = lines.filtered(lambda l: not l.reconciled and l.account_id.internal_type in ['payable', 'receivable'])
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)
        return st_line.prepare_move_lines_for_reconciliation_widget(lines)
