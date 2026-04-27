# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import models, fields, _, api, Command
from odoo.exceptions import UserError
from odoo.tools import groupby, SQL
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

    def _get_domain_fully_inside_period(self, options):
        return [  # Exclude if entirely inside the period
            '!', '&', '&', '&', '&', '&', '&', '&',
                ('deferred_start_date', '!=', False),
                ('deferred_end_date', '!=', False),
                ('deferred_start_date', '>=', options['date']['date_from']),
                ('deferred_start_date', '<=', options['date']['date_to']),
                ('deferred_end_date', '>=', options['date']['date_from']),
                ('deferred_end_date', '<=', options['date']['date_to']),
                ('move_id.date', '>=', options['date']['date_from']),
                ('move_id.date', '<=', options['date']['date_to']),
        ]

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
        domain += self._get_domain_fully_inside_period(options)
        if filter_already_generated:
            # Avoid regenerating already generated deferrals
            domain += [
            ('deferred_end_date', '>=', options['date']['date_from']),
            '!',
                ('move_id.deferred_move_ids', 'any', [
                    ('date', '=', options['date']['date_to']),
                    '|',
                        ('state', '=', 'posted'),  # Either posted
                        '&',  # Or autoposted in the future
                            ('auto_post', '=', 'at_date'),
                            ('date', '>=', fields.Date.context_today(self)),
                ])
        ]
        if filter_not_started:
            domain += [('deferred_start_date', '>', options['date']['date_to'])]
        return domain

    @api.model
    def _get_select(self, options):
        account_name = self.env['account.account']._field_to_sql('account_move_line__account_id', 'name')
        return [
            SQL("account_move_line.id AS line_id"),
            SQL("account_move_line.account_id AS account_id"),
            SQL("account_move_line.partner_id AS partner_id"),
            SQL("account_move_line.product_id AS product_id"),
            SQL("account_move_line__product_template_id.categ_id AS product_category_id"),
            SQL("account_move_line.name AS line_name"),
            SQL("account_move_line.deferred_start_date AS deferred_start_date"),
            SQL("account_move_line.deferred_end_date AS deferred_end_date"),
            SQL("account_move_line.deferred_end_date - account_move_line.deferred_start_date AS diff_days"),
            SQL("account_move_line.balance AS balance"),
            SQL("account_move_line.analytic_distribution AS analytic_distribution"),
            SQL("account_move_line__move_id.id as move_id"),
            SQL("account_move_line__move_id.name AS move_name"),
            SQL("""
                NOT (
                    account_move_line.deferred_end_date >= %(report_date_from)s
                    AND
                    NOT EXISTS (
                         SELECT 1 
                           FROM account_move_deferred_rel AS amdr
                      LEFT JOIN account_move AS am ON amdr.deferred_move_id = am.id
                          WHERE amdr.original_move_id = account_move_line.move_id
                            AND am.date = %(report_date_to)s
                            AND (
                                 am.state = 'posted' 
                                 OR (am.auto_post = 'at_date' AND am.date >= %(today)s)
                                )
                    )
                ) AS is_already_generated
            """,
                report_date_from=options['date']['date_from'],
                report_date_to=options['date']['date_to'],
                today=fields.Date.context_today(self),
            ),
            SQL("%s AS account_name", account_name),
        ]

    def _get_lines(self, report, options, filter_already_generated=False):
        if 'report_deferred_lines' not in self.env.cr.cache:
            self._fetch_lines(report, options, filter_already_generated)

        if not filter_already_generated:
            # No more filtering needed, we can reuse the cached result
            return self.env.cr.cache['report_deferred_lines'].values()
        else:
            # Filter the cached result to only keep the lines that are not already generated
            cached_lines = self.env.cr.cache['report_deferred_lines'].values()
            return [cached_line for cached_line in cached_lines if not cached_line['is_already_generated']]

    def _fetch_lines(self, report, options, filter_already_generated):
        """Fetch the lines that need to be deferred from the DB and store them in the cache for later reuse"""
        domain = self._get_domain(report, options, filter_already_generated)
        query = report._get_report_query(options, domain=domain, date_scope='from_beginning')
        select_clause = SQL(', ').join(self._get_select(options))

        query = SQL(
            """
            SELECT %(select_clause)s
            FROM %(table_references)s
            LEFT JOIN product_product AS account_move_line__product_id ON account_move_line.product_id = account_move_line__product_id.id
        LEFT JOIN product_template AS account_move_line__product_template_id ON account_move_line__product_id.product_tmpl_id = account_move_line__product_template_id.id
        WHERE %(search_condition)s
            ORDER BY account_move_line.deferred_start_date, account_move_line.id
            """,
            select_clause=select_clause,
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )

        self.env.cr.execute(query)
        # Cache the result so that it can be reused to check whether a warning banner should be shown
        # only if it's the generic query (so without filtering already generated deferrals)
        self.env.cr.cache['report_deferred_lines'] = {
            r['line_id']: r for r in self.env.cr.dictfetchall()
        }

    @api.model
    def _get_grouping_fields_deferred_lines(self, filter_already_generated=False, grouping_field='account_id'):
        return (grouping_field,)

    @api.model
    def _group_by_deferred_fields(self, line, filter_already_generated=False, grouping_field='account_id'):
        return tuple(line[k] for k in self._get_grouping_fields_deferred_lines(filter_already_generated, grouping_field))

    @api.model
    def _get_grouping_fields_deferral_lines(self):
        return ()

    @api.model
    def _group_by_deferral_fields(self, line):
        return tuple(line[k] for k in self._get_grouping_fields_deferral_lines())

    @api.model
    def _group_deferred_amounts_by_grouping_field(self, deferred_amounts_by_line, periods, is_reverse, filter_already_generated=False, grouping_field='account_id'):
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
        deferred_amounts_by_line = groupby(deferred_amounts_by_line, key=lambda x: self._group_by_deferred_fields(x, filter_already_generated, grouping_field))
        totals_per_key = {}  # {key: {**self._get_grouping_fields_deferral_lines(), total, before, current, later}}
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

    def _custom_options_initializer(self, report, options, previous_options):
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
            'date_to': fields.Date.to_string(fields.Date.to_date(options['columns'][0]['date_from']) - relativedelta(days=1)),
        }]
        later_column = [{
            **options['columns'][0],
            'name': _('Later'),
            'expression_label': 'later',
            'date_from': fields.Date.to_string(fields.Date.to_date(options['columns'][-1]['date_to']) + relativedelta(days=1)),
            'date_to': DEFERRED_DATE_MAX,
        }]
        options['columns'] = total_column + not_started_column + before_column + options['columns'] + later_column
        options['column_headers'] = []
        options['deferred_report_type'] = self._get_deferred_report_type()
        options['deferred_grouping_field'] = previous_options.get('deferred_grouping_field') or 'account_id'
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
        _grouping_model, grouping_record_id = report._get_model_info_from_id(params.get('calling_line_dict_id'))

        # Find the original lines to be deferred in the report period
        original_move_lines_domain = self._get_domain(
            report, options, filter_not_started=column_values['expression_label'] == 'not_started'
        )
        if grouping_record_id:
            # We're auditing a specific account, so we only want moves containing this account
            original_move_lines_domain.append((options['deferred_grouping_field'], '=', grouping_record_id))
        # We're getting all lines from the concerned moves. They are filtered later for flexibility.
        original_moves = self.env['account.move.line'].search(original_move_lines_domain).move_id

        domain = [
            # For the Total period only show the original move lines
            '&',
                ('move_id', 'in', original_moves.ids),
                ('deferred_end_date', '>=', report_date_from),
        ]

        # Show both the original move lines and deferral move lines for all other periods
        if column_values['expression_label'] != 'total' and original_moves.deferred_move_ids:
            domain = ['|'] + [('move_id', 'in', original_moves.deferred_move_ids.ids)] + domain

        if column_values['expression_label'] == 'not_started':
            domain += [('deferred_start_date', '>=', column_date_from)]
        else:
            # If in manually & grouped mode, and deferrals have not yet been generated
            # so no move with `date` set => instead show the candidates original deferred moves that
            # will be deferred upon clicking the button. If totally/partially generated, we'll just
            # use the `date` filter which will include both the originals and deferrals.
            if not original_moves.deferred_move_ids:
                domain += [
                    ('deferred_start_date', '<=', column_date_to),
                    ('deferred_end_date', '>=', column_date_from),
                ]
            else:
                domain += [
                    ('date', '>=', column_date_from),
                    ('date', '<=', column_date_to),
                ]
        domain += self._get_domain_fully_inside_period(options)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entries'),
            'res_model': 'account.move.line',
            'domain': domain,
            'views': [(self.env.ref('account_accountant.view_deferred_entries_tree').id, 'list'), (False, 'pivot'), (False, 'graph'), (False, 'kanban')],
            # Most filters are set here to allow auditing flexibility to the user
            'context': {
                'search_default_pl_accounts': True,
                f'search_default_{options["deferred_grouping_field"]}': grouping_record_id,
                'expand': True,
            },
        }

    def _caret_options_initializer(self):
        return {
            'deferred_caret': [
                {'name': _("Journal Items"), 'action': 'open_journal_items'},
            ],
        }

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        if (
            self._get_deferred_report_type() == 'expense' and self.env.company.generate_deferred_expense_entries_method == 'manual'
            or self._get_deferred_report_type() == 'revenue' and self.env.company.generate_deferred_revenue_entries_method == 'manual'
        ):
            already_generated = self.env['account.move'].search_count(
                report._get_generated_deferral_entries_domain(options)
            )
            # This will trigger a second _get_lines call, however the first one was cached, so we just need to filter again on the cache (see _get_lines)
            moves_lines_to_generate, __, __, __, __ = self._get_moves_to_defer(options)
            if moves_lines_to_generate and already_generated:
                warnings['account_reports.deferred_report_warning_partially_generated'] = {'alert_type': 'warning'}
            elif moves_lines_to_generate:
                warnings['account_reports.deferred_report_warning_never_generated'] = {'alert_type': 'warning'}
            elif already_generated:
                warnings['account_reports.deferred_report_info_fully_generated'] = {'alert_type': 'info'}


    def open_journal_items(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        record_model, record_id = report._get_model_info_from_id(params.get('line_id'))
        domain = self._get_domain(report, options)
        if record_model == 'account.account' and record_id:
            domain += [('account_id', '=', record_id)]
        elif record_model == 'product.product' and record_id:
            domain += [('product_id', '=', record_id)]
        elif record_model == 'product.category' and record_id:
            domain += [('product_category_id', '=', record_id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _("Deferred Entries"),
            'res_model': 'account.move.line',
            'domain': domain,
            'views': [(self.env.ref('account_accountant.view_deferred_entries_tree').id, 'list')],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            }
        }

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

        lines = self._get_lines(report, options)
        periods = [
            (
                fields.Date.from_string(column['date_from']),
                fields.Date.from_string(column['date_to']),
                column['expression_label'],
            )
            for column in options['columns']
        ]
        deferred_amounts_by_line = self.env['account.move']._get_deferred_amounts_by_line(lines, periods, self._get_deferred_report_type())
        totals_per_grouping_field, totals_all_grouping_field = self._group_deferred_amounts_by_grouping_field(
            deferred_amounts_by_line=deferred_amounts_by_line,
            periods=periods,
            is_reverse=self._get_deferred_report_type() == 'expense',
            filter_already_generated=False,
            grouping_field=options['deferred_grouping_field'],
        )

        report_lines = []
        grouping_model = self.env['account.move.line'][options['deferred_grouping_field']]._name
        for totals_grouping_field in totals_per_grouping_field.values():
            grouping_record = self.env[grouping_model].browse(totals_grouping_field[options['deferred_grouping_field']])
            grouping_field_description = self.env['account.move.line'][options['deferred_grouping_field']]._description
            if options['deferred_grouping_field'] == 'product_id':
                grouping_field_description = _("Product")
            grouping_name = grouping_record.display_name or _("(No %s)", grouping_field_description)
            report_lines.append((0, {
                'id': report._get_generic_line_id(grouping_model, grouping_record.id),
                'name': grouping_name,
                'caret_options': 'deferred_caret',
                'level': 1,
                'columns': get_columns(totals_grouping_field),
            }))
        if totals_per_grouping_field:
            report_lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total'),
                'name': 'Total',
                'level': 1,
                'columns': get_columns(totals_all_grouping_field),
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
            'views': [(False, "list"), (False, "form")],
            'domain': [('id', 'in', new_deferred_moves.ids)],
            'res_model': 'account.move',
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            },
            'target': 'current',
        }

    def _get_moves_to_defer(self, options):
        date_from = fields.Date.to_date(DEFERRED_DATE_MIN)
        date_to = fields.Date.from_string(options['date']['date_to'])
        if date_to.day != calendar.monthrange(date_to.year, date_to.month)[1]:
            raise UserError(_("You cannot generate entries for a period that does not end at the end of the month."))
        options['all_entries'] = False  # We only want to create deferrals for posted moves
        report = self.env["account.report"].browse(options["report_id"])
        self.env['account.move.line'].flush_model()
        lines = self._get_lines(report, options, filter_already_generated=True)
        deferral_entry_period = self.env['account.report']._get_dates_period(date_from, date_to, 'range', period_type='month')
        ref = _("Grouped Deferral Entry of %s", deferral_entry_period['string'])
        ref_rev = _("Reversal of Grouped Deferral Entry of %s", deferral_entry_period['string'])
        deferred_account = self.env.company.deferred_expense_account_id if self._get_deferred_report_type() == 'expense' else self.env.company.deferred_revenue_account_id
        move_lines, original_move_ids = self._get_deferred_lines(lines, deferred_account, (date_from, date_to, 'current'), self._get_deferred_report_type() == 'expense', ref)
        return move_lines, original_move_ids, ref, ref_rev, date_to

    def _generate_deferral_entry(self, options):
        journal = self.env.company.deferred_expense_journal_id if self._get_deferred_report_type() == "expense" else self.env.company.deferred_revenue_journal_id
        if not journal:
            raise UserError(_("Please set the deferred journal in the accounting settings."))
        move_lines, original_move_ids, ref, ref_rev, date_to = self._get_moves_to_defer(options)
        if self.env.company._get_violated_lock_dates(date_to, False, journal):
            raise UserError(_("You cannot generate entries for a period that is locked."))
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
        new_deferred_moves.invalidate_recordset()
        new_deferred_moves._post(soft=True)
        return new_deferred_moves

    @api.model
    def _get_current_key_totals_dict(self, lines_per_key, sign):
        return {
            'account_id': lines_per_key[0]['account_id'],
            'product_id': lines_per_key[0]['product_id'],
            'product_category_id': lines_per_key[0]['product_category_id'],
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

        deferred_amounts_by_line = self.env['account.move']._get_deferred_amounts_by_line(lines, [period], is_reverse)
        deferred_amounts_by_key, deferred_amounts_totals = self._group_deferred_amounts_by_grouping_field(deferred_amounts_by_line, [period], is_reverse, filter_already_generated=True)
        totals_aggregated = deferred_amounts_totals['totals_aggregated']
        if totals_aggregated == deferred_amounts_totals[period]:
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
            # the deferred line with the deferral account which will use _get_grouping_fields_deferral_lines()
            sign = 1 if is_reverse else -1
            key_amount = deferred_amounts_by_key.get(self._group_by_deferred_fields(line, True))
            total_amount = key_amount.get('amount_total')
            key_ratio = sign * line['balance'] / total_amount if total_amount else 0
            full_ratio = sign * line['balance'] / totals_aggregated if totals_aggregated else 0

            for account_id, distribution in line['analytic_distribution'].items():
                anal_dist_by_key[self._group_by_deferred_fields(line, True)][account_id] += distribution * key_ratio
                deferred_anal_dist[self._group_by_deferral_fields(line)][account_id] += distribution * full_ratio

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
                key=self._group_by_deferral_fields,
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
