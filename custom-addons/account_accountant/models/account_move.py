# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
import logging
import math
import re

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import frozendict, SQL


_logger = logging.getLogger(__name__)


DEFERRED_DATE_MIN = '1900-01-01'
DEFERRED_DATE_MAX = '9999-12-31'


class AccountMove(models.Model):
    _inherit = "account.move"

    # Technical field to keep the value of payment_state when switching from invoicing to accounting
    # (using invoicing_switch_threshold setting field). It allows keeping the former payment state, so that
    # we can restore it if the user misconfigured the switch date and wants to change it.
    payment_state_before_switch = fields.Char(string="Payment State Before Switch", copy=False)

    # Deferred management fields
    deferred_move_ids = fields.Many2many(
        string="Deferred Entries",
        comodel_name='account.move',
        relation='account_move_deferred_rel',
        column1='original_move_id',
        column2='deferred_move_id',
        help="The deferred entries created by this invoice",
        copy=False,
    )

    deferred_original_move_ids = fields.Many2many(
        string="Original Invoices",
        comodel_name='account.move',
        relation='account_move_deferred_rel',
        column1='deferred_move_id',
        column2='original_move_id',
        help="The original invoices that created the deferred entries",
        copy=False,
    )

    deferred_entry_type = fields.Selection(
        string="Deferred Entry Type",
        selection=[
            ('expense', 'Deferred Expense'),
            ('revenue', 'Deferred Revenue'),
        ],
        compute='_compute_deferred_entry_type',
        copy=False,
    )

    @api.model
    def _get_invoice_in_payment_state(self):
        # OVERRIDE to enable the 'in_payment' state on invoices.
        return 'in_payment'

    def _post(self, soft=True):
        # Deferred management
        posted = super()._post(soft)
        for move in self:
            if move._get_deferred_entries_method() == 'on_validation' and any(move.line_ids.mapped('deferred_start_date')):
                move._generate_deferred_entries()
        return posted

    def action_post(self):
        # EXTENDS 'account' to trigger the CRON auto-reconciling the statement lines.
        res = super().action_post()
        if self.statement_line_id and not self._context.get('skip_statement_line_cron_trigger'):
            self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()
        return res

    def button_draft(self):
        if any(len(deferral_move.deferred_original_move_ids) > 1 for deferral_move in self.deferred_move_ids):
            raise UserError(_("You cannot reset to draft an invoice that is grouped in deferral entry. You can create a credit note instead."))
        reversed_moves = self.deferred_move_ids._unlink_or_reverse()
        if reversed_moves:
            for move in reversed_moves:
                move.date = move._get_accounting_date(move.date, move._affect_tax_report())
            self.deferred_move_ids |= reversed_moves
        return super().button_draft()

    # ============================= START - Deferred Management ====================================

    def _get_deferred_entries_method(self):
        self.ensure_one()
        if self.is_outbound():
            return self.company_id.generate_deferred_expense_entries_method
        return self.company_id.generate_deferred_revenue_entries_method

    @api.depends('deferred_original_move_ids')
    def _compute_deferred_entry_type(self):
        for move in self:
            if move.deferred_original_move_ids:
                move.deferred_entry_type = 'expense' if move.deferred_original_move_ids[0].is_outbound() else 'revenue'
            else:
                move.deferred_entry_type = False

    @api.model
    def _get_deferred_diff_dates(self, start, end):
        """
        Returns the number of months between two dates [start, end[
        The computation is done by using months of 30 days so that the deferred amount for february
        (28-29 days), march (31 days) and april (30 days) are all the same (in case of monthly computation).
        See test_deferred_management_get_diff_dates for examples.
        """
        if start > end:
            start, end = end, start
        nb_months = end.month - start.month + 12 * (end.year - start.year)
        start_day, end_day = start.day, end.day
        if start_day == calendar.monthrange(start.year, start.month)[1]:
            start_day = 30
        if end_day == calendar.monthrange(end.year, end.month)[1]:
            end_day = 30
        nb_days = end_day - start_day
        return (nb_months * 30 + nb_days) / 30

    @api.model
    def _get_deferred_period_amount(self, method, period_start, period_end, line_start, line_end, balance):
        """
        Returns the amount to defer for the given period taking into account the deferred method (day/month/full_months).
        """
        if method == 'day':
            amount_per_day = balance / (line_end - line_start).days
            return (period_end - period_start).days * amount_per_day if period_end > line_start else 0
        elif method == "month":
            amount_per_month = balance / self._get_deferred_diff_dates(line_end, line_start)
            nb_months_period = self._get_deferred_diff_dates(period_end, period_start)
            return nb_months_period * amount_per_month if period_end > line_start and period_end > period_start else 0
        elif method == "full_months":
            line_diff = self._get_deferred_diff_dates(line_end, line_start)
            period_diff = self._get_deferred_diff_dates(period_end, period_start)
            if line_diff < 1:
                amount = balance
            else:
                if line_end.day == calendar.monthrange(line_end.year, line_end.month)[1]:
                    line_diff = math.ceil(line_diff)
                else:
                    line_diff = math.floor(line_diff)
                if period_end.day == calendar.monthrange(period_end.year, period_end.month)[1] or line_end != period_end:
                    period_diff = math.ceil(period_diff)
                else:
                    period_diff = math.floor(period_diff)
                amount_per_month = balance / line_diff
                amount = period_diff * amount_per_month
            return amount if period_end > line_start and period_end > period_start else 0

    @api.model
    def _get_deferred_amounts_by_line(self, lines, periods):
        """
        :return: a list of dictionaries containing the deferred amounts for each line and each period
        E.g. (where period1 = (date1, date2, label1), period2 = (date2, date3, label2), ...)
        [
            {'account_id': 1, period_1: 100, period_2: 200},
            {'account_id': 1, period_1: 100, period_2: 200},
            {'account_id': 2, period_1: 300, period_2: 400},
        ]
        """
        values = []
        for line in lines:
            line_start = fields.Date.to_date(line['deferred_start_date'])
            line_end = fields.Date.to_date(line['deferred_end_date'])
            if line_end < line_start:
                # This normally shouldn't happen, but if it does, would cause calculation errors later on.
                # To not make the reports crash, we just set both dates to the same day.
                # The user should fix the dates manually.
                line_end = line_start

            columns = {}
            for period in periods:
                if period[2] == 'not_started' and line_start <= period[0]:
                    # The 'Not Started' column only considers lines starting the deferral after the report end date
                    columns[period] = 0.0
                    continue
                # periods = [Total, Not Started, Before, ..., Current, ..., Later]
                # The dates to calculate the amount for the current period
                period_start = max(period[0], line_start)
                period_end = min(period[1], line_end)
                if (
                    period[2] in ('not_started', 'later') and period[0] < line_start
                    or len(periods) <= 1
                    or period[2] not in ('not_started', 'before', 'later')
                ):
                    # We are subtracting 1 day from `period_start` because the start date should be included when:
                    # - in the 'Not Started' or 'Later' period if the deferral has not started yet (line_start, line_end)
                    # - we only have one period
                    # - not in the 'Not Started', 'Before' or 'Later' period
                    period_start -= relativedelta(days=1)
                columns[period] = self._get_deferred_period_amount(
                    self.env.company.deferred_amount_computation_method,
                    period_start, period_end,
                    line_start - relativedelta(days=1), line_end,  # -1 because we want to include the start date
                    line['balance']
                )

            values.append({
                **self.env['account.move.line']._get_deferred_amounts_by_line_values(line),
                **columns,
            })
        return values

    @api.model
    def _get_deferred_lines(self, line, deferred_account, period, ref, force_balance=None):
        """
        :return: a list of Command objects to create the deferred lines of a single given period
        """
        deferred_amounts = self._get_deferred_amounts_by_line(line, [period])[0]
        balance = deferred_amounts[period] if force_balance is None else force_balance
        return [
            Command.create({
                **self.env['account.move.line']._get_deferred_lines_values(account.id, coeff * balance, ref, line.analytic_distribution, line),
                'partner_id': line.partner_id.id,
                'product_id': line.product_id.id,
            })
            for (account, coeff) in [(deferred_amounts['account_id'], 1), (deferred_account, -1)]
        ]

    def _generate_deferred_entries(self):
        """
        Generates the deferred entries for the invoice.
        """
        self.ensure_one()
        if self.is_entry():
            raise UserError(_("You cannot generate deferred entries for a miscellaneous journal entry."))
        is_deferred_expense = self.is_purchase_document()
        deferred_account = self.company_id.deferred_expense_account_id if is_deferred_expense else self.company_id.deferred_revenue_account_id
        deferred_journal = self.company_id.deferred_journal_id
        if not deferred_journal:
            raise UserError(_("Please set the deferred journal in the accounting settings."))
        if not deferred_account:
            raise UserError(_("Please set the deferred accounts in the accounting settings."))

        for line in self.line_ids.filtered(lambda l: l.deferred_start_date and l.deferred_end_date):
            periods = line._get_deferred_periods()
            if not periods:
                continue

            ref = _("Deferral of %s", line.move_id.name or '')
            # Defer the current invoice
            move_fully_deferred = self.create({
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(line.move_id.ids)],
                'journal_id': deferred_journal.id,
                'company_id': self.company_id.id,
                'partner_id': line.partner_id.id,
                'date': line.move_id.date,
                'auto_post': 'at_date',
                'ref': ref,
            })
            # We write the lines after creation, to make sure the `deferred_original_move_ids` is set.
            # This way we can avoid adding taxes for deferred moves.
            move_fully_deferred.write({
                'line_ids': [
                    Command.create(
                        self.env['account.move.line']._get_deferred_lines_values(account.id, coeff * line.balance, ref, line.analytic_distribution, line)
                    ) for (account, coeff) in [(line.account_id, -1), (deferred_account, 1)]
                ],
            })

            # Create the deferred entries for the periods [deferred_start_date, deferred_end_date]
            deferral_moves = self.create([{
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(line.move_id.ids)],
                'journal_id': deferred_journal.id,
                'partner_id': line.partner_id.id,
                'date': period[1],
                'auto_post': 'at_date',
                'ref': ref,
            } for period in periods])
            remaining_balance = line.balance
            for period_index, (period, deferral_move) in enumerate(zip(periods, deferral_moves)):
                # For the last deferral move the balance is forced to remaining balance to avoid rounding errors
                force_balance = remaining_balance if period_index == len(periods) - 1 else None
                # Same as before, to avoid adding taxes for deferred moves.
                deferral_move.write({
                    'line_ids': self._get_deferred_lines(line, deferred_account, period, ref, force_balance=force_balance),
                })
                remaining_balance -= deferral_move.line_ids[0].balance
                # Avoid having deferral moves with a total amount of 0
                if deferral_move.currency_id.is_zero(deferral_move.amount_total):
                    deferral_moves -= deferral_move
                    deferral_move.unlink()

            deferred_moves = move_fully_deferred + deferral_moves
            if len(deferral_moves) == 1 and move_fully_deferred.date.month == deferral_moves.date.month:
                # If, after calculation, we have 2 deferral entries in the same month, it means that
                # they simply cancel out each other, so there is no point in creating them.
                deferred_moves.unlink()
                continue
            line.move_id.deferred_move_ids |= deferred_moves
            deferred_moves._post(soft=True)

    def open_deferred_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Deferred Entries"),
            'res_model': 'account.move.line',
            'domain': [('id', 'in', self.deferred_move_ids.line_ids.ids)],
            'views': [(False, 'tree'), (False, 'form')],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            }
        }

    def open_deferred_original_entry(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _("Original Deferred Entries"),
            'res_model': 'account.move.line',
            'domain': [('id', 'in', self.deferred_original_move_ids.line_ids.ids)],
            'views': [(False, 'tree'), (False, 'form')],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            }
        }
        if len(self.deferred_original_move_ids) == 1:
            action.update({
                'res_model': 'account.move',
                'res_id': self.deferred_original_move_ids[0].id,
                'views': [(False, 'form')],
            })
        return action

    # ============================= END - Deferred management ======================================

    def action_open_bank_reconciliation_widget(self):
        return self.statement_line_id._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_journal_id': self.statement_line_id.journal_id.id,
                'search_default_statement_line_id': self.statement_line_id.id,
                'default_st_line_id': self.statement_line_id.id,
            }
        )

    def action_open_bank_reconciliation_widget_statement(self):
        return self.statement_line_id._action_open_bank_reconciliation_widget(
            extra_domain=[('statement_id', 'in', self.statement_id.ids)],
        )

    def action_open_business_doc(self):
        if self.statement_line_id:
            return self.action_open_bank_reconciliation_widget()
        else:
            action = super().action_open_business_doc()
            # prevent propagation of the following keys
            action['context'] = action.get('context', {}) | {
                'preferred_aml_value': None,
                'preferred_aml_currency_id': None,
            }
            return action

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        res += self.statement_line_id.statement_id.attachment_ids
        return res

    @contextmanager
    def _get_edi_creation(self):
        with super()._get_edi_creation() as move:
            previous_lines = move.invoice_line_ids
            yield move.with_context(disable_onchange_name_predictive=True)
            for line in move.invoice_line_ids - previous_lines:
                line._onchange_name_predictive()


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    move_attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment')

    # Deferred management fields
    deferred_start_date = fields.Date(
        string="Start Date",
        compute='_compute_deferred_start_date', store=True, readonly=False,
        index='btree_not_null',
        copy=False,
        help="Date at which the deferred expense/revenue starts"
    )
    deferred_end_date = fields.Date(
        string="End Date",
        index='btree_not_null',
        copy=False,
        help="Date at which the deferred expense/revenue ends"
    )
    has_deferred_moves = fields.Boolean(compute='_compute_has_deferred_moves')

    def _order_to_sql(self, order, query, alias=None, reverse=False):
        sql_order = super()._order_to_sql(order, query, alias, reverse)
        preferred_aml_residual_value = self._context.get('preferred_aml_value')
        preferred_aml_currency_id = self._context.get('preferred_aml_currency_id')
        if preferred_aml_residual_value and preferred_aml_currency_id and order == self._order:
            currency = self.env['res.currency'].browse(preferred_aml_currency_id)
            # using round since currency.round(55.55) = 55.550000000000004
            preferred_aml_residual_value = round(preferred_aml_residual_value, currency.decimal_places)
            sql_residual_currency = self._field_to_sql(alias or self._table, 'amount_residual_currency', query)
            sql_currency = self._field_to_sql(alias or self._table, 'currency_id', query)
            return SQL(
                "ROUND(%(residual_currency)s, %(decimal_places)s) = %(value)s "
                "AND %(currency)s = %(currency_id)s DESC, %(order)s",
                residual_currency=sql_residual_currency,
                decimal_places=currency.decimal_places,
                value=preferred_aml_residual_value,
                currency=sql_currency,
                currency_id=currency.id,
                order=sql_order,
            )
        return sql_order

    def copy_data(self, default=None):
        data_list = super().copy_data(default=default)
        for line, values in zip(self, data_list):
            if 'move_reverse_cancel' in self._context:
                values['deferred_start_date'] = line.deferred_start_date
                values['deferred_end_date'] = line.deferred_end_date
        return data_list

    def write(self, vals):
        """ Prevent changing the account of a move line when there are already deferral entries.
        """
        if 'account_id' in vals:
            for line in self:
                if (
                    line.has_deferred_moves
                    and line.deferred_start_date
                    and line.deferred_end_date
                    and vals['account_id'] != line.account_id.id
                ):
                    raise UserError(_(
                        "You cannot change the account for a deferred line in %(move_name)s if it has already been deferred.",
                        move_name=line.move_id.display_name
                    ))
        return super().write(vals)

    # ============================= START - Deferred management ====================================
    def _compute_has_deferred_moves(self):
        for line in self:
            line.has_deferred_moves = line.move_id.deferred_move_ids

    def _is_compatible_account(self):
        self.ensure_one()
        return (
            self.move_id.is_purchase_document()
            and
            self.account_id.account_type in ('expense', 'expense_depreciation', 'expense_direct_cost')
        ) or (
            self.move_id.is_sale_document()
            and
            self.account_id.account_type in ('income', 'income_other')
        )

    @api.onchange('deferred_start_date')
    def _onchange_deferred_start_date(self):
        if not self._is_compatible_account():
            self.deferred_start_date = False

    @api.onchange('deferred_end_date')
    def _onchange_deferred_end_date(self):
        if not self._is_compatible_account():
            self.deferred_end_date = False

    @api.depends('deferred_end_date', 'move_id.invoice_date', 'move_id.state')
    def _compute_deferred_start_date(self):
        for line in self:
            if not line.deferred_start_date and line.move_id.invoice_date and line.deferred_end_date:
                line.deferred_start_date = line.move_id.invoice_date

    @api.constrains('deferred_start_date', 'deferred_end_date', 'account_id')
    def _check_deferred_dates(self):
        for line in self:
            if line.deferred_start_date and not line.deferred_end_date:
                raise UserError(_("You cannot create a deferred entry with a start date but no end date."))
            elif line.deferred_start_date and line.deferred_end_date and line.deferred_start_date > line.deferred_end_date:
                raise UserError(_("You cannot create a deferred entry with a start date later than the end date."))

    @api.model
    def _get_deferred_tax_key(self, line, tax_key, tax_repartition_line_id):
        if (
            line.deferred_start_date
            and line.deferred_end_date
            and line._is_compatible_account()
            and tax_repartition_line_id
            and not tax_repartition_line_id.use_in_tax_closing
        ):
            return frozendict(
                **tax_key,
                deferred_start_date=line.deferred_start_date,
                deferred_end_date=line.deferred_end_date,
            )
        return tax_key

    @api.depends('deferred_start_date', 'deferred_end_date')
    def _compute_tax_key(self):
        super()._compute_tax_key()
        for line in self:
            line.tax_key = self._get_deferred_tax_key(line, line.tax_key, line.tax_repartition_line_id)

    @api.depends('deferred_start_date', 'deferred_end_date')
    def _compute_all_tax(self):
        super()._compute_all_tax()
        for line in self:
            for key in list(line.compute_all_tax.keys()):
                tax_repartition_line_id = self.env['account.tax.repartition.line'].browse(key.get('tax_repartition_line_id'))
                new_key = self._get_deferred_tax_key(line, key, tax_repartition_line_id)
                line.compute_all_tax[new_key] = line.compute_all_tax.pop(key)

    @api.model
    def _get_deferred_ends_of_month(self, start_date, end_date):
        """
        :return: a list of dates corresponding to the end of each month between start_date and end_date.
            See test_get_ends_of_month for examples.
        """
        dates = []
        while start_date <= end_date:
            start_date = start_date + relativedelta(day=31)  # Go to end of month
            dates.append(start_date)
            start_date = start_date + relativedelta(days=1)  # Go to first day of next month
        return dates

    def _get_deferred_periods(self):
        """
        :return: a list of tuples (start_date, end_date) during which the deferred expense/revenue is spread.
            If there is only one period containing the move date, it means that we don't need to defer the
            expense/revenue since the invoice deferral and its deferred entry will be created on the same day and will
            thus cancel each other.
        """
        self.ensure_one()
        periods = [
            (max(self.deferred_start_date, date.replace(day=1)), min(date, self.deferred_end_date), 'current')
            for date in self._get_deferred_ends_of_month(self.deferred_start_date, self.deferred_end_date)
        ]
        if not periods or len(periods) == 1 and periods[0][0].replace(day=1) == self.date.replace(day=1):
            return []
        else:
            return periods

    @api.model
    def _get_deferred_amounts_by_line_values(self, line):
        return {
            'account_id': line['account_id'],
            'balance': line['balance'],
            'move_id': line['move_id'],
        }

    @api.model
    def _get_deferred_lines_values(self, account_id, balance, ref, analytic_distribution, line=None):
        return {
            'account_id': account_id,
            'balance': balance,
            'name': ref,
            'analytic_distribution': analytic_distribution,
        }

    # ============================= END - Deferred management ====================================

    def _get_computed_taxes(self):
        if self.move_id.deferred_original_move_ids:
            # If this line is part of a deferral move, do not (re)calculate its taxes automatically.
            # Doing so might unvoluntarily impact the tax report in deferral moves (if a default tax is set on the account).
            return self.tax_ids
        return super()._get_computed_taxes()

    def _compute_attachment(self):
        for record in self:
            record.move_attachment_ids = self.env['ir.attachment'].search(expression.OR(record._get_attachment_domains()))

    def action_reconcile(self):
        """ This function is called by the 'Reconcile' button of account.move.line's
        tree view. It performs reconciliation between the selected lines.
        - If the reconciliation can be done directly we do it silently
        - Else, if a write-off is required we open the wizard to let the client enter required information
        """
        wizard = self.env['account.reconcile.wizard'].with_context(
            active_model='account.move.line',
            active_ids=self.ids,
        ).new({})
        return wizard._action_open_wizard() if (wizard.is_write_off_required or wizard.force_partials) else wizard.reconcile()

    def _get_predict_postgres_dictionary(self):
        lang = self._context.get('lang') and self._context.get('lang')[:2]
        return {'fr': 'french'}.get(lang, 'english')

    def _build_predictive_query(self, additional_domain=None):
        move_query = self.env['account.move']._where_calc([
            ('move_type', '=', self.move_id.move_type),
            ('state', '=', 'posted'),
            ('partner_id', '=', self.move_id.partner_id.id),
            ('company_id', '=', self.move_id.journal_id.company_id.id or self.env.company.id),
        ])
        move_query.order = 'account_move.invoice_date'
        move_query.limit = int(self.env["ir.config_parameter"].sudo().get_param(
            "account.bill.predict.history.limit",
            '100',
        ))
        return self.env['account.move.line']._where_calc([
            ('move_id', 'in', move_query),
            ('display_type', '=', 'product'),
        ] + (additional_domain or []))

    def _predicted_field(self, field, query=None, additional_queries=None):
        r"""Predict the most likely value based on the previous history.

        This method uses postgres tsvector in order to try to deduce a field of
        an invoice line based on the text entered into the name (description)
        field and the partner linked.
        We only limit the search on the previous 100 entries, which according
        to our tests bore the best results. However this limit parameter is
        configurable by creating a config parameter with the key:
        account.bill.predict.history.limit

        For information, the tests were executed with a dataset of 40 000 bills
        from a live database, We split the dataset in 2, removing the 5000 most
        recent entries and we tried to use this method to guess the account of
        this validation set based on the previous entries.
        The result is roughly 90% of success.

        :param field (str): the sql column that has to be predicted.
            /!\ it is injected in the query without any checks.
        :param query (osv.Query): the query object on account.move.line that is
            used to do the ranking, containing the right domain, limit, etc. If
            it is omitted, a default query is used.
        :param additional_queries (list<str>): can be used in addition to the
            default query on account.move.line to fetch data coming from other
            tables, to have starting values for instance.
            /!\ it is injected in the query without any checks.
        """
        if not self.name or not self.partner_id:
            return False

        psql_lang = self._get_predict_postgres_dictionary()
        description = self.name + ' account_move_line' # give more priority to main query than additional queries
        parsed_description = re.sub(r"[*&()|!':<>=%/~@,.;$\[\]]+", " ", description)
        parsed_description = ' | '.join(parsed_description.split())

        from_clause, where_clause, params = (query if query is not None else self._build_predictive_query()).get_sql()
        mask_from_clause, mask_where_clause, mask_params = self._build_predictive_query().get_sql()
        try:
            account_move_line = self.env.cr.mogrify(
                f"SELECT account_move_line.* FROM {mask_from_clause} WHERE {mask_where_clause}",
                mask_params,
            ).decode()
            group_by_clause = ""
            if "(" in field:  # aggregate function
                group_by_clause = "GROUP BY account_move_line.id, account_move_line.name, account_move_line.partner_id"
            self.env.cr.execute(f"""
                WITH account_move_line AS MATERIALIZED ({account_move_line}),
                source AS ({'(' + ') UNION ALL ('.join([self.env.cr.mogrify(f'''
                    SELECT {field} AS prediction,
                           setweight(to_tsvector(%%(lang)s, account_move_line.name), 'B')
                           || setweight(to_tsvector('simple', 'account_move_line'), 'A') AS document
                      FROM {from_clause}
                     WHERE {where_clause}
                  {group_by_clause}
                ''', params).decode()] + (additional_queries or [])) + ')'}
                ),

                ranking AS (
                    SELECT prediction, ts_rank(source.document, query_plain) AS rank
                      FROM source, to_tsquery(%(lang)s, %(description)s) query_plain
                     WHERE source.document @@ query_plain
                )

                SELECT prediction, MAX(rank) AS ranking, COUNT(*)
                  FROM ranking
              GROUP BY prediction
              ORDER BY ranking DESC, count DESC
                 LIMIT 2
            """, {
                'lang': psql_lang,
                'description': parsed_description,
            })
            result = self.env.cr.dictfetchall()
            if result:
                # Only confirm the prediction if it's at least 10% better than the second one
                if len(result) > 1 and result[0]['ranking'] < 1.1 * result[1]['ranking']:
                    return False
                return result[0]['prediction']
        except Exception:
            # In case there is an error while parsing the to_tsquery (wrong character for example)
            # We don't want to have a blocking traceback, instead return False
            _logger.exception('Error while predicting invoice line fields')
        return False

    def _predict_taxes(self):
        field = 'array_agg(account_move_line__tax_rel__tax_ids.id ORDER BY account_move_line__tax_rel__tax_ids.id)'
        query = self._build_predictive_query()
        query.left_join('account_move_line', 'id', 'account_move_line_account_tax_rel', 'account_move_line_id', 'tax_rel')
        query.left_join('account_move_line__tax_rel', 'account_tax_id', 'account_tax', 'id', 'tax_ids')
        query.add_where('account_move_line__tax_rel__tax_ids.active IS NOT FALSE')
        predicted_tax_ids = self._predicted_field(field, query)
        if predicted_tax_ids == [None]:
            return False
        if predicted_tax_ids is not False and set(predicted_tax_ids) != set(self.tax_ids.ids):
            return predicted_tax_ids
        return False

    def _predict_specific_tax(self, amount_type, amount, type_tax_use):
        field = 'array_agg(account_move_line__tax_rel__tax_ids.id ORDER BY account_move_line__tax_rel__tax_ids.id)'
        query = self._build_predictive_query()
        query.left_join('account_move_line', 'id', 'account_move_line_account_tax_rel', 'account_move_line_id', 'tax_rel')
        query.left_join('account_move_line__tax_rel', 'account_tax_id', 'account_tax', 'id', 'tax_ids')
        query.add_where("""
            account_move_line__tax_rel__tax_ids.active IS NOT FALSE
            AND account_move_line__tax_rel__tax_ids.amount_type = %s
            AND account_move_line__tax_rel__tax_ids.type_tax_use = %s
            AND account_move_line__tax_rel__tax_ids.amount = %s
        """, (amount_type, type_tax_use, amount))
        return self._predicted_field(field, query)

    def _predict_product(self):
        predict_product = int(self.env['ir.config_parameter'].sudo().get_param('account_predictive_bills.predict_product', '1'))
        if predict_product and self.company_id.predict_bill_product:
            query = self._build_predictive_query(['|', ('product_id', '=', False), ('product_id.active', '=', True)])
            predicted_product_id = self._predicted_field('account_move_line.product_id', query)
            if predicted_product_id and predicted_product_id != self.product_id.id:
                return predicted_product_id
        return False

    def _predict_account(self):
        field = 'account_move_line.account_id'
        if self.move_id.is_purchase_document(True):
            excluded_group = 'income'
        else:
            excluded_group = 'expense'
        account_query = self.env['account.account']._where_calc([
            *self.env['account.account']._check_company_domain(self.move_id.company_id or self.env.company),
            ('deprecated', '=', False),
            ('internal_group', 'not in', (excluded_group, 'off_balance')),
            ('account_type', 'not in', ('liability_payable', 'asset_receivable')),
        ])
        psql_lang = self._get_predict_postgres_dictionary()
        additional_queries = [self.env.cr.mogrify(*account_query.select(
            "account_account.id AS account_id",
            SQL("setweight(to_tsvector(%s, name), 'B') AS document", psql_lang),
        )).decode()]
        query = self._build_predictive_query([('account_id', 'in', account_query)])

        predicted_account_id = self._predicted_field(field, query, additional_queries)
        if predicted_account_id and predicted_account_id != self.account_id.id:
            return predicted_account_id
        return False

    @api.onchange('name')
    def _onchange_name_predictive(self):
        if ((self.move_id.quick_edit_mode or self.move_id.move_type == 'in_invoice') and self.name and self.display_type == 'product'
            and not self.env.context.get('disable_onchange_name_predictive', False)):

            if not self.product_id:
                predicted_product_id = self._predict_product()
                if predicted_product_id:
                    name = self.name
                    self.product_id = predicted_product_id
                    self.name = name

            # In case no product has been set, the account and taxes
            # will not depend on any product and can thus be predicted
            if not self.product_id:
                # Predict account.
                predicted_account_id = self._predict_account()
                if predicted_account_id:
                    self.account_id = predicted_account_id

                # Predict taxes
                predicted_tax_ids = self._predict_taxes()
                if predicted_tax_ids:
                    self.tax_ids = [Command.set(predicted_tax_ids)]

    def _read_group_groupby(self, groupby_spec, query):
        # enable grouping by :abs_rounded on fields, which is useful when trying
        # to match positive and negative amounts
        if ':' in groupby_spec:
            fname, method = groupby_spec.split(':')
            if fname in self and method == 'abs_rounded':  # field in self avoids possible injections
                # rounds with the used currency settings
                sql_field = self._field_to_sql(self._table, fname, query)
                currency_alias = query.left_join(self._table, 'currency_id', 'res_currency', 'id', 'currency_id')
                sql_decimal = self.env['res.currency']._field_to_sql(currency_alias, 'decimal_places', query)
                sql_group = SQL('ROUND(ABS(%s), %s)', sql_field, sql_decimal)
                return sql_group, [fname, 'currency_id']

        return super()._read_group_groupby(groupby_spec, query)

    def _read_group_having(self, having_domain, query):
        # Enable to use HAVING clause that sum rounded values depending on the
        # currency precision settings. Limitation: we only handle a having
        # clause of one element with that specific method :sum_rounded.
        if len(having_domain) == 1:
            left, operator, right = having_domain[0]
            fname, *funcs = left.split(':')
            if fname in self and funcs == ['sum_rounded']:  # fname in self avoids possible injections
                sql_field = self._field_to_sql(self._table, fname, query)
                currency_alias = query.left_join(self._table, 'currency_id', 'res_currency', 'id', 'currency_id')
                sql_decimal = self.env['res.currency']._field_to_sql(currency_alias, 'decimal_places', query)
                sql_operator = expression.SQL_OPERATORS[operator]
                sql_expr = SQL(
                    'SUM(ROUND(%s, %s)) %s %s',
                    sql_field, sql_decimal, sql_operator, right,
                )
                return sql_expr, [fname]
        return super()._read_group_having(having_domain, query)
