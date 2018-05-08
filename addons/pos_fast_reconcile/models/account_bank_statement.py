# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

from psycopg2.extensions import AsIs
import math
import time


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def _pos_statement_confirm(self):
        self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            for st_line in statement.line_ids:
                if st_line.account_id and not st_line.journal_entry_ids.ids:
                    st_line.fast_counterpart_creation()
                elif not st_line.journal_entry_ids.ids:
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                moves = (moves | st_line.journal_entry_ids)
            if moves:
                moves.filtered(lambda m: m.state != 'posted').post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})
    
    def _pos_fast_counterpart_creation(self):
        aml_obj = self.env['account.move.line']

        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        partner_id = self.partner_id.id or None
        st_line_currency = self.currency_id or statement_currency
        for st_line in self:
            # If we are in multi-currency use standard process
            if st_line_currency.id != company_currency.id:
                vals = {
                    'name': st_line.name,
                    'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                    'credit': st_line.amount > 0 and st_line.amount or 0.0,
                    'account_id': st_line.account_id.id,
                }
                return st_line.process_reconciliation(new_aml_dicts=[vals])
            move_vals = self._prepare_reconciliation_move(st_line.statement_id.name)
            move = self.env['account.move'].create(move_vals)
            debit = st_line.amount < 0 and -st_line.amount or 0.0
            credit = st_line.amount > 0 and st_line.amount or 0.0
            debit_cash_basis = 0 if move.journal_id.type in ('sale','purchase') else debit
            credit_cash_basis = 0 if move.journal_id.type in ('sale','purchase') else credit
            aml_dict = {
                'name': st_line.name,
                'debit': debit,
                'credit': credit,
                'balance': debit-credit,
                'account_id': st_line.account_id.id,
                'move_id': move.id,
                'partner_id': partner_id,
                'statement_id': st_line.statement_id.id,
                'reconciled': False,
                'amount_residual': debit-credit if st_line.account_id.reconcile else 0,
                'amount_residual_currency': 0,
                'debit_cash_basis': debit_cash_basis,
                'credit_cash_basis': credit_cash_basis,
                'balance_cash_basis': debit_cash_basis - credit_cash_basis,
                'company_currency_id': move.company_id.currency_id.id,
                'ref': move.ref,
                'journal_id': move.journal_id.id,
                'date': move.date,
                'date_maturity': move.date,
                'company_id': st_line.account_id.company_id.id,
                'user_type_id': st_line.account_id.user_type_id.id,
            }
            columns = aml_dict.keys()
            values = [aml_dict[column] for column in columns]
            self.env.cr.execute('''INSERT INTO account_move_line(%s) VALUES %s''', (AsIs(','.join(columns)), tuple(values)))
            # Create conterpart
            account = credit > 0 and self.statement_id.journal_id.default_credit_account_id or self.statement_id.journal_id.default_debit_account_id
            aml_dict['debit'] = credit
            aml_dict['credit'] = debit
            aml_dict['balance'] = credit-debit
            aml_dict['account_id'] = account.id
            aml_dict['amount_residual'] = debit-credit if account.reconcile else 0,
            aml_dict['debit_cash_basis'] = credit_cash_basis,
            aml_dict['credit_cash_basis'] = debit_cash_basis,
            aml_dict['balance_cash_basis'] = credit_cash_basis - debit_cash_basis,
            columns = aml_dict.keys()
            values = [aml_dict[column] for column in columns]
            self.env.cr.execute('''INSERT INTO account_move_line(%s) VALUES %s''', (AsIs(','.join(columns)), tuple(values)))
            move.post()
            #record the move name on the statement line to be able to retrieve it in case of unreconciliation
            st_line.write({'move_name': move.name})