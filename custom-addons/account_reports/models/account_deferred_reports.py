# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import models, fields, _, api, Command
from odoo.exceptions import UserError
from odoo.tools import groupby
from odoo.addons.account_accountant.models.account_move import DEFERRED_DATE_MIN, DEFERRED_DATE_MAX


class DeferredReportCustomHandler(models.AbstractModel):
    _name = 'account.deferred.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Deferred Expense Report Custom Handler'

    def _get_deferred_report_type(self):
        raise NotImplementedError("This method is not implemented in the deferred report handler.")

    ############################################
    # DEFERRED COMMON (DISPLAY AND GENERATION) #
    ############################################

    def _get_domain(self, report, options, filter_already_generated=False, filter_not_started=False):
        domain = report._get_options_domain(options, "from_beginning")
        account_types = ('expense', 'expense_depreciation', 'expense_direct_cost') if self._get_deferred_report_type() == 'expense' else ('income', 'income_other')
        domain += [
            ('account_id.account_type', 'in', account_types),
            ('deferred_start_date', '!=', False),
            ('deferred_end_date', '!=', False),
            ('deferred_end_date', '>=', options['date']['date_from']),
            ('move_id.date', '<=', options['date']['date_to']),
        ]
        domain += [  # Exclude if entirely inside the period
            '!', '&', '&', '&', '&', '&',
            ('deferred_start_date', '>=', options['date']['date_from']),
            ('deferred_start_date', '<=', options['date']['date_to']),
            ('deferred_end_date', '>=', options['date']['date_from']),
            ('deferred_end_date', '<=', options['date']['date_to']),
            ('move_id.date', '>=', options['date']['date_from']),
            ('move_id.date', '<=', options['date']['date_to']),
        ]
        if filter_already_generated:
            domain += [
                ('deferred_end_date', '>=', options['date']['date_from']),
                '!',
                    '&',
                    ('move_id.deferred_move_ids.date', '=', options['date']['date_to']),
                    ('move_id.deferred_move_ids.state', '=', 'posted'),
            ]
        if filter_not_started:
            domain += [('deferred_start_date', '>', options['date']['date_to'])]
        return domain

    @api.model
    def _get_select(self):
        return [
            "account_move_line.id AS line_id",
            "account_move_line.account_id AS account_id",
            "account_move_line.partner_id AS partner_id",
            "account_move_line.name AS line_name",
            "account_move_line.deferred_start_date AS deferred_start_date",
            "account_move_line.deferred_end_date AS deferred_end_date",
            "account_move_line.deferred_end_date - account_move_line.deferred_start_date AS diff_days",
            "account_move_line.balance AS balance",
            "account_move_line.analytic_distribution AS analytic_distribution",
            "account_move_line__move_id.id as move_id",
            "account_move_line__move_id.name AS move_name",
            "account_move_line__account_id.name AS account_name",
        ]

    def _get_lines(self, report, options, filter_already_generated=False):
        domain = self._get_domain(report, options, filter_already_generated)
        tables, where_clause, where_params = report._query_get(options, domain=domain, date_scope='from_beginning')
        select_clause = ', '.join(self._get_select())

        query = f"""
        SELECT {select_clause}
        FROM {tables}
        WHERE {where_clause}
        ORDER BY "account_move_line"."deferred_start_date", "account_move_line"."id"
        """

        self.env.cr.execute(query, where_params)
        res = self.env.cr.dictfetchall()
        return res

    @api.model
    def _get_grouping_keys_deferred_lines(self, filter_already_generated=False):
        return ('account_id',)

    @api.model
    def _group_by_deferred_keys(self, line, filter_already_generated=False):
        return tuple(line[k] for k in self._get_grouping_keys_deferred_lines(filter_already_generated))

    @api.model
    def _get_grouping_keys_deferral_lines(self):
        return ()

    @api.model
    def _group_by_deferral_keys(self, line):
        return tuple(line[k] for k in self._get_grouping_keys_deferral_lines())

    @api.model
    def _group_deferred_amounts_by_account(self, deferred_amounts_by_line, periods, is_reverse, filter_already_generated=False):
        """
        Groups the deferred amounts by account and computes the totals for each account for each period.
        And the total for all accounts for each period.
        E.g. (where period1 = (date1, date2, label1), period2 = (date2, date3, label2), ...)
        {
            self._get_grouping_keys_deferred_lines(): {
                'account_id': account1, 'amount_total': 600, period_1: 200, period_2: 400
            },
            self._get_grouping_keys_deferred_lines(): {
                'account_id': account2, 'amount_total': 700, period_1: 300, period_2: 400
            },
        }, {'totals_aggregated': 1300, period_1: 500, period_2: 800}
        """
        deferred_amounts_by_line = groupby(deferred_amounts_by_line, key=lambda x: self._group_by_deferred_keys(x, filter_already_generated))
        totals_per_key = {}  # {key: {**self._get_grouping_keys_deferral_lines(), total, before, current, later}}
        totals_aggregated_by_period = {period: 0 for period in periods + ['totals_aggregated']}
        sign = 1 if is_reverse else -1
        for key, lines_per_key in deferred_amounts_by_line:
            lines_per_key = list(lines_per_key)
            current_key_totals = self._get_current_key_totals_dict(lines_per_key, sign)
            totals_aggregated_by_period['totals_aggregated'] += current_key_totals['amount_total']
            for period in periods:
                current_key_totals[period] = sign * sum(line[period] for line in lines_per_key)
                totals_aggregated_by_period[period] += self.env.company.currency_id.round(current_key_totals[period])
            totals_per_key[key] = current_key_totals
        return totals_per_key, totals_aggregated_by_period

    ###########################
    # DEFERRED REPORT DISPLAY #
    ###########################

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportFilters': 'account_reports.DeferredFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options_per_col_group = report._split_options_per_column_group(options)
        for column_dict in options['columns']:
            column_options = options_per_col_group[column_dict['column_group_key']]
            column_dict['name'] = column_options['date']['string']
            column_dict['date_from'] = column_options['date']['date_from']
            column_dict['date_to'] = column_options['date']['date_to']

        options['columns'] = list(reversed(options['columns']))
        total_column = [{
            **options['columns'][0],
            'name': _('Total'),
            'expression_label': 'total',
            'date_from': DEFERRED_DATE_MIN,
            'date_to': DEFERRED_DATE_MAX,
        }]
        not_started_column = [{
            **options['columns'][0],
            'name': _('Not Started'),
            'expression_label': 'not_started',
            'date_from': options['columns'][-1]['date_to'],
            'date_to': DEFERRED_DATE_MAX,
        }]
        before_column = [{
            **options['columns'][0],
            'name': _('Before'),
            'expression_label': 'before',
            'date_from': DEFERRED_DATE_MIN,
            'date_to': options['columns'][0]['date_from'],
        }]
        later_column = [{
            **options['columns'][0],
            'name': _('Later'),
            'expression_label': 'later',
            'date_from': options['columns'][-1]['date_to'],
            'date_to': DEFERRED_DATE_MAX,
        }]
        options['columns'] = total_column + not_started_column + before_column + options['columns'] + later_column
        options['column_headers'] = []
        options['deferred_report_type'] = self._get_deferred_report_type()
        if (
            self._get_deferred_report_type() == 'expense' and self.env.company.generate_deferred_expense_entries_method == 'manual'
            or self._get_deferred_report_type() == 'revenue' and self.env.company.generate_deferred_revenue_entries_method == 'manual'
        ):
            options['buttons'].append({'name': _('Generate entry'), 'action': 'action_generate_entry', 'sequence': 80, 'always_show': True})

    def action_audit_cell(self, options, params):
        """ Open a list of invoices/bills and/or deferral entries for the clicked cell in a deferred report.

        Specifically, we show the following lines, grouped by their journal entry, filtered by the column date bounds:
        - Total: Lines of all invoices/bills being deferred in the current period
        - Not Started: Lines of all deferral entries for which the original invoice/bill date is before or in the
                       current period, but the deferral only starts after the current period, as well as the lines of
                       their original invoices/bills
        - Before: Lines of all deferral entries with a date before the current period, created by invoices/bills also
                  being deferred in the current period, as well as the lines of their original invoices/bills
        - Current: Lines of all deferral entries in the current period, as well as these of their original
                   invoices/bills
        - Later: Lines of all deferral entries with a date after the current period, created by invoices/bills also
                 being deferred in the current period, as well as the lines of their original invoices/bills

        :param dict options: the report's `options`
        :param dict params:  a dict containing:
                                 `calling_line_dict_id`: line id containing the optional account of the cell
                                 `column_group_id`: the column group id of the cell
                                 `expression_label`: the expression label of the cell
        """
        report = self.env['account.report'].browse(options['report_id'])
        column_values = next(
            (column for column in options['columns'] if (
                column['column_group_key'] == params.get('column_group_key')
                and column['expression_label'] == params.get('expression_label')
            )),
            None
        )
        if not column_values:
            return

        column_date_from = fields.Date.to_date(column_values['date_from'])
        column_date_to = fields.Date.to_date(column_values['date_to'])
        report_date_from = fields.Date.to_date(options['date']['date_from'])
        report_date_to = fields.Date.to_date(options['date']['date_to'])

        # Corrections for comparisons
        if column_values['expression_label'] in ('not_started', 'later'):
            # Not Started and Later period start one day after `report_date_to`
            column_date_from = report_date_to + relativedelta(days=1)
        if column_values['expression_label'] == 'before':
            # Before period ends one day before `report_date_from`
            column_date_to = report_date_from - relativedelta(days=1)

        # calling_line_dict_id is of the format `~account.report~15|~account.account~25`
        model, account_id = report._get_model_info_from_id(params.get('calling_line_dict_id'))
        if model != 'account.account':
            account_id = None

        # Find the original lines to be deferred in the report period
        original_move_lines_domain = self._get_domain(
            report, options, filter_not_started=column_values['expression_label'] == 'not_started'
        )
        if account_id:
            # We're auditing a specific account, so we only want moves containing this account
            original_move_lines_domain.append(('account_id', '=', account_id))
        # We're getting all lines from the concerned moves. They are filtered later for flexibility.
        original_move = self.env['account.move.line'].search(original_move_lines_domain).move_id

        # For the Total period only show the original move lines
        line_ids = original_move.line_ids.ids

        # Show both the original move lines and deferral move lines for all other periods
        if not column_values['expression_label'] == 'total':
            line_ids += original_move.deferred_move_ids.line_ids.ids

        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entries'),
            'res_model': 'account.move.line',
            'domain': [('id', 'in', line_ids)],
            'views': [(False, 'list'), (False, 'form'), (False, 'pivot'), (False, 'graph'), (False, 'kanban')],
            # Most filters are set here to allow auditing flexibility to the user
            'context': {
                'search_default_pl_accounts': True,
                'search_default_account_id': account_id,
                'date_from': column_date_from,
                'date_to': column_date_to,
                'search_default_date_between': True,
                'expand': True,
            }
        }

    def _caret_options_initializer(self):
        return {
            'deferred_caret': [
                {'name': _("Journal Items"), 'action': 'open_journal_items'},
            ],
        }

    def open_journal_items(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        action = report.open_journal_items(options=options, params=params)
        action.get('context', {}).pop('search_default_date_between', None)
        action['domain'] = action.get('domain', []) + self._get_domain(report, options)
        return action

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        def get_columns(totals):
            return [
                {
                    **report._build_column_dict(
                        totals[(
                            fields.Date.to_date(column['date_from']),
                            fields.Date.to_date(column['date_to']),
                            column['expression_label']
                        )],
                        column,
                        options=options,
                        currency=self.env.company.currency_id,
                    ),
                    'auditable': True,
                }
                for column in options['columns']
            ]

        if warnings is not None:
            already_generated = (
                (
                    self._get_deferred_report_type() == 'expense' and self.env.company.generate_deferred_expense_entries_method == 'manual'
                    or self._get_deferred_report_type() == 'revenue' and self.env.company.generate_deferred_revenue_entries_method == 'manual'
                )
                and self.env['account.move'].search_count(
                    report._get_generated_deferral_entries_domain(options)
                )
            )
            if already_generated:
                warnings['account_reports.deferred_report_warning_already_posted'] = {'alert_type': 'warning'}

        lines = self._get_lines(report, options)
        periods = [
            (
                fields.Date.from_string(column['date_from']),
                fields.Date.from_string(column['date_to']),
                column['expression_label'],
            )
            for column in options['columns']
        ]
        deferred_amounts_by_line = self.env['account.move']._get_deferred_amounts_by_line(lines, periods)
        totals_per_account, totals_all_accounts = self._group_deferred_amounts_by_account(deferred_amounts_by_line, periods, self._get_deferred_report_type() == 'expense')

        report_lines = []

        for totals_account in totals_per_account.values():
            account = self.env['account.account'].browse(totals_account['account_id'])
            report_lines.append((0, {
                'id': report._get_generic_line_id('account.account', account.id),
                'name': f"{account.code} {account.name}",
                'caret_options': 'deferred_caret',
                'level': 1,
                'columns': get_columns(totals_account),
            }))
        if totals_per_account:
            report_lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total'),
                'name': 'Total',
                'level': 1,
                'columns': get_columns(totals_all_accounts),
            }))

        return report_lines

    #######################
    # DEFERRED GENERATION #
    #######################

    def action_generate_entry(self, options):
        new_deferred_moves = self._generate_deferral_entry(options)
        return {
            'name': _('Deferred Entries'),
            'type': 'ir.actions.act_window',
            'views': [(False, "tree"), (False, "form")],
            'domain': [('id', 'in', new_deferred_moves.ids)],
            'res_model': 'account.move',
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            },
            'target': 'current',
        }

    def _generate_deferral_entry(self, options):
        journal = self.env.company.deferred_journal_id
        if not journal:
            raise UserError(_("Please set the deferred journal in the accounting settings."))
        date_from = fields.Date.to_date(DEFERRED_DATE_MIN)
        date_to = fields.Date.from_string(options['date']['date_to'])
        if date_to.day != calendar.monthrange(date_to.year, date_to.month)[1]:
            raise UserError(_("You cannot generate entries for a period that does not end at the end of the month."))
        if self.env.company._get_violated_lock_dates(date_to, False):
            raise UserError(_("You cannot generate entries for a period that is locked."))
        options['all_entries'] = False  # We only want to create deferrals for posted moves
        report = self.env["account.report"].browse(options["report_id"])
        self.env['account.move.line'].flush_model()
        lines = self._get_lines(report, options, filter_already_generated=True)
        deferral_entry_period = self.env['account.report']._get_dates_period(date_from, date_to, 'range', period_type='month')
        ref = _("Grouped Deferral Entry of %s", deferral_entry_period['string'])
        ref_rev = _("Reversal of Grouped Deferral Entry of %s", deferral_entry_period['string'])
        deferred_account = self.env.company.deferred_expense_account_id if self._get_deferred_report_type() == 'expense' else self.env.company.deferred_revenue_account_id
        move_lines, original_move_ids = self._get_deferred_lines(lines, deferred_account, (date_from, date_to, 'current'), self._get_deferred_report_type() == 'expense', ref)
        if not move_lines:
            raise UserError(_("No entry to generate."))

        deferred_move = self.env['account.move'].with_context(skip_account_deprecation_check=True).create({
            'move_type': 'entry',
            'deferred_original_move_ids': [Command.set(original_move_ids)],
            'journal_id': journal.id,
            'date': date_to,
            'auto_post': 'at_date',
            'ref': ref,
        })
        # We write the lines after creation, to make sure the `deferred_original_move_ids` is set.
        # This way we can avoid adding taxes for deferred moves.
        deferred_move.write({'line_ids': move_lines})
        reverse_move = deferred_move._reverse_moves()
        reverse_move.write({
            'date': deferred_move.date + relativedelta(days=1),
            'ref': ref_rev,
        })
        reverse_move.line_ids.name = ref_rev
        new_deferred_moves = deferred_move + reverse_move
        # We create the relation (original deferred move, deferral entry)
        # using SQL. This avoids a MemoryError using the ORM which will
        # load huge amounts of moves in memory for nothing
        self.env.cr.execute_values("""
            INSERT INTO account_move_deferred_rel(original_move_id, deferred_move_id)
                 VALUES %s
            ON CONFLICT DO NOTHING
        """, [
            (original_move_id, deferral_move.id)
            for original_move_id in original_move_ids
            for deferral_move in new_deferred_moves
        ])
        (deferred_move + reverse_move)._post(soft=True)
        return new_deferred_moves

    @api.model
    def _get_current_key_totals_dict(self, lines_per_key, sign):
        return {
            'account_id': lines_per_key[0]['account_id'],
            'amount_total': sign * sum(line['balance'] for line in lines_per_key),
            'move_ids': {line['move_id'] for line in lines_per_key},
        }

    @api.model
    def _get_deferred_lines(self, lines, deferred_account, period, is_reverse, ref):
        """
        Returns a list of Command objects to create the deferred lines of a single given period.
        And the move_ids of the original lines that created these deferred
        (to keep track of the original invoice in the deferred entries).
        """
        if not deferred_account:
            raise UserError(_("Please set the deferred accounts in the accounting settings."))
        deferred_amounts_by_line = self.env['account.move']._get_deferred_amounts_by_line(lines, [period])
        deferred_amounts_by_key, deferred_amounts_totals = self._group_deferred_amounts_by_account(deferred_amounts_by_line, [period], is_reverse, filter_already_generated=True)
        if deferred_amounts_totals['totals_aggregated'] == deferred_amounts_totals[period]:
            return [], set()

        # compute analytic distribution to populate on deferred lines
        # structure: {self._get_grouping_keys_deferred_lines(): [analytic distribution]}
        # dict of keys: self._get_grouping_keys_deferred_lines()
        #         values: dict of keys: "account.analytic.account.id" (string)
        #                         values: float
        anal_dist_by_key = defaultdict(lambda: defaultdict(float))
        # using another var for the analytic distribution of the deferral account
        deferred_anal_dist = defaultdict(lambda: defaultdict(float))
        for line in lines:
            if not line['analytic_distribution']:
                continue
            # Analytic distribution should be computed from the lines with the same _get_grouping_keys_deferred_lines(), except for
            # the deferred line with the deferral account which will use _get_grouping_keys_deferral_lines()
            full_ratio = (line['balance'] / deferred_amounts_totals['totals_aggregated']) if deferred_amounts_totals['totals_aggregated'] else 0
            key_amount = deferred_amounts_by_key.get(self._group_by_deferred_keys(line, True))
            key_ratio = (line['balance'] / key_amount['amount_total']) if key_amount and key_amount['amount_total'] else 0

            for account_id, distribution in line['analytic_distribution'].items():
                anal_dist_by_key[self._group_by_deferred_keys(line, True)][account_id] += distribution * key_ratio
                deferred_anal_dist[self._group_by_deferral_keys(line)][account_id] += distribution * full_ratio

        remaining_balance = 0
        deferred_lines = []
        original_move_ids = set()
        for key, line in deferred_amounts_by_key.items():
            for balance in (-line['amount_total'], line[period]):
                if balance != 0 and line[period] != line['amount_total']:
                    original_move_ids |= line['move_ids']
                    deferred_balance = self.env.company.currency_id.round((1 if is_reverse else -1) * balance)
                    deferred_lines.append(
                        Command.create(
                            self.env['account.move.line']._get_deferred_lines_values(
                                account_id=line['account_id'],
                                balance=deferred_balance,
                                ref=ref,
                                analytic_distribution=anal_dist_by_key[key] or False,
                                line=line,
                            )
                        )
                    )
                    remaining_balance += deferred_balance

        grouped_by_key = {
            key: list(value)
            for key, value in groupby(
                deferred_amounts_by_key.values(),
                key=self._group_by_deferral_keys,
            )
        }
        deferral_lines = []
        for key, lines_per_key in grouped_by_key.items():
            balance = 0
            for line in lines_per_key:
                if line[period] != line['amount_total']:
                    balance += self.env.company.currency_id.round((1 if is_reverse else -1) * (line['amount_total'] - line[period]))
            deferral_lines.append(
                Command.create(
                    self.env['account.move.line']._get_deferred_lines_values(
                        account_id=deferred_account.id,
                        balance=balance,
                        ref=ref,
                        analytic_distribution=deferred_anal_dist[key] or False,
                        line=lines_per_key[0],
                    )
                )
            )
            remaining_balance += balance

        if not self.env.company.currency_id.is_zero(remaining_balance):
            deferral_lines.append(
                Command.create({
                    'account_id': deferred_account.id,
                    'balance': -remaining_balance,
                    'name': ref,
                })
            )
        return deferred_lines + deferral_lines, original_move_ids


class DeferredExpenseCustomHandler(models.AbstractModel):
    _name = 'account.deferred.expense.report.handler'
    _inherit = 'account.deferred.report.handler'
    _description = 'Deferred Expense Custom Handler'

    def _get_deferred_report_type(self):
        return 'expense'


class DeferredRevenueCustomHandler(models.AbstractModel):
    _name = 'account.deferred.revenue.report.handler'
    _inherit = 'account.deferred.report.handler'
    _description = 'Deferred Revenue Custom Handler'

    def _get_deferred_report_type(self):
        return 'revenue'
