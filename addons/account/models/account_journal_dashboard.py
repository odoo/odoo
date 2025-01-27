import ast
from babel.dates import format_datetime, format_date
from collections import defaultdict
from datetime import datetime, timedelta
import base64
import json
import random

from odoo import models, api, _, fields, Command, tools
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, SQL
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang


def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res


class account_journal(models.Model):
    _inherit = "account.journal"

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    json_activity_data = fields.Text(compute='_get_json_activity_data')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', help="Whether this journal should be displayed on the dashboard or not", default=True)
    color = fields.Integer("Color Index", default=0)
    current_statement_balance = fields.Monetary(compute='_compute_current_statement_balance') # technical field used to avoid computing the value multiple times
    has_statement_lines = fields.Boolean(compute='_compute_current_statement_balance') # technical field used to avoid computing the value multiple times
    entries_count = fields.Integer(compute='_compute_entries_count')
    has_posted_entries = fields.Boolean(compute='_compute_has_entries')
    has_entries = fields.Boolean(compute='_compute_has_entries')
    has_sequence_holes = fields.Boolean(compute='_compute_has_sequence_holes')
    has_unhashed_entries = fields.Boolean(string='Unhashed Entries', compute='_compute_has_unhashed_entries')
    last_statement_id = fields.Many2one(comodel_name='account.bank.statement', compute='_compute_last_bank_statement')

    def _compute_current_statement_balance(self):
        query_result = self._get_journal_dashboard_bank_running_balance()
        for journal in self:
            journal.has_statement_lines, journal.current_statement_balance = query_result.get(journal.id)

    def _compute_last_bank_statement(self):
        self.env.cr.execute("""
            SELECT journal.id, statement.id
              FROM account_journal journal
         LEFT JOIN LATERAL (
                      SELECT id, company_id
                        FROM account_bank_statement
                       WHERE journal_id = journal.id
                    ORDER BY first_line_index DESC
                       LIMIT 1
                   ) statement ON TRUE
             WHERE journal.id = ANY(%s)
               AND statement.company_id = ANY(%s)
        """, [self.ids, self.env.companies.ids])
        last_statements = {journal_id: statement_id for journal_id, statement_id in self.env.cr.fetchall()}
        for journal in self:
            journal.last_statement_id = self.env['account.bank.statement'].browse(last_statements.get(journal.id))

    def _kanban_dashboard(self):
        dashboard_data = self._get_journal_dashboard_data_batched()
        for journal in self:
            journal.kanban_dashboard = json.dumps(dashboard_data[journal.id])

    @api.depends('current_statement_balance')
    def _kanban_dashboard_graph(self):
        bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash', 'credit'))
        bank_cash_graph_datas = bank_cash_journals._get_bank_cash_graph_data()
        for journal in bank_cash_journals:
            journal.kanban_dashboard_graph = json.dumps(bank_cash_graph_datas[journal.id])

        sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        sale_purchase_graph_datas = sale_purchase_journals._get_sale_purchase_graph_data()
        for journal in sale_purchase_journals:
            journal.kanban_dashboard_graph = json.dumps(sale_purchase_graph_datas[journal.id])

        (self - bank_cash_journals - sale_purchase_journals).kanban_dashboard_graph = False

    def _get_json_activity_data(self):
        today = fields.Date.context_today(self)
        activities = defaultdict(list)
        # search activity on move on the journal
        act_type_name = self.env['mail.activity.type']._field_to_sql('act_type', 'name')
        sql_query = SQL(
            """
         SELECT activity.id,
                activity.res_id,
                activity.res_model,
                activity.summary,
      CASE WHEN activity.date_deadline < %(today)s THEN 'late' ELSE 'future' END as status,
                %(act_type_name)s as act_type_name,
                act_type.category as activity_category,
                activity.date_deadline,
                move.journal_id
           FROM account_move move
           JOIN mail_activity activity ON activity.res_id = move.id AND activity.res_model = 'account.move'
      LEFT JOIN mail_activity_type act_type ON activity.activity_type_id = act_type.id
          WHERE move.journal_id = ANY(%(ids)s)
            AND move.company_id = ANY(%(company_ids)s)

      UNION ALL

         SELECT activity.id,
                activity.res_id,
                activity.res_model,
                activity.summary,
      CASE WHEN activity.date_deadline < %(today)s THEN 'late' ELSE 'future' END as status,
                %(act_type_name)s as act_type_name,
                act_type.category as activity_category,
                activity.date_deadline,
                journal.id as journal_id
           FROM account_journal journal
           JOIN mail_activity activity ON activity.res_id = journal.id AND activity.res_model = 'account.journal'
      LEFT JOIN mail_activity_type act_type ON activity.activity_type_id = act_type.id
          WHERE journal.id = ANY(%(ids)s)
            AND journal.company_id = ANY(%(company_ids)s)
            """,
            today=today,
            act_type_name=act_type_name,
            ids=self.ids,
            company_ids=self.env.companies.ids,
        )
        self.env.cr.execute(sql_query)
        for activity in self.env.cr.dictfetchall():
            act = {
                'id': activity['id'],
                'res_id': activity['res_id'],
                'res_model': activity['res_model'],
                'status': activity['status'],
                'name': activity['summary'] or activity['act_type_name'],
                'activity_category': activity['activity_category'],
                'date': odoo_format_date(self.env, activity['date_deadline'])
            }

            activities[activity['journal_id']].append(act)
        for journal in self:
            journal.json_activity_data = json.dumps({'activities': activities[journal.id]})

    def _query_has_sequence_holes(self):
        self.env['account.move'].flush_model(['journal_id', 'date', 'sequence_prefix', 'made_sequence_gap'])
        queries = []
        for company in self.env.companies:
            company = company.with_context(ignore_exceptions=True)
            queries.append(SQL(
                """
                    SELECT move.journal_id,
                           move.sequence_prefix
                      FROM account_move move
                      JOIN account_journal journal ON move.journal_id = journal.id
                     WHERE move.journal_id = ANY(%(journal_ids)s)
                       AND move.company_id = %(company_id)s
                       AND move.made_sequence_gap = TRUE
                       AND move.date > %(fiscal_lock_date)s
                       AND (journal.type <> 'sale' OR move.date > %(sale_lock_date)s)
                       AND (journal.type <> 'purchase' OR move.date > %(purchase_lock_date)s)
                  GROUP BY move.journal_id, move.sequence_prefix
                """,
                journal_ids=self.ids,
                company_id=company.id,
                fiscal_lock_date=max(company.user_fiscalyear_lock_date, company.user_hard_lock_date),
                sale_lock_date=company.user_sale_lock_date,
                purchase_lock_date=company.user_purchase_lock_date,
            ))
        self.env.cr.execute(SQL(' UNION ALL '.join(['%s'] * len(queries)), *queries))
        return self.env.cr.fetchall()

    def _get_moves_to_hash(self, include_pre_last_hash, early_stop):
        """
        If we have INV/1, INV/2 not hashed, then INV/3, INV/4 hashed, then INV/5 and INV/6 not hashed
        :param include_pre_last_hash: if True, this will include INV/1 and INV/2. Otherwise not.
        :param early_stop: if True, stop searching when we found at least one record
        :return:
        """
        return self.env['account.move'].search([
            ('restrict_mode_hash_table', '=', True),
            ('inalterable_hash', '=', False),
            ('journal_id', '=', self.id),
            ('date', '>', self.company_id._get_user_fiscal_lock_date(self)),
        ])._get_chains_to_hash(force_hash=True, raise_if_gap=False, raise_if_no_document=False, early_stop=early_stop, include_pre_last_hash=include_pre_last_hash)

    def _compute_has_sequence_holes(self):
        has_sequence_holes = set(journal_id for journal_id, _prefix in self._query_has_sequence_holes())
        for journal in self:
            journal.has_sequence_holes = journal.id in has_sequence_holes

    def _compute_has_unhashed_entries(self):
        for journal in self:
            if journal.restrict_mode_hash_table:
                journal.has_unhashed_entries = journal._get_moves_to_hash(include_pre_last_hash=False, early_stop=True)
            else:
                journal.has_unhashed_entries = False

    def _compute_has_entries(self):
        sql_query = SQL(
            """
                       SELECT j.id,
                              has_posted_entries.val,
                              has_entries.val
                         FROM account_journal j
            LEFT JOIN LATERAL (
                                  SELECT bool(m.id) as val
                                    FROM account_move m
                                   WHERE m.journal_id = j.id
                                     AND m.state = 'posted'
                                   LIMIT 1
                              ) AS has_posted_entries ON true
            LEFT JOIN LATERAL (
                                  SELECT bool(m.id) as val
                                    FROM account_move m
                                   WHERE m.journal_id = j.id
                                   LIMIT 1
                              ) AS has_entries ON true
                        WHERE j.id in %(journal_ids)s
            """,
            journal_ids=tuple(self.ids),
        )
        self.env.cr.execute(sql_query)
        res = {journal_id: (has_posted, has_entries) for journal_id, has_posted, has_entries in self.env.cr.fetchall()}
        for journal in self:
            r = res.get(journal.id, (False, False))
            journal.has_posted_entries = bool(r[0])
            journal.has_entries = bool(r[1])

    def _compute_entries_count(self):
        res = {
            journal.id: count
            for journal, count in self.env['account.move']._read_group(
                domain=[
                    *self.env['account.move']._check_company_domain(self.env.companies),
                    ('journal_id', 'in', self.ids),
                ],
                groupby=['journal_id'],
                aggregates=['__count'],
            )
        }
        for journal in self:
            journal.entries_count = res.get(journal.id, 0)

    def _graph_title_and_key(self):
        if self.type in ['sale', 'purchase']:
            return ['', _('Residual amount')]
        elif self.type == 'cash':
            return ['', _('Cash: Balance')]
        elif self.type == 'bank':
            return ['', _('Bank: Balance')]
        elif self.type == 'credit':
            return ['', _('Credit Card: Balance')]

    def _get_bank_cash_graph_data(self):
        """Computes the data used to display the graph for bank and cash journals in the accounting dashboard"""
        def build_graph_data(date, amount, currency):
            #display date in locale format
            name = format_date(date, 'd LLLL Y', locale=locale)
            short_name = format_date(date, 'd MMM', locale=locale)
            return {'x': short_name, 'y': currency.round(amount), 'name': name}

        today = datetime.today()
        last_month = today + timedelta(days=-30)
        locale = get_lang(self.env).code

        query = """
            SELECT move.journal_id,
                   move.date,
                   SUM(st_line.amount) AS amount
              FROM account_bank_statement_line st_line
              JOIN account_move move ON move.id = st_line.move_id
             WHERE move.journal_id = ANY(%s)
               AND move.date > %s
               AND move.date <= %s
               AND move.company_id = ANY(%s)
          GROUP BY move.date, move.journal_id
          ORDER BY move.date DESC
        """
        self.env.cr.execute(query, (self.ids, last_month, today, self.env.companies.ids))
        query_result = group_by_journal(self.env.cr.dictfetchall())

        result = {}
        for journal in self:
            graph_title, graph_key = journal._graph_title_and_key()
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            journal_result = query_result[journal.id]

            color = '#875A7B' if 'e' in version else '#7c7bad'
            is_sample_data = not journal_result and not journal.has_statement_lines

            data = []
            if is_sample_data:
                for i in range(30, 0, -5):
                    current_date = today + timedelta(days=-i)
                    data.append(build_graph_data(current_date, random.randint(-5, 15), currency))
                    graph_key = _('Sample data')
            else:
                last_balance = journal.current_statement_balance
                data.append(build_graph_data(today, last_balance, currency))
                date = today
                amount = last_balance
                #then we subtract the total amount of bank statement lines per day to get the previous points
                #(graph is drawn backward)
                for val in journal_result:
                    date = val['date']
                    if date.strftime(DF) != today.strftime(DF):  # make sure the last point in the graph is today
                        data[:0] = [build_graph_data(date, amount, currency)]
                    amount -= val['amount']

                # make sure the graph starts 1 month ago
                if date.strftime(DF) != last_month.strftime(DF):
                    data[:0] = [build_graph_data(last_month, amount, currency)]

            result[journal.id] = [{'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color, 'is_sample_data': is_sample_data}]
        return result

    def _get_sale_purchase_graph_data(self):
        today = fields.Date.today()
        day_of_week = int(format_datetime(today, 'e', locale=get_lang(self.env).code))
        first_day_of_week = today + timedelta(days=-day_of_week+1)
        format_month = lambda d: format_date(d, 'MMM', locale=get_lang(self.env).code)

        self.env.cr.execute("""
            SELECT move.journal_id,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due < %(start_week1)s), 0) AS total_before,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week1)s AND invoice_date_due < %(start_week2)s), 0) AS total_week1,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week2)s AND invoice_date_due < %(start_week3)s), 0) AS total_week2,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week3)s AND invoice_date_due < %(start_week4)s), 0) AS total_week3,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week4)s AND invoice_date_due < %(start_week5)s), 0) AS total_week4,
                   COALESCE(SUM(move.amount_residual_signed) FILTER (WHERE invoice_date_due >= %(start_week5)s), 0) AS total_after
              FROM account_move move
             WHERE move.journal_id = ANY(%(journal_ids)s)
               AND move.state = 'posted'
               AND move.payment_state in ('not_paid', 'partial')
               AND move.move_type IN %(invoice_types)s
               AND move.company_id = ANY(%(company_ids)s)
          GROUP BY move.journal_id
        """, {
            'invoice_types': tuple(self.env['account.move'].get_invoice_types(True)),
            'journal_ids': self.ids,
            'company_ids': self.env.companies.ids,
            'start_week1': first_day_of_week + timedelta(days=-7),
            'start_week2': first_day_of_week + timedelta(days=0),
            'start_week3': first_day_of_week + timedelta(days=7),
            'start_week4': first_day_of_week + timedelta(days=14),
            'start_week5': first_day_of_week + timedelta(days=21),
        })
        query_results = {r['journal_id']: r for r in self.env.cr.dictfetchall()}
        result = {}
        for journal in self:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            graph_title, graph_key = journal._graph_title_and_key()
            sign = 1 if journal.type == 'sale' else -1
            journal_data = query_results.get(journal.id)
            data = []
            data.append({'label': _('Due'), 'type': 'past'})
            for i in range(-1, 3):
                if i == 0:
                    label = _('This Week')
                else:
                    start_week = first_day_of_week + timedelta(days=i*7)
                    end_week = start_week + timedelta(days=6)
                    if start_week.month == end_week.month:
                        label = f"{start_week.day} - {end_week.day} {format_month(end_week)}"
                    else:
                        label = f"{start_week.day} {format_month(start_week)} - {end_week.day} {format_month(end_week)}"
                data.append({'label': label, 'type': 'past' if i < 0 else 'future'})
            data.append({'label': _('Not Due'), 'type': 'future'})

            is_sample_data = not journal_data
            if not is_sample_data:
                data[0]['value'] = currency.round(sign * journal_data['total_before'])
                data[1]['value'] = currency.round(sign * journal_data['total_week1'])
                data[2]['value'] = currency.round(sign * journal_data['total_week2'])
                data[3]['value'] = currency.round(sign * journal_data['total_week3'])
                data[4]['value'] = currency.round(sign * journal_data['total_week4'])
                data[5]['value'] = currency.round(sign * journal_data['total_after'])
            else:
                for index in range(6):
                    data[index]['type'] = 'o_sample_data'
                    # we use unrealistic values for the sample data
                    data[index]['value'] = random.randint(0, 20)
                    graph_key = _('Sample data')

            result[journal.id] = [{'values': data, 'title': graph_title, 'key': graph_key, 'is_sample_data': is_sample_data}]
        return result

    def _get_journal_dashboard_data_batched(self):
        self.env['account.move'].flush_model()
        self.env['account.move.line'].flush_model()
        self.env['account.payment'].flush_model()
        dashboard_data = {}  # container that will be filled by functions below
        for journal in self:
            dashboard_data[journal.id] = {
                'currency_id': journal.currency_id.id or journal.company_id.sudo().currency_id.id,
                'show_company': len(self.env.companies) > 1 or journal.company_id.id != self.env.company.id,
            }
        self._fill_bank_cash_dashboard_data(dashboard_data)
        self._fill_sale_purchase_dashboard_data(dashboard_data)
        self._fill_general_dashboard_data(dashboard_data)
        self._fill_onboarding_data(dashboard_data)
        return dashboard_data

    def _fill_dashboard_data_count(self, dashboard_data, model, name, domain):
        """Populate the dashboard data with the result of a count.

        :param dashboard_data: a mapping between a journal ids and the data needed to display their
                               dashboard kanban card.
        :type dashboard_data: dict[int, dict]
        :param model: the model on which to perform the count
        :type model: str
        :param name: the name of the variable to inject in the dashboard's data
        :type name: str
        :param domain: the domain of records to count
        :type domain: list[tuple]
        """
        res = {
            journal.id: count
            for journal, count in self.env[model]._read_group(
                domain=[
                   *self.env[model]._check_company_domain(self.env.companies),
                   ('journal_id', 'in', self.ids),
               ] + domain,
                groupby=['journal_id'],
                aggregates=['__count'],
            )
        }
        for journal in self:
            dashboard_data[journal.id][name] = res.get(journal.id, 0)

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        """Populate all bank and cash journal's data dict with relevant information for the kanban card."""
        bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash', 'credit'))
        if not bank_cash_journals:
            return

        # Number to reconcile
        self._cr.execute("""
            SELECT st_line.journal_id,
                   COUNT(st_line.id)
              FROM account_bank_statement_line st_line
              JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
             WHERE st_line.journal_id IN %s
               AND st_line.company_id IN %s
               AND NOT st_line.is_reconciled
               AND st_line_move.checked IS TRUE
               AND st_line_move.state = 'posted'
          GROUP BY st_line.journal_id
        """, [tuple(bank_cash_journals.ids), tuple(self.env.companies.ids)])
        number_to_reconcile = {
            journal_id: count
            for journal_id, count in self.env.cr.fetchall()
        }

        # Last statement
        bank_cash_journals.last_statement_id.mapped(lambda s: s.balance_end_real)  # prefetch

        outstanding_pay_account_balances = bank_cash_journals._get_journal_dashboard_outstanding_payments()

        # Payment with method outstanding account == journal default account
        direct_payment_balances = bank_cash_journals._get_direct_bank_payments()

        # Misc Entries (journal items in the default_account not linked to bank.statement.line)
        misc_domain = []
        for journal in bank_cash_journals:
            date_limit = journal.last_statement_id.date or journal.company_id.fiscalyear_lock_date
            misc_domain.append(
                [('account_id', '=', journal.default_account_id.id), ('date', '>', date_limit)]
                if date_limit else
                [('account_id', '=', journal.default_account_id.id)]
            )
        misc_domain = [
            *self.env['account.move.line']._check_company_domain(self.env.companies),
            ('statement_line_id', '=', False),
            ('parent_state', '=', 'posted'),
            ('payment_id', '=', False),
      ] + expression.OR(misc_domain)

        misc_totals = {
            account: (balance, count_lines, currencies)
            for account, balance, count_lines, currencies in self.env['account.move.line']._read_group(
                domain=misc_domain,
                aggregates=['amount_currency:sum', 'id:count', 'currency_id:recordset'],
                groupby=['account_id'])
        }

        # To check
        to_check = {
            journal: (amount, count)
            for journal, amount, count in self.env['account.bank.statement.line']._read_group(
                domain=[
                    ('journal_id', 'in', bank_cash_journals.ids),
                    ('move_id.company_id', 'in', self.env.companies.ids),
                    ('move_id.checked', '=', False),
                    ('move_id.state', '=', 'posted'),
                ],
                groupby=['journal_id'],
                aggregates=['amount:sum', '__count'],
            )
        }

        for journal in bank_cash_journals:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            has_outstanding, outstanding_pay_account_balance = outstanding_pay_account_balances[journal.id]
            to_check_balance, number_to_check = to_check.get(journal, (0, 0))
            misc_balance, number_misc, misc_currencies = misc_totals.get(journal.default_account_id, (0, 0, currency))
            currency_consistent = misc_currencies == currency
            accessible = journal.company_id.id in journal.company_id._accessible_branches().ids
            nb_direct_payments, direct_payments_balance = direct_payment_balances[journal.id]
            drag_drop_settings = {
                'image': '/account/static/src/img/bank.svg' if journal.type in ('bank', 'credit') else '/web/static/img/rfq.svg',
                'text': _('Drop to import transactions'),
            }

            dashboard_data[journal.id].update({
                'number_to_check': number_to_check,
                'to_check_balance': currency.format(to_check_balance),
                'number_to_reconcile': number_to_reconcile.get(journal.id, 0),
                'account_balance': currency.format(journal.current_statement_balance + direct_payments_balance),
                'has_at_least_one_statement': bool(journal.last_statement_id),
                'nb_lines_bank_account_balance': (bool(journal.has_statement_lines) or bool(nb_direct_payments)) and accessible,
                'outstanding_pay_account_balance': currency.format(outstanding_pay_account_balance),
                'nb_lines_outstanding_pay_account_balance': has_outstanding,
                'last_balance': currency.format(journal.last_statement_id.balance_end_real),
                'last_statement_id': journal.last_statement_id.id,
                'bank_statements_source': journal.bank_statements_source,
                'is_sample_data': journal.has_statement_lines,
                'nb_misc_operations': number_misc,
                'misc_class': 'text-warning' if not currency_consistent else '',
                'misc_operations_balance': currency.format(misc_balance) if currency_consistent else None,
                'drag_drop_settings': drag_drop_settings,
            })

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        """Populate all sale and purchase journal's data dict with relevant information for the kanban card."""
        sale_purchase_journals = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        purchase_journals = self.filtered(lambda journal: journal.type == 'purchase')
        sale_journals = self.filtered(lambda journal: journal.type == 'sale')
        if not sale_purchase_journals:
            return
        bills_field_list = [
            "account_move.journal_id",
            "(CASE WHEN account_move.move_type IN ('out_refund', 'in_refund') THEN -1 ELSE 1 END) * account_move.amount_residual AS amount_total",
            "(CASE WHEN account_move.move_type IN ('in_invoice', 'in_refund', 'in_receipt') THEN -1 ELSE 1 END) * account_move.amount_residual_signed AS amount_total_company",
            "account_move.currency_id AS currency",
            "account_move.move_type",
            "account_move.invoice_date",
            "account_move.company_id",
        ]
        # DRAFTS
        query, params = sale_purchase_journals._get_draft_sales_purchases_query().select(*bills_field_list)
        self.env.cr.execute(query, params)
        query_results_drafts = group_by_journal(self.env.cr.dictfetchall())

        # WAITING AND LATE BILLS AND PAYMENTS
        query_results_to_pay = {}
        late_query_results = {}
        for journal_type, journals in [('sale', sale_journals), ('purchase', purchase_journals)]:
            if not journals:
                continue

            query, selects = journals._get_open_sale_purchase_query(journal_type)
            sql = SQL("""%s
                    GROUP BY account_move.company_id, account_move.journal_id, account_move.currency_id, late, to_pay""",
                      query.select(*selects),
            )
            self.env.cr.execute(sql)
            query_result = group_by_journal(self.env.cr.dictfetchall())
            for journal in journals:
                query_results_to_pay[journal.id] = [r for r in query_result[journal.id] if r['to_pay']]
                late_query_results[journal.id] = [r for r in query_result[journal.id] if r['late']]

        to_check_vals = {
            journal.id: (amount_total_signed_sum, count)
            for journal, amount_total_signed_sum, count in self.env['account.move']._read_group(
                domain=[
                    *self.env['account.move']._check_company_domain(self.env.companies),
                    ('journal_id', 'in', sale_purchase_journals.ids),
                    ('checked', '=', False),
                    ('state', '=', 'posted'),
                ],
                groupby=['journal_id'],
                aggregates=['amount_total_signed:sum', '__count'],
            )
        }

        self.env.cr.execute(SQL("""
            SELECT id, moves_exists
            FROM account_journal journal
            LEFT JOIN LATERAL (
                SELECT EXISTS(SELECT 1
                              FROM account_move move
                              WHERE move.journal_id = journal.id
                              AND move.company_id = ANY (%(companies_ids)s) AND
                                  move.journal_id = ANY (%(journal_ids)s)) AS moves_exists
            ) moves ON TRUE
            WHERE journal.id = ANY (%(journal_ids)s);
        """,
            journal_ids=sale_purchase_journals.ids,
            companies_ids=self.env.companies.ids,
        ))
        is_sample_data_by_journal_id = {row[0]: not row[1] for row in self.env.cr.fetchall()}

        for journal in sale_purchase_journals:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay[journal.id], currency)
            (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts[journal.id], currency)
            (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results[journal.id], currency)
            amount_total_signed_sum, count = to_check_vals.get(journal.id, (0, 0))
            if journal.type == 'purchase':
                title_has_sequence_holes = _("Irregularities due to draft, cancelled or deleted bills with a sequence number since last lock date.")
                drag_drop_settings = {
                    'image': '/account/static/src/img/Bill.svg',
                    'text': _('Drop and let the AI process your bills automatically.'),
                }
            else:
                title_has_sequence_holes = _("Irregularities due to draft, cancelled or deleted invoices with a sequence number since last lock date.")
                drag_drop_settings = {
                    'image': '/web/static/img/quotation.svg',
                    'text': _('Drop to import your invoices.'),
                }

            dashboard_data[journal.id].update({
                'number_to_check': count,
                'to_check_balance': currency.format(amount_total_signed_sum),
                'title': _('Bills to pay') if journal.type == 'purchase' else _('Invoices owed to you'),
                'number_draft': number_draft,
                'number_waiting': number_waiting,
                'number_late': number_late,
                'sum_draft': currency.format(sum_draft),  # sign is already handled by the SQL query
                'sum_waiting': currency.format(sum_waiting * (1 if journal.type == 'sale' else -1)),
                'sum_late': currency.format(sum_late * (1 if journal.type == 'sale' else -1)),
                'has_sequence_holes': journal.has_sequence_holes,
                'title_has_sequence_holes': title_has_sequence_holes,
                'has_unhashed_entries': journal.has_unhashed_entries,
                'is_sample_data': is_sample_data_by_journal_id[journal.id],
                'has_entries': not is_sample_data_by_journal_id[journal.id],
                'drag_drop_settings': drag_drop_settings,
            })

    def _fill_general_dashboard_data(self, dashboard_data):
        """Populate all miscelaneous journal's data dict with relevant information for the kanban card."""
        general_journals = self.filtered(lambda journal: journal.type == 'general')
        if not general_journals:
            return
        to_check_vals = {
            journal.id: (amount_total_signed_sum, count)
            for journal, amount_total_signed_sum, count in self.env['account.move']._read_group(
                domain=[
                    *self.env['account.move']._check_company_domain(self.env.companies),
                    ('journal_id', 'in', general_journals.ids),
                    ('checked', '=', False),
                    ('state', '=', 'posted'),
                ],
                groupby=['journal_id'],
                aggregates=['amount_total_signed:sum', '__count'],
            )
        }
        for journal in general_journals:
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            amount_total_signed_sum, count = to_check_vals.get(journal.id, (0, 0))
            drag_drop_settings = {
                'image': '/web/static/img/folder.svg',
                'text': _('Drop to create journal entries with attachments.'),
                'group': 'account.group_account_user',
            }

            dashboard_data[journal.id].update({
                'number_to_check': count,
                'to_check_balance': currency.format(amount_total_signed_sum),
                'drag_drop_settings': drag_drop_settings,
            })

    def _fill_onboarding_data(self, dashboard_data):
        """ Populate journals with onboarding data if they have no entries"""
        journal_onboarding_map = {
            'sale': 'account_invoice',
            'general': 'account_dashboard',
        }
        onboarding_data = defaultdict(dict)
        onboarding_progresses = self.env['onboarding.progress'].sudo().search([
            ('onboarding_id.route_name', 'in', [*journal_onboarding_map.values()]),
            ('company_id', 'in', self.company_id.ids),
        ])
        for progress in onboarding_progresses:
            ob = progress.onboarding_id
            ob_vals = ob.with_company(progress.company_id)._prepare_rendering_values()
            onboarding_data[progress.company_id][ob.route_name] = ob_vals
            onboarding_data[progress.company_id][ob.route_name]['current_onboarding_state'] = ob.current_onboarding_state
            onboarding_data[progress.company_id][ob.route_name]['steps'] = [
                {
                    'id': step.id,
                    'title': step.title,
                    'description': step.description,
                    'state': ob_vals['state'][step.id],
                    'action': step.panel_step_open_action_name,
                }
                for step in ob_vals['steps']
            ]
        for journal in self:
            dashboard_data[journal.id]['onboarding'] = onboarding_data[journal.company_id].get(journal_onboarding_map.get(journal.type))

    def _get_draft_sales_purchases_query(self):
        return self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('state', '=', 'draft'),
            ('move_type', 'in', self.env['account.move'].get_invoice_types(include_receipts=True)),
        ])

    def _get_open_sale_purchase_query(self, journal_type):
        assert journal_type in ('sale', 'purchase')
        query = self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('move_type', 'in', ('out_invoice', 'out_refund') if journal_type == 'sale' else ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
        ])
        selects = [
            SQL("journal_id"),
            SQL("company_id"),
            SQL("currency_id AS currency"),
            SQL("invoice_date_due < %s AS late", fields.Date.context_today(self)),
            SQL("SUM(amount_residual_signed) AS amount_total_company"),
            SQL("SUM((CASE WHEN move_type = 'in_invoice' THEN -1 ELSE 1 END) * amount_residual) AS amount_total"),
            SQL("COUNT(*)"),
            SQL("TRUE AS to_pay")
        ]

        return query, selects

    def _count_results_and_sum_amounts(self, results_dict, target_currency):
        """ Loops on a query result to count the total number of invoices and sum
        their amount_total field (expressed in the given target currency).
        amount_total must be signed!
        """
        if not results_dict:
            return 0, 0

        total_amount = 0
        count = 0
        company = self.env.company
        today = fields.Date.context_today(self)
        ResCurrency = self.env['res.currency']
        ResCompany = self.env['res.company']
        for result in results_dict:
            document_currency = ResCurrency.browse(result.get('currency'))
            document_company = ResCompany.browse(result.get('company_id')) or company
            date = result.get('invoice_date') or today
            count += result.get('count', 1)

            if document_company.currency_id == target_currency:
                total_amount += result.get('amount_total_company') or 0
            else:
                total_amount += document_currency._convert(result.get('amount_total'), target_currency, document_company, date)
        return count, target_currency.round(total_amount)

    def _get_journal_dashboard_bank_running_balance(self):
        # In order to not recompute everything from the start, we take the last
        # bank statement and only sum starting from there.
        self._cr.execute("""
            SELECT journal.id AS journal_id,
                   statement.id AS statement_id,
                   COALESCE(statement.balance_end_real, 0) AS balance_end_real,
                   without_statement.amount AS unlinked_amount,
                   without_statement.count AS unlinked_count
              FROM account_journal journal
         LEFT JOIN LATERAL (  -- select latest statement based on the date
                           SELECT id,
                                  first_line_index,
                                  balance_end_real
                             FROM account_bank_statement
                            WHERE journal_id = journal.id
                              AND company_id = ANY(%s)
                         ORDER BY date DESC, id DESC
                            LIMIT 1
                   ) statement ON TRUE
         LEFT JOIN LATERAL (  -- sum all the lines not linked to a statement with a higher index than the last line of the statement
                           SELECT COALESCE(SUM(stl.amount), 0.0) AS amount,
                                  COUNT(*)
                             FROM account_bank_statement_line stl
                             JOIN account_move move ON move.id = stl.move_id
                            WHERE stl.statement_id IS NULL
                              AND move.state != 'cancel'
                              AND stl.journal_id = journal.id
                              AND stl.company_id = ANY(%s)
                              AND stl.internal_index >= COALESCE(statement.first_line_index, '')
                            LIMIT 1
                   ) without_statement ON TRUE
             WHERE journal.id = ANY(%s)
        """, [self.env.companies.ids, self.env.companies.ids, self.ids])
        query_res = {res['journal_id']: res for res in self.env.cr.dictfetchall()}
        result = {}
        for journal in self:
            journal_vals = query_res[journal.id]
            result[journal.id] = (
                bool(journal_vals['statement_id'] or journal_vals['unlinked_count']),
                journal_vals['balance_end_real'] + journal_vals['unlinked_amount'],
            )
        return result

    def _get_direct_bank_payments(self):
        self.env.cr.execute("""
            SELECT move.journal_id AS journal_id,
                   move.company_id AS company_id,
                   move.currency_id AS currency,
                   SUM(CASE
                       WHEN payment.payment_type = 'outbound' THEN -payment.amount
                       ELSE payment.amount
                   END) AS amount_total,
                   SUM(amount_company_currency_signed) AS amount_total_company
              FROM account_payment payment
              JOIN account_move move ON move.origin_payment_id = payment.id
              JOIN account_journal journal ON move.journal_id = journal.id
             WHERE payment.is_matched IS TRUE
               AND move.state = 'posted'
               AND payment.journal_id = ANY(%s)
               AND payment.company_id = ANY(%s)
               AND payment.outstanding_account_id = journal.default_account_id
          GROUP BY move.company_id, move.journal_id, move.currency_id
        """, [self.ids, self.env.companies.ids])
        query_result = group_by_journal(self.env.cr.dictfetchall())
        result = {}
        for journal in self:
            # User may have read access on the journal but not on the company
            currency = (journal.currency_id or journal.company_id.sudo().currency_id).with_env(self.env)
            result[journal.id] = self._count_results_and_sum_amounts(query_result[journal.id], currency)
        return result

    def _get_journal_dashboard_outstanding_payments(self):
        self.env.cr.execute("""
            SELECT payment.journal_id AS journal_id,
                   payment.company_id AS company_id,
                   payment.currency_id AS currency,
                   SUM(CASE
                       WHEN payment.payment_type = 'outbound' THEN -payment.amount
                       ELSE payment.amount
                   END) AS amount_total,
                   SUM(amount_company_currency_signed) AS amount_total_company
              FROM account_payment payment
              JOIN account_move move ON move.origin_payment_id = payment.id
             WHERE (NOT payment.is_matched OR payment.is_matched IS NULL)
               AND move.state = 'posted'
               AND payment.journal_id = ANY(%s)
               AND payment.company_id = ANY(%s)
          GROUP BY payment.company_id, payment.journal_id, payment.currency_id
        """, [self.ids, self.env.companies.ids])
        query_result = group_by_journal(self.env.cr.dictfetchall())
        result = {}
        for journal in self:
            # User may have read access on the journal but not on the company
            currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
            result[journal.id] = self._count_results_and_sum_amounts(query_result[journal.id], currency)
        return result

    def _get_move_action_context(self):
        ctx = self._context.copy()
        journal = self
        if not ctx.get('default_journal_id'):
            ctx['default_journal_id'] = journal.id
        elif not journal:
            journal = self.browse(ctx['default_journal_id'])
        if journal.type == 'sale':
            ctx['default_move_type'] = 'out_refund' if ctx.get('refund') else 'out_invoice'
        elif journal.type == 'purchase':
            ctx['default_move_type'] = 'in_refund' if ctx.get('refund') else 'in_invoice'
        else:
            ctx['default_move_type'] = 'entry'
            ctx['view_no_maturity'] = True
        return ctx

    def action_create_new(self):
        return {
            'name': _('Create invoice/bill'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'context': self._get_move_action_context(),
        }

    def _build_no_journal_error_msg(self, company_name, journal_types):
        return _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company_name,
                journal_types=', '.join(journal_types),
            )

    def action_create_vendor_bill(self):
        """ This function is called by the "try our sample" button of Vendor Bills,
        visible on dashboard if no bill has been created yet.
        """
        context = dict(self._context)
        purchase_journal = self.browse(context.get('default_journal_id')) or self.search([('type', '=', 'purchase')], limit=1)
        if not purchase_journal:
            raise UserError(self._build_no_journal_error_msg(self.env.company.display_name, ['purchase']))
        context['default_move_type'] = 'in_invoice'
        invoice_date = fields.Date.today() - timedelta(days=12)
        partner = self.env['res.partner'].search([('name', '=', 'Deco Addict')], limit=1)
        company = purchase_journal.company_id
        if not partner:
            partner = self.env['res.partner'].create({
                'name': 'Deco Addict',
                'is_company': True,
            })
        ProductCategory = self.env['product.category'].with_company(company)
        default_expense_account = ProductCategory._fields['property_account_expense_categ_id'].get_company_dependent_fallback(ProductCategory)
        ref = 'DE%s' % invoice_date.strftime('%Y%m')
        bill = self.env['account.move'].with_context(default_extract_state='done').create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'ref': ref,
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date + timedelta(days=30),
            'journal_id': purchase_journal.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "[FURN_8999] Three-Seat Sofa",
                    'account_id': purchase_journal.default_account_id.id or default_expense_account.id,
                    'quantity': 5,
                    'price_unit': 1500,
                }),
                Command.create({
                    'name': "[FURN_8220] Four Person Desk",
                    'account_id': purchase_journal.default_account_id.id or default_expense_account.id,
                    'quantity': 5,
                    'price_unit': 2350,
                })
            ],
        })
        # In case of test environment, don't create the pdf
        if tools.config['test_enable'] or tools.config['test_file']:
            bill.with_context(no_new_invoice=True).message_post()
        else:
            addr = [x for x in [
                company.street,
                company.street2,
                ' '.join([x for x in [company.state_id.name, company.zip] if x]),
                company.country_id.name,
            ] if x]

            html = self.env['ir.qweb']._render('account.bill_preview', {
                'company_name': company.name,
                'company_street_address': addr,
                'invoice_name': 'Invoice ' + ref,
                'invoice_ref': ref,
                'invoice_date': invoice_date,
                'invoice_due_date': invoice_date + timedelta(days=30),
            })
            bodies = self.env['ir.actions.report']._prepare_html(html)[0]
            content = self.env['ir.actions.report']._run_wkhtmltopdf(bodies)
            attachment = self.env['ir.attachment'].create({
                'type': 'binary',
                'name': 'INV-%s-0001.pdf' % invoice_date.strftime('%Y-%m'),
                'res_model': 'mail.compose.message',
                'datas': base64.encodebytes(content),
            })
            bill.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
        return {
            'name': _('Bills'),
            'res_id': bill.id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'views': [[False, "form"]],
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def to_check_ids(self):
        self.ensure_one()
        return self.env['account.bank.statement.line'].search([
            ('journal_id', '=', self.id),
            ('move_id.company_id', 'in', self.env.companies.ids),
            ('move_id.checked', '=', False),
            ('move_id.state', '=', 'posted'),
        ])

    def _select_action_to_open(self):
        self.ensure_one()
        if self._context.get('action_name'):
            return self._context.get('action_name')
        elif self.type == 'bank':
            return 'action_bank_statement_tree'
        elif self.type == 'credit':
            return 'action_credit_statement_tree'
        elif self.type == 'cash':
            return 'action_view_bank_statement_tree'
        elif self.type == 'sale':
            return 'action_move_out_invoice_type'
        elif self.type == 'purchase':
            return 'action_move_in_invoice_type'
        else:
            return 'action_move_journal_line'

    def open_action(self):
        """return action based on type for related journals"""
        self.ensure_one()
        action_name = self._select_action_to_open()

        # Set 'account.' prefix if missing.
        if not action_name.startswith("account."):
            action_name = 'account.%s' % action_name

        action = self.env["ir.actions.act_window"]._for_xml_id(action_name)

        context = self._context.copy()
        if 'context' in action and isinstance(action['context'], str):
            context.update(ast.literal_eval(action['context']))
        else:
            context.update(action.get('context', {}))
        action['context'] = context
        action['context'].update({
            'default_journal_id': self.id,
        })
        domain_type_field = action['res_model'] == 'account.move.line' and 'move_id.move_type' or 'move_type' # The model can be either account.move or account.move.line

        # Override the domain only if the action was not explicitly specified in order to keep the
        # original action domain.
        if action.get('domain') and isinstance(action['domain'], str):
            action['domain'] = ast.literal_eval(action['domain'] or '[]')
        if not self._context.get('action_name'):
            if self.type == 'sale':
                action['domain'] = [(domain_type_field, 'in', ('out_invoice', 'out_refund', 'out_receipt'))]
            elif self.type == 'purchase':
                action['domain'] = [(domain_type_field, 'in', ('in_invoice', 'in_refund', 'in_receipt', 'entry'))]

        action['domain'] = (action['domain'] or []) + [('journal_id', '=', self.id)]
        return action

    def open_payments_action(self, payment_type=False, mode='list'):
        if payment_type == 'outbound':
            action_ref = 'account.action_account_payments_payable'
        elif payment_type == 'transfer':
            action_ref = 'account.action_account_payments_transfer'
        elif payment_type == 'inbound':
            action_ref = 'account.action_account_payments'
        else:
            action_ref = 'account.action_account_all_payments'
        action = self.env['ir.actions.act_window']._for_xml_id(action_ref)
        action['context'] = dict(ast.literal_eval(action.get('context')), default_journal_id=self.id, search_default_journal_id=self.id)
        if payment_type == 'transfer':
            action['context'].update({
                'default_partner_id': self.company_id.partner_id.id,
                'default_is_internal_transfer': True,
            })
        if mode == 'form':
            action['views'] = [[False, 'form']]
        return action

    def open_action_with_context(self):
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
            ctx['search_default_journal'] = False  # otherwise it will do a useless groupby in bank statements
        ctx.pop('group_by', None)
        action = self.env['ir.actions.act_window']._for_xml_id(f"account.{action_name}")
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = isinstance(ctx['use_domain'], list) and ctx['use_domain'] or ['|', ('journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] = _(
                "%(action)s for journal %(journal)s",
                action=action["name"],
                journal=self.name,
            )
        return action

    def open_bank_difference_action(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("account.action_account_moves_all_a")
        action['context'] = {
            'search_default_account_id': self.default_account_id.id,
            'search_default_group_by_move': False,
            'search_default_no_st_line_id': True,
            'search_default_posted': False,
        }
        date_from = self.last_statement_id.date or self.company_id.fiscalyear_lock_date
        if date_from:
            action['context'] |= {
                'date_from': date_from,
                'date_to': fields.Date.context_today(self),
                'search_default_date_between': True
            }
        return action

    def _show_sequence_holes(self, domain):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Entries"),
            'res_model': 'account.move',
            'search_view_id': (self.env.ref('account.view_account_move_with_gaps_in_sequence_filter').id, 'search'),
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'search_default_group_by_sequence_prefix': 1,
                'search_default_irregular_sequences': 1,
                'expand': 1,
            }
        }

    def show_sequence_holes(self):
        has_sequence_holes = self._query_has_sequence_holes()
        domain = expression.OR(
            [
                *self.env['account.move']._check_company_domain(self.env.companies),
                ('journal_id', '=', journal_id),
                ('sequence_prefix', '=', prefix),
            ]
            for journal_id, prefix in has_sequence_holes
        )
        action = self._show_sequence_holes(domain)
        action['context'] = {**self._get_move_action_context(), **action['context']}
        return action

    def show_unhashed_entries(self):
        self.ensure_one()
        chains_to_hash = self._get_moves_to_hash(include_pre_last_hash=True, early_stop=False)
        moves = self.env['account.move'].concat(*[chain_moves['moves'] for chain_moves in chains_to_hash])
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries to Hash'),
            'res_model': 'account.move',
            'domain': [('id', 'in', moves.ids)],
            'views': [(False, 'list'), (False, 'form')],
        }
        if len(moves.ids) == 1:
            action.update({
                'res_id': moves[0].id,
                'views': [(False, 'form')],
            })
        return action

    def create_bank_statement(self):
        """return action to create a bank statements. This button should be called only on journals with type =='bank'"""
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_bank_statement_tree")
        action.update({
            'views': [[False, 'form']],
            'context': "{'default_journal_id': " + str(self.id) + "}",
        })
        return action

    def create_customer_payment(self):
        """return action to create a customer payment"""
        return self.open_payments_action('inbound', mode='form')

    def create_supplier_payment(self):
        """return action to create a supplier payment"""
        return self.open_payments_action('outbound', mode='form')
