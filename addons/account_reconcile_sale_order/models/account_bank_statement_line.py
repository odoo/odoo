# -*- coding: utf-8 -*-

from openerp import models

def matches_sale_order_payment_memo_pattern(string):
    return string.lower().startswith('so') and string[2:].isdigit()

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_move_lines_for_auto_reconcile(self):
        """ Prevent automatic reconciliation of payments whose memo suggests they were
            made to pay an open sales order.
        """
        # TOCHECK: allow it if the memo == the counterpart ref ? (so, if the SO was invoiced but is not yet in state done)
        if self.find_matching_sale_order():
            return None
        return super(AccountBankStatementLine, self)._get_move_lines_for_auto_reconcile()

    def get_data_for_single_reconciliation_widget(self, excluded_move_line_ids):
        """ If a sales order matches the transaction, add its id to the data for the reconciliation widget
            and use potential SO's invoices as reconciliation proposition.
        """
        ret = super(AccountBankStatementLine, self).get_data_for_single_reconciliation_widget(excluded_move_line_ids)
        sale_order = self.find_matching_sale_order()
        if sale_order:
            if not self.partner_id:
                self.partner_id = sale_order.partner_invoice_id
            ret['sale_order_id'] = sale_order.id
            ret['reconciliation_proposition'] = sale_order.get_move_lines_for_reconciliation_widget(self.id)
        return ret

    def find_matching_sale_order(self):
        """ Try to find a sales order this transaction was made to pay.
            Eg. a e-commerce user pays an order by wire transfer.
        """
        self.ensure_one()
        if not matches_sale_order_payment_memo_pattern(self.name):
            return None

        domain_so = [
            # TOCHECK: filter on payment acquirer ?
            '&', ('state', 'in', ('sent', 'sale')),
            '|', ('name', '=ilike', self.name),
            ('client_order_ref', '=ilike', self.name)]
        if self.partner_id:
            domain_so += [('partner_invoice_id', '=', self.partner_id.id)]
        sale_order = self.env['sale.order'].search(domain_so)

        # TOCHECK: could that happen or can we drop this code
        if len(sale_order) != 1:
            return None

        return sale_order
