# -*- coding: utf-8 -*-

from openerp import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_move_lines_for_auto_reconcile(self):
        """ Prevent automatic reconciliation of payments whose memo suggests they were
            made to pay an open sales order.
        """
        # TOCHECK: allow it if the memo == the counterpart ref ? (so, if the SO was invoiced but is not yet in state done)
        if self.find_matching_sale_orders():
            return None
        return super(AccountBankStatementLine, self)._get_move_lines_for_auto_reconcile()

    def get_data_for_single_reconciliation_widget(self, excluded_move_line_ids):
        """ If a sales order matches the transaction, add its id to the data for the reconciliation widget
            and use potential SO's invoices as reconciliation proposition.
        """
        ret = super(AccountBankStatementLine, self).get_data_for_single_reconciliation_widget(excluded_move_line_ids)
        sale_orders = self.find_matching_sale_orders()
        if sale_orders:
            ret['sale_order_ids'] = sale_orders.ids
            #ret['reconciliation_proposition'] = sale_order.get_move_lines_for_reconciliation_widget(self.id)
        return ret

    def find_matching_sale_orders(self):
        """ Try to find sales orders this transaction was made to pay.
            Eg. a e-commerce user pays an order by wire transfer.
        """
        self.ensure_one()

        domain_so = [
            # TOCHECK: filter on payment acquirer ?
            ('state', 'in', ('sent', 'sale'))]
        if self.partner_id:
            domain_so += [('partner_invoice_id', '=', self.partner_id.id)]
        sale_orders = self.env['sale.order'].search(domain_so)

        return sale_orders
