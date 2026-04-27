# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date


class AccountMissingTransaction(models.TransientModel):
    _name = 'account.missing.transaction.wizard'
    _description = 'Wizard for missing transactions'

    date = fields.Date(
        string="Starting Date",
        default=lambda self: fields.Date.today() - relativedelta(months=1),
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'bank'), ('account_online_account_id', '!=', 'False'), ('account_online_link_state', '=', 'connected')]"
    )

    def _get_manual_bank_statement_lines(self):
        return self.env['account.bank.statement.line'].search(
            domain=[
                ('date', '>=', self.date),
                ('journal_id', '=', self.journal_id.id),
                ('online_transaction_identifier', '=', False),
            ],
        )

    def action_fetch_missing_transaction(self):
        self.ensure_one()

        if not self.journal_id:
            raise UserError(_("You have to select one journal to continue."))

        if not self.date:
            raise UserError(_("Please enter a valid Starting Date to continue."))

        if self.journal_id.account_online_link_state != 'connected':
            raise UserError(_("You can't find missing transactions for a journal that isn't connected."))

        fetched_transactions = self.journal_id.account_online_account_id._retrieve_transactions(date=self.date, include_pendings=True)
        transactions = fetched_transactions.get('transactions') or []
        pendings = fetched_transactions.get('pendings') or []

        pendings = [{**pending, 'state': 'pending'} for pending in pendings]
        filtered_transactions = self.journal_id.account_online_account_id._get_filtered_transactions(transactions + pendings)

        transient_transactions_ids = self.env['account.bank.statement.line.transient'].create(filtered_transactions)

        return {
            'name': _("Missing and Pending Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line.transient',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('id', 'in', transient_transactions_ids.ids)],
            'context': {
                'has_manual_entries': bool(self._get_manual_bank_statement_lines()),
                'is_fetch_before_creation': self.date < self.journal_id.account_online_link_id.create_date.date(),
                'account_online_link_create_date': format_date(self.env, self.journal_id.account_online_link_id.create_date),
                'search_default_filter_posted': bool([transaction for transaction in filtered_transactions if transaction.get('state') != 'pending']),  # Activate this default filter only if we have posted transactions
            },
        }

    def action_open_manual_bank_statement_lines(self):
        self.ensure_one()
        bank_statement_lines = self._get_manual_bank_statement_lines()

        return {
            'name': _("Manual Bank Statement Lines"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', bank_statement_lines.ids)],
        }
