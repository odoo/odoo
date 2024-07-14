# -*- coding: utf-8 -*-
import ast
from odoo import models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_open_manual_reconciliation_widget(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        '''
        self.ensure_one()
        action_values = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_move_line_posted_unreconciled')
        if self.partner_id:
            context = ast.literal_eval(action_values['context'])
            context.update({'search_default_partner_id': self.partner_id.id})
            if self.partner_type == 'customer':
                context.update({'search_default_trade_receivable': 1})
            elif self.partner_type == 'supplier':
                context.update({'search_default_trade_payable': 1})
            action_values['context'] = context
        return action_values

    def button_open_statement_lines(self):
        # OVERRIDE
        """ Redirect the user to the statement line(s) reconciled to this payment.
            :return: An action to open the view of the payment in the reconciliation widget.
        """
        self.ensure_one()

        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('id', 'in', self.reconciled_statement_line_ids.ids)],
            default_context={
                'create': False,
                'default_st_line_id': self.reconciled_statement_line_ids.ids[-1],
            },
            name=_("Matched Transactions")
        )
