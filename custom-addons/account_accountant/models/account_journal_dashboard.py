from odoo import models


class account_journal(models.Model):
    _inherit = "account.journal"

    def action_open_reconcile(self):
        self.ensure_one()

        if self.type in ('bank', 'cash'):
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                default_context={
                    'default_journal_id': self.id,
                    'search_default_journal_id': self.id,
                    'search_default_not_matched': True,
                },
            )
        else:
            # Open reconciliation view for customers/suppliers
            return self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_move_line_posted_unreconciled')

    def action_open_to_check(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_to_check': True,
                'search_default_journal_id': self.id,
                'default_journal_id': self.id,
            },
        )

    def action_open_bank_transactions(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_journal_id': self.id,
                'default_journal_id': self.id
             },
            kanban_first=False,
        )

    def action_open_reconcile_statement(self):
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_statement_id': self.env.context.get('statement_id'),
            },
        )

    def action_new_transaction(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_bank_statement_line_form_bank_rec_widget')
        action['context'] = {'default_journal_id': self.id}
        return action

    def open_action(self):
        # EXTENDS account
        # set default action for liquidity journals in dashboard

        if self.type in ('bank', 'cash') and not self._context.get('action_name'):
            self.ensure_one()
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                extra_domain=[('line_ids.account_id', '=', self.default_account_id.id)],
                default_context={
                    'default_journal_id': self.id,
                    'search_default_journal_id': self.id,
                },
            )
        return super().open_action()

