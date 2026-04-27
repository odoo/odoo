from odoo import models, fields, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

from datetime import timedelta
from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = 'res.company'

    invoicing_switch_threshold = fields.Date(string="Invoicing Switch Threshold", help="Every payment and invoice before this date will receive the 'From Invoicing' status, hiding all the accounting entries related to it. Use this option after installing Accounting if you were using only Invoicing before, before importing all your actual accounting data in to Odoo.")
    predict_bill_product = fields.Boolean(string="Predict Bill Product")

    sign_invoice = fields.Boolean(string='Display signing field on invoices')
    signing_user = fields.Many2one(comodel_name='res.users')

    # Deferred expense management
    deferred_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Deferred Expense Journal",
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Deferred Expense Account",
    )
    generate_deferred_expense_entries_method = fields.Selection(
        string="Generate Deferred Expense Entries",
        selection=[
            ('on_validation', 'On bill validation'),
            ('manual', 'Manually & Grouped'),
        ],
        default='on_validation',
        required=True,
    )
    deferred_expense_amount_computation_method = fields.Selection(
        string="Deferred Expense Based on",
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('full_months', 'Full Months'),
        ],
        default='month',
        required=True,
    )

    # Deferred revenue management
    deferred_revenue_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Deferred Revenue Journal",
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Deferred Revenue Account",
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        string="Generate Deferred Revenue Entries",
        selection=[
            ('on_validation', 'On bill validation'),
            ('manual', 'Manually & Grouped'),
        ],
        default='on_validation',
        required=True,
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        string="Deferred Revenue Based on",
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('full_months', 'Full Months'),
        ],
        default='month',
        required=True,
    )

    def write(self, vals):
        old_threshold_vals = {}
        for record in self:
            old_threshold_vals[record] = record.invoicing_switch_threshold

        rslt = super(ResCompany, self).write(vals)

        for record in self:
            if 'invoicing_switch_threshold' in vals and old_threshold_vals[record] != vals['invoicing_switch_threshold']:
                self.env['account.move.line'].flush_model(['move_id', 'parent_state'])
                self.env['account.move'].flush_model(['company_id', 'date', 'state', 'payment_state', 'payment_state_before_switch'])
                if record.invoicing_switch_threshold:
                    # If a new date was set as threshold, we switch all the
                    # posted moves and payments before it to 'invoicing_legacy'.
                    # We also reset to posted all the moves and payments that
                    # were 'invoicing_legacy' and were posterior to the threshold
                    self.env.cr.execute("""
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.date >= %(switch_threshold)s
                        and move.company_id = %(company_id)s;

                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and date >= %(switch_threshold)s
                        and company_id = %(company_id)s;

                        update account_move_line aml
                        set parent_state = 'cancel'
                        from account_move move
                        where aml.move_id = move.id
                        and move.state = 'posted'
                        and move.date < %(switch_threshold)s
                        and move.company_id = %(company_id)s;

                        update account_move
                        set state = 'cancel',
                            payment_state_before_switch = payment_state,
                            payment_state = 'invoicing_legacy'
                        where state = 'posted'
                        and date < %(switch_threshold)s
                        and company_id = %(company_id)s;
                    """, {'company_id': record.id, 'switch_threshold': record.invoicing_switch_threshold})
                else:
                    # If the threshold date has been emptied, we re-post all the
                    # invoicing_legacy entries.
                    self.env.cr.execute("""
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.company_id = %(company_id)s;

                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and company_id = %(company_id)s;
                    """, {'company_id': record.id})

                self.env['account.move.line'].invalidate_model(['parent_state'])
                self.env['account.move'].invalidate_model(['state', 'payment_state', 'payment_state_before_switch'])

        return rslt

    def compute_fiscalyear_dates(self, current_date):
        """Compute the start and end dates of the fiscal year where the given 'date' belongs to.

        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
            * [Optionally] record: The fiscal year record.
        """
        self.ensure_one()
        date_str = current_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # Search a fiscal year record containing the date.
        # If a record is found, then no need further computation, we get the dates range directly.
        fiscalyear = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_str),
            ('date_to', '>=', date_str),
        ], limit=1)
        if fiscalyear:
            return {
                'date_from': fiscalyear.date_from,
                'date_to': fiscalyear.date_to,
                'record': fiscalyear,
            }

        date_from, date_to = date_utils.get_fiscal_year(
            current_date, day=self.fiscalyear_last_day, month=int(self.fiscalyear_last_month))

        date_from_str = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to_str = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # Search for fiscal year records reducing the delta between the date_from/date_to.
        # This case could happen if there is a gap between two fiscal year records.
        # E.g. two fiscal year records: 2017-01-01 -> 2017-02-01 and 2017-03-01 -> 2017-12-31.
        # => The period 2017-02-02 - 2017-02-30 is not covered by a fiscal year record.

        fiscalyear_from = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_from_str),
            ('date_to', '>=', date_from_str),
        ], limit=1)
        if fiscalyear_from:
            date_from = fiscalyear_from.date_to + timedelta(days=1)

        fiscalyear_to = self.env['account.fiscal.year'].search([
            ('company_id', '=', self.id),
            ('date_from', '<=', date_to_str),
            ('date_to', '>=', date_to_str),
        ], limit=1)
        if fiscalyear_to:
            date_to = fiscalyear_to.date_from - timedelta(days=1)

        return {'date_from': date_from, 'date_to': date_to}

    def _get_unreconciled_statement_lines_redirect_action(self, unreconciled_statement_lines):
        # OVERRIDE account
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('id', 'in', unreconciled_statement_lines.ids)],
            name=_('Unreconciled statements lines'),
        )
