# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import copy
import json
import io
import logging
import lxml.html
import datetime
import ast
from collections import defaultdict
from math import copysign

from dateutil.relativedelta import relativedelta

from odoo.tools.misc import xlsxwriter
from odoo import models, fields, api, _
from odoo.tools import config, date_utils, get_lang
from odoo.osv import expression
from babel.dates import get_quarter_names, parse_date
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class AccountReportManager(models.Model):
    _name = 'account.report.manager'
    _description = 'Manage Summary and Footnotes of Reports'

    # must work with multi-company, in case of multi company, no company_id defined
    report_name = fields.Char(required=True, help='name of the model of the report')
    summary = fields.Char()
    footnotes_ids = fields.One2many('account.report.footnote', 'manager_id')
    company_id = fields.Many2one('res.company')
    financial_report_id = fields.Many2one('account.financial.html.report')

    def add_footnote(self, text, line):
        return self.env['account.report.footnote'].create({'line': line, 'text': text, 'manager_id': self.id})

class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Account Report Footnote'

    text = fields.Char()
    line = fields.Char(index=True)
    manager_id = fields.Many2one('account.report.manager')

class AccountReport(models.AbstractModel):
    _name = 'account.report'
    _description = 'Account Report'

    MAX_LINES = 80
    filter_multi_company = True
    filter_date = None
    filter_all_entries = None
    filter_comparison = None
    filter_journals = None
    filter_analytic = None
    filter_unfold_all = None
    filter_hierarchy = None
    filter_partner = None
    order_selected_column = None

    ####################################################
    # OPTIONS: multi_company
    ####################################################

    @api.model
    def _init_filter_multi_company(self, options, previous_options=None):
        if not self.filter_multi_company:
            return

        companies = self.env.user.company_ids
        if len(companies) > 1:
            allowed_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
            options['multi_company'] = [
                {'id': c.id, 'name': c.name, 'selected': c.id in allowed_company_ids} for c in companies
            ]

    @api.model
    def _get_options_companies(self, options):
        if not options.get('multi_company'):
            company = self.env.company
            return [{'id': company.id, 'name': company.name, 'selected': True}]

        all_companies = []
        companies = []
        for company_option in options['multi_company']:
            if company_option['selected']:
                companies.append(company_option)
            all_companies.append(company_option)
        return companies or all_companies

    @api.model
    def _get_options_companies_domain(self, options):
        if options.get('multi_company'):
            return [('company_id', 'in', [c['id'] for c in self._get_options_companies(options)])]
        else:
            return [('company_id', '=', self.env.company.id)]

    ####################################################
    # OPTIONS: journals
    ####################################################

    @api.model
    def _get_filter_journals(self):
        return self.env['account.journal'].search([
            ('company_id', 'in', self.env.user.company_ids.ids or [self.env.company.id])
        ], order="company_id, name")

    @api.model
    def _get_filter_journal_groups(self):
        journals = self._get_filter_journals()
        groups = self.env['account.journal.group'].search([], order='sequence')
        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if it doesn't exclude every journal
            if journals - journal_group.excluded_journal_ids:
                ret += journal_group
        return ret

    @api.model
    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return

        previous_company = False
        if previous_options and previous_options.get('journals'):
            journal_map = dict((opt['id'], opt['selected']) for opt in previous_options['journals'] if opt['id'] != 'divider' and 'selected' in opt)
        else:
            journal_map = {}
        options['journals'] = []

        group_header_displayed = False
        default_group_ids = []
        for group in self._get_filter_journal_groups():
            journal_ids = (self._get_filter_journals() - group.excluded_journal_ids).ids
            if len(journal_ids):
                if not group_header_displayed:
                    group_header_displayed = True
                    options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
                    default_group_ids = journal_ids
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': journal_ids})

        for j in self._get_filter_journals():
            if j.company_id != previous_company:
                options['journals'].append({'id': 'divider', 'name': j.company_id.name})
                previous_company = j.company_id
            options['journals'].append({
                'id': j.id,
                'name': j.name,
                'code': j.code,
                'type': j.type,
                'selected': journal_map.get(j.id, j.id in default_group_ids),
            })

    @api.model
    def _get_options_journals(self, options):
        return [
            journal for journal in options.get('journals', []) if
            not journal['id'] in ('divider', 'group') and journal['selected']
        ]

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    @api.model
    def _get_options_periods_list(self, options):
        ''' Get periods as a list of options, one per impacted period.
        The first element is the range of dates requested in the report, others are the comparisons.

        :param options: The report options.
        :return:        A list of options having size 1 + len(options['comparison']['periods']).
        '''
        periods_options_list = []
        if options.get('date'):
            periods_options_list.append(options)
        if options.get('comparison') and options['comparison'].get('periods'):
            for period in options['comparison']['periods']:
                period_options = options.copy()
                period_options['date'] = period
                periods_options_list.append(period_options)
        return periods_options_list

    @api.model
    def _get_dates_period(self, options, date_from, date_to, mode, period_type=None):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('As of %s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM YYYY')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if period_type == 'fiscalyear':
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(options, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode)
        if period_type in ('month', 'today', 'custom'):
            return self._get_dates_period(options, *date_utils.get_month(date_to), mode, period_type='month')
        if period_type == 'quarter':
            return self._get_dates_period(options, *date_utils.get_quarter(date_to), mode, period_type='quarter')
        if period_type == 'year':
            return self._get_dates_period(options, *date_utils.get_fiscal_year(date_to), mode, period_type='year')
        return None

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(options, date_from, date_to, mode, period_type=period_type)

    @api.model
    def _init_filter_date(self, options, previous_options=None):
        if self.filter_date is None:
            return

        # Default values.
        mode = self.filter_date.get('mode', 'range')
        options_filter = self.filter_date.get('filter') or ('today' if mode == 'single' else 'fiscalyear')
        date_from = self.filter_date.get('date_from') and fields.Date.from_string(self.filter_date['date_from'])
        date_to = self.filter_date.get('date_to') and fields.Date.from_string(self.filter_date['date_to'])
        # Handle previous_options.
        if previous_options and previous_options.get('date') and previous_options['date'].get('filter') \
                and not (previous_options['date']['filter'] == 'today' and mode == 'range'):

            options_filter = previous_options['date']['filter']
            if options_filter == 'custom':
                if previous_options['date']['date_from'] and mode == 'range':
                    date_from = fields.Date.from_string(previous_options['date']['date_from'])
                if previous_options['date']['date_to']:
                    date_to = fields.Date.from_string(previous_options['date']['date_to'])

        # Create date option for each company.
        period_type = False
        if 'today' in options_filter:
            date_to = fields.Date.context_today(self)
            date_from = date_utils.get_month(date_to)[0]
        elif 'month' in options_filter:
            date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
            period_type = 'month'
        elif 'quarter' in options_filter:
            date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
            period_type = 'quarter'
        elif 'year' in options_filter:
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
            date_from = company_fiscalyear_dates['date_from']
            date_to = company_fiscalyear_dates['date_to']
        elif not date_from:
            # options_filter == 'custom' && mode == 'single'
            date_from = date_utils.get_month(date_to)[0]

        options['date'] = self._get_dates_period(options, date_from, date_to, mode, period_type=period_type)
        if 'last' in options_filter:
            options['date'] = self._get_dates_previous_period(options, options['date'])
        options['date']['filter'] = options_filter

    @api.model
    def _init_filter_comparison(self, options, previous_options=None):
        if self.filter_comparison is None or not options.get('date'):
            return

        cmp_filter = self.filter_comparison and self.filter_comparison.get('filter', 'no_comparison')
        number_period = self.filter_comparison and self.filter_comparison.get('number_period', 1)
        date_from = self.filter_comparison and self.filter_comparison.get('date_from')
        date_to = self.filter_comparison and self.filter_comparison.get('date_to')

        # Copy value from previous_options.
        previous_value = previous_options and previous_options.get('comparison')
        if previous_value:
            # Copy the filter.
            if previous_value.get('filter'):
                cmp_filter = previous_value['filter']

                # Copy dates if filter is custom.
                if cmp_filter == 'custom':
                    if previous_value['date_from'] is not None:
                        date_from = previous_value['date_from']
                    if previous_value['date_to'] is not None:
                        date_to = previous_value['date_to']

            # Copy the number of periods.
            if previous_value.get('number_period') and previous_value['number_period'] > 1:
                number_period = previous_value['number_period']

        options['comparison'] = {'filter': cmp_filter, 'number_period': number_period}
        options['comparison']['date_from'] = date_from
        options['comparison']['date_to'] = date_to
        options['comparison']['periods'] = []

        if cmp_filter == 'no_comparison':
            return

        if cmp_filter == 'custom':
            number_period = 1

        previous_period = options['date']
        for index in range(0, number_period):
            if cmp_filter == 'previous_period':
                period_vals = self._get_dates_previous_period(options, previous_period)
            elif cmp_filter == 'same_last_year':
                period_vals = self._get_dates_previous_year(options, previous_period)
            else:
                date_from_obj = fields.Date.from_string(date_from)
                date_to_obj = fields.Date.from_string(date_to)
                period_vals = self._get_dates_period(options, date_from_obj, date_to_obj, previous_period['mode'])
            options['comparison']['periods'].append(period_vals)
            previous_period = period_vals

        if len(options['comparison']['periods']) > 0:
            options['comparison'].update(options['comparison']['periods'][0])

    @api.model
    def _get_options_date_domain(self, options):
        def create_date_domain(options_date):
            date_field = options_date.get('date_field', 'date')
            domain = [(date_field, '<=', options_date['date_to'])]
            if options_date['mode'] == 'range':
                strict_range = options_date.get('strict_range')
                if not strict_range:
                    domain += [
                        '|',
                        (date_field, '>=', options_date['date_from']),
                        ('account_id.user_type_id.include_initial_balance', '=', True)
                    ]
                else:
                    domain += [(date_field, '>=', options_date['date_from'])]
            return domain

        if not options.get('date'):
            return []
        return create_date_domain(options['date'])

    ####################################################
    # OPTIONS: analytic
    ####################################################

    @api.model
    def _init_filter_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return

        options['analytic'] = self.filter_analytic

        if self.user_has_groups('analytic.group_analytic_accounting'):
            options['analytic_accounts'] = previous_options and previous_options.get('analytic_accounts') or []
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            selected_analytic_accounts = analytic_account_ids \
                                         and self.env['account.analytic.account'].browse(analytic_account_ids) \
                                         or self.env['account.analytic.account']
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')
        if self.user_has_groups('analytic.group_analytic_tags'):
            options['analytic_tags'] = previous_options and previous_options.get('analytic_tags') or []
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            selected_analytic_tags = analytic_tag_ids \
                                     and self.env['account.analytic.tag'].browse(analytic_tag_ids) \
                                     or self.env['account.analytic.tag']
            options['selected_analytic_tag_names'] = selected_analytic_tags.mapped('name')

    @api.model
    def _get_options_analytic_domain(self, options):
        domain = []
        if options.get('analytic_accounts'):
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            domain.append(('analytic_account_id', 'in', analytic_account_ids))
        if options.get('analytic_tags'):
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            domain.append(('analytic_tag_ids', 'in', analytic_tag_ids))
        return domain

    ####################################################
    # OPTIONS: partners
    ####################################################

    @api.model
    def _init_filter_partner(self, options, previous_options=None):
        if not self.filter_partner:
            return

        options['partner'] = True
        options['partner_ids'] = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []
        selected_partner_ids = [int(partner) for partner in options['partner_ids']]
        selected_partners = selected_partner_ids and self.env['res.partner'].browse(selected_partner_ids) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('name')
        selected_partner_category_ids = [int(category) for category in options['partner_categories']]
        selected_partner_categories = selected_partner_category_ids and self.env['res.partner.category'].browse(selected_partner_category_ids) or self.env['res.partner.category']
        options['selected_partner_categories'] = selected_partner_categories.mapped('name')

    @api.model
    def _get_options_partner_domain(self, options):
        domain = []
        if options.get('partner_ids'):
            partner_ids = [int(partner) for partner in options['partner_ids']]
            domain.append(('partner_id', 'in', partner_ids))
        if options.get('partner_categories'):
            partner_category_ids = [int(category) for category in options['partner_categories']]
            domain.append(('partner_id.category_id', 'in', partner_category_ids))
        return domain

    ####################################################
    # OPTIONS: all_entries
    ####################################################

    @api.model
    def _get_options_all_entries_domain(self, options):
        if options.get('all_entries') is False:
            return [('move_id.state', '=', 'posted')]
        else:
            return [('move_id.state', '!=', 'cancel')]

    ####################################################
    # OPTIONS: order column
    ####################################################

    @api.model
    def _init_order_selected_column(self, options, previous_options=None):
        if self.order_selected_column is not None:
            options['selected_column'] = previous_options and previous_options.get('selected_column') or self.order_selected_column['default']

    ####################################################
    # OPTIONS: hierarchy
    ####################################################
    MOST_SORT_PRIO = 0
    LEAST_SORT_PRIO = 99

    # Create codes path in the hierarchy based on account.
    def get_account_codes(self, account):
        # A code is tuple(sort priority, actual code)
        codes = []
        if account.group_id:
            group = account.group_id
            while group:
                code = '%s %s' % (group.code_prefix or '', group.name)
                codes.append((self.MOST_SORT_PRIO, code))
                group = group.parent_id
        else:
            # Limit to 3 levels.
            code = account.code[:3]
            while code:
                codes.append((self.MOST_SORT_PRIO, code))
                code = code[:-1]
        return list(reversed(codes))

    @api.model
    def _sort_lines(self, lines, options):
        def merge_tree(line):
            sorted_list.append(line)
            for l in sorted(tree[line['id']], key=lambda k: selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format']):
                merge_tree(l)

        sorted_list = []
        selected_column = abs(options['selected_column']) - 1
        selected_sign = -copysign(1, options['selected_column'])
        tree = defaultdict(list)
        if 'sortable' not in self._get_columns_name(options)[selected_column].get('class', ''):
            return lines  # Nothing to do here
        for line in lines:
            tree[line.get('parent_id')].append(line)
        for line in sorted(tree[None], key=lambda k: ('total' in k.get('class', ''), selected_sign * k['columns'][selected_column - k.get('colspan', 1)]['no_format'])):
            merge_tree(line)

        return sorted_list

    @api.model
    def _create_hierarchy(self, lines, options):
        """This method is called when the option 'hiearchy' is enabled on a report.
        It receives the lines (as computed by _get_lines()) in argument, and will add
        a hiearchy in those lines by using the account.group of accounts. If not set,
        it will fallback on creating a hierarchy based on the account's code first 3
        digits.
        """
        # Avoid redundant browsing.
        accounts_cache = {}

        # Retrieve account either from cache, either by browsing.
        def get_account(id):
            if id not in accounts_cache:
                accounts_cache[id] = self.env['account.account'].browse(id)
            return accounts_cache[id]

        # Add the report line to the hierarchy recursively.
        def add_line_to_hierarchy(line, codes, level_dict, depth=None):
            # Recursively build a dict where:
            # 'children' contains only subcodes
            # 'lines' contains the lines at this level
            # This > lines [optional, i.e. not for topmost level]
            #      > children > [codes] "That" > lines
            #                                  > metadata
            #                                  > children
            #      > metadata(depth, parent ...)

            if not codes:
                return
            if not depth:
                depth = line.get('level', 1)
            level_dict.setdefault('depth', depth)
            level_dict.setdefault('parent_id', 'hierarchy_' + codes[0][1] if codes[0][0] != 'root' else codes[0][1])
            level_dict.setdefault('children', {})
            code = codes[1]
            codes = codes[1:]
            level_dict['children'].setdefault(code, {})

            if len(codes) > 1:
                add_line_to_hierarchy(line, codes, level_dict['children'][code], depth=depth + 1)
            else:
                level_dict['children'][code].setdefault('lines', [])
                level_dict['children'][code]['lines'].append(line)
                line['level'] = depth + 1
                for l in level_dict['children'][code]['lines']:
                    l['parent_id'] = 'hierarchy_' + code[1]

        # Merge a list of columns together and take care about str values.
        def merge_columns(columns):
            return [('n/a' if any(i != '' for i in x) else '') if any(isinstance(i, str) for i in x) else sum(x) for x in zip(*columns)]

        # Get_lines for the newly computed hierarchy.
        def get_hierarchy_lines(values, depth=1):
            lines = []
            sum_sum_columns = []
            unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0
            for base_line in values.get('lines', []):
                lines.append(base_line)
                sum_sum_columns.append([c.get('no_format_name', c['name']) for c in base_line['columns']])

            # For the last iteration, there might not be the children key (see add_line_to_hierarchy)
            for key in sorted(values.get('children', {}).keys()):
                sum_columns, sub_lines = get_hierarchy_lines(values['children'][key], depth=values['depth'])
                id = 'hierarchy_' + key[1]
                header_line = {
                    'id': id,
                    'name': key[1] if len(key[1]) < 60 else key[1][:60] + '...',  # second member of the tuple
                    'title_hover': key[1],
                    'unfoldable': True,
                    'unfolded': id in options.get('unfolded_lines') or unfold_all,
                    'level': values['depth'],
                    'parent_id': values['parent_id'],
                    'columns': [{'name': self.format_value(c) if not isinstance(c, str) else c} for c in sum_columns],
                }
                if key[0] == self.LEAST_SORT_PRIO:
                    header_line['style'] = 'font-style:italic;'
                lines += [header_line] + sub_lines
                sum_sum_columns.append(sum_columns)
            return merge_columns(sum_sum_columns), lines

        def deep_merge_dict(source, destination):
            for key, value in source.items():
                if isinstance(value, dict):
                    # get node or create one
                    node = destination.setdefault(key, {})
                    deep_merge_dict(value, node)
                else:
                    destination[key] = value

            return destination

        # Hierarchy of codes.
        accounts_hierarchy = {}

        new_lines = []
        no_group_lines = []
        # If no account.group at all, we need to pass once again in the loop to dispatch
        # all the lines across their account prefix, hence the None
        for line in lines + [None]:
            # Only deal with lines grouped by accounts.
            # And discriminating sections defined by account.financial.html.report.line
            is_grouped_by_account = line and (line.get('caret_options') == 'account.account' or line.get('account_id'))
            if not is_grouped_by_account or not line:

                # No group code found in any lines, compute it automatically.
                no_group_hierarchy = {}
                for no_group_line in no_group_lines:
                    codes = [('root', str(line.get('parent_id')) or 'root') if line else 'root', (self.LEAST_SORT_PRIO, _('(No Group)'))]
                    if not accounts_hierarchy:
                        account = get_account(no_group_line.get('account_id', no_group_line.get('id')))
                        codes = [('root', line and str(line.get('parent_id')) or 'root')] + self.get_account_codes(account)
                    add_line_to_hierarchy(no_group_line, codes, no_group_hierarchy, line and line.get('level') or 0 + 1)
                no_group_lines = []

                deep_merge_dict(no_group_hierarchy, accounts_hierarchy)

                # Merge the newly created hierarchy with existing lines.
                if accounts_hierarchy:
                    new_lines += get_hierarchy_lines(accounts_hierarchy)[1]
                    accounts_hierarchy = {}

                if line:
                    new_lines.append(line)
                continue

            # Exclude lines having no group.
            account = get_account(line.get('account_id', line.get('id')))
            if not account.group_id:
                no_group_lines.append(line)
                continue

            codes = [('root', str(line.get('parent_id')) or 'root')] + self.get_account_codes(account)
            add_line_to_hierarchy(line, codes, accounts_hierarchy, line.get('level', 0) + 1)

        return new_lines

    ####################################################
    # OPTIONS: CORE
    ####################################################

    @api.model
    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        }

        # Multi-company is there for security purpose and can't be disabled by a filter.
        self._init_filter_multi_company(options, previous_options=previous_options)

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)

        filter_list = [attr for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_')) and attr not in ('filter_date', 'filter_comparison') and len(attr) > 7 and not callable(getattr(self, attr))]
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[filter_key[7:]] = filter_opt
        return options

    @api.model
    def _get_options_domain(self, options):
        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
        ]
        domain += self._get_options_companies_domain(options)
        domain += self._get_options_journals_domain(options)
        domain += self._get_options_date_domain(options)
        domain += self._get_options_analytic_domain(options)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        return domain

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _get_query_currency_table(self, options):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param options: The report options.
        :return:        The query representing the currency table.
        '''

        user_company = self.env.company
        user_currency = user_company.currency_id
        if options.get('multi_company'):
            company_ids = [c['id'] for c in self._get_options_companies(options) if c['id'] != user_company.id and c['selected']]
            company_ids.append(self.env.company.id)
            companies = self.env['res.company'].browse(company_ids)
            conversion_date = options['date']['date_to']
            currency_rates = companies.mapped('currency_id')._get_rates(user_company, conversion_date)
        else:
            companies = user_company
            currency_rates = {user_currency.id: 1.0}

        conversion_rates = []
        for company in companies:
            conversion_rates.append((
                company.id,
                currency_rates[user_company.currency_id.id] / currency_rates[company.currency_id.id],
                user_currency.decimal_places,
            ))

        currency_table = ','.join('(%s, %s, %s)' % args for args in conversion_rates)
        return '(VALUES %s) AS currency_table(company_id, rate, precision)' % currency_table

    @api.model
    def _query_get(self, options, domain=None):
        domain = self._get_options_domain(options) + (domain or [])
        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query.get_sql()

    ####################################################
    # MISC
    ####################################################

    def get_header(self, options):
        if not options.get('groups', {}).get('ids'):
            columns = self._get_columns_name(options)
            if 'selected_column' in options and self.order_selected_column:
                selected_column = columns[abs(options['selected_column']) - 1]
                if 'sortable' in selected_column.get('class', ''):
                    selected_column['class'] = (options['selected_column'] > 0 and 'up ' or 'down ') + selected_column['class']
            return [columns]
        return self._get_columns_name_hierarchy(options)

    #TO BE OVERWRITTEN
    def _get_columns_name_hierarchy(self, options):
        return []

    # TO BE OVERWRITTEN
    def _get_columns_name(self, options):
        return []

    #TO BE OVERWRITTEN
    def _get_lines(self, options, line_id=None):
        return []

    #TO BE OVERWRITTEN
    def _get_templates(self):
        return {
                'main_template': 'account_reports.main_template',
                'main_table_header_template': 'account_reports.main_table_header',
                'line_template': 'account_reports.line_template',
                'footnotes_template': 'account_reports.footnotes_template',
                'search_template': 'account_reports.search_template',
        }

    #TO BE OVERWRITTEN
    def _get_report_name(self):
        return _('General Report')

    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        return self._get_report_name().lower().replace(' ', '_')

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].browse([action_id])
        action_type = action.type
        action = self.env[action.type].browse([action_id])
        action_read = action.read()[0]
        if action_type == 'ir.actions.client':
            # Check if we are opening another report and if yes, pass options and ignore_session
            if action.tag == 'account_report':
                options['unfolded_lines'] = []
                options['unfold_all'] = False
                action_read.update({'options': options, 'ignore_session': 'read'})
        if params.get('id'):
            # Add the id of the account.financial.html.report.line in the action's context
            context = action_read.get('context') and safe_eval(action_read['context']) or {}
            context.setdefault('active_id', int(params['id']))
            action_read['context'] = context
        return action_read

    @api.model
    def _resolve_caret_option_document(self, model, res_id, document):
        '''Retrieve the target record of the caret option.

        :param model:       The source model of the report line, 'account.move.line' by default.
        :param res_id:      The source id of the report line.
        :param document:    The target model of the redirection.
        :return: The target record.
        '''
        if model == 'account.move':
            if document == 'res.partner':
                return self.env[model].browse(res_id).partner_id.commercial_partner_id
        if model == 'account.bank.statement.line' and document == 'account.bank.statement':
            return self.env[model].browse(res_id).statement_id

        # model == 'account.move.line' by default.
        if document == 'account.move':
            return self.env[model].browse(res_id).move_id
        if document == 'account.payment':
            return self.env[model].browse(res_id).payment_id

        return self.env[model].browse(res_id)

    @api.model
    def _resolve_caret_option_view(self, target):
        '''Retrieve the target view name of the caret option.

        :param target:  The target record of the redirection.
        :return: The target view name as a string.
        '''
        if target._name == 'account.payment':
            return 'account.view_account_payment_form'
        if target._name == 'res.partner':
            return 'base.view_partner_form'
        if target._name == 'account.bank.statement':
            return 'account.view_bank_statement_form'

        # document == 'account.move' by default.
        return 'view_move_form'

    def open_document(self, options, params=None):
        if not params:
            params = {}

        ctx = self.env.context.copy()
        ctx.pop('id', '')

        # Decode params
        model = params.get('model', 'account.move.line')
        res_id = params.get('id')
        document = params.get('object', 'account.move')

        # Redirection data
        target = self._resolve_caret_option_document(model, res_id, document)
        view_name = self._resolve_caret_option_view(target)
        module = 'account'
        if '.' in view_name:
            module, view_name = view_name.split('.')

        # Redirect
        view_id = self.env['ir.model.data'].get_object_reference(module, view_name)[1]
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'res_model': document,
            'view_id': view_id,
            'res_id': target.id,
            'context': ctx,
        }

    def open_action(self, options, domain):
        assert isinstance(domain, (list, tuple))
        domain += [('date', '>=', options.get('date').get('date_from')),
                   ('date', '<=', options.get('date').get('date_to'))]
        if not options.get('all_entries'):
            domain += [('move_id.state', '=', 'posted')]

        ctx = self.env.context.copy()
        ctx.update({'search_default_account': 1, 'search_default_groupby_date': 1})

        action = self.env.ref('account.action_move_line_select_tax_audit').read()[0]
        action = clean_action(action)
        action['domain'] = domain
        action['context'] = ctx
        return action

    def open_tax(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        tax = self.env['account.tax'].browse(active_id)
        domain = ['|', ('tax_ids', 'in', [active_id]),
                       ('tax_line_id', 'in', [active_id])]
        if tax.tax_exigibility == 'on_payment':
            domain += [('tax_exigible', '=', True)]
        return self.open_action(options, domain)

    def tax_tag_template_open_aml(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        tag_template = self.env['account.tax.report.line'].browse(active_id)
        domain = [('tag_ids', 'in', tag_template.tag_ids.ids), ('tax_exigible', '=', True)]
        return self.open_action(options, domain)

    def open_tax_report_line(self, options, params=None):
        active_id = int(str(params.get('id')).split('_')[0])
        line = self.env['account.financial.html.report.line'].browse(active_id)
        domain = ast.literal_eval(line.domain)
        action = self.open_action(options, domain)
        action['display_name'] = _('Journal Items (%s)') % line.name
        return action

    def view_too_many(self, options, params=None):
        model, active_id = params.get('actionId').split(',')
        ctx = self.env.context.copy()
        if model == 'account':
            action = self.env.ref('account.action_move_line_select').read()[0]
            ctx.update({
                'search_default_account_id': [int(active_id)],
                'active_id': int(active_id),
                })
        if model == 'partner':
            action = self.env.ref('account.action_move_line_select_by_partner').read()[0]
            ctx.update({
                'search_default_partner_id': [int(active_id)],
                'active_id': int(active_id),
                })
        action = clean_action(action)
        action['context'] = ctx
        return action

    def open_general_ledger(self, options, params=None):
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        action = self.env.ref('account_reports.action_account_report_general_ledger').read()[0]
        options['unfolded_lines'] = ['account_%s' % (params.get('id', ''),)]
        options['unfold_all'] = False
        ctx.update({'model': 'account.general.ledger'})
        action.update({'options': options, 'context': ctx, 'ignore_session': 'read'})
        return action

    def open_unposted_moves(self, options, params=None):
        ''' Open the list of draft journal entries that might impact the reporting'''
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action = clean_action(action)
        domain = [('state', '=', 'draft')]
        if options.get('date'):
            #there's no condition on the date from, as a draft entry might change the initial balance of a line
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            domain += [('date', '<=', date_to)]
        action['domain'] = domain
        #overwrite the context to avoid default filtering on 'misc' journals
        action['context'] = {}
        return action

    def periodic_tva_entries(self, options):
        # Return action to open form view of newly entry created
        ctx = self._set_context(options)
        ctx['strict_range'] = True
        self = self.with_context(ctx)
        move = self.env['account.generic.tax.report']._generate_tax_closing_entry(options)
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action = clean_action(action)
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = move.id
        return action

    def _get_vat_report_attachments(self, options):
        # Fetch pdf
        pdf = self.get_pdf(options)
        return [('vat_report.pdf', pdf)]

    def action_partner_reconcile(self, options, params):
        form = self.env.ref('account.action_manual_reconciliation', False)
        ctx = self.env.context.copy()
        ctx['partner_ids'] = ctx['active_id'] = [params.get('partner_id')]
        ctx['all_entries'] = True
        return {
            'type': 'ir.actions.client',
            'view_id': form.id,
            'tag': form.tag,
            'context': ctx,
        }

    def open_journal_items(self, options, params):
        action = self.env.ref('account.action_move_line_select').read()[0]
        action = clean_action(action)
        ctx = self.env.context.copy()
        if params and 'id' in params:
            active_id = params['id']
            ctx.update({
                    'search_default_account_id': [active_id],
            })

        if options:
            if options.get('journals'):
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if selected_journals: # Otherwise, nothing is selected, so we want to display everything
                    ctx.update({
                        'search_default_journal_id': selected_journals,
                    })

            domain = expression.normalize_domain(ast.literal_eval(action.get('domain', '[]')))
            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('analytic_account_id', 'in', analytic_ids)]])
            if options.get('date'):
                opt_date = options['date']
                if opt_date.get('date_from'):
                    domain = expression.AND([domain, [('date', '>=', opt_date['date_from'])]])
                if opt_date.get('date_to'):
                    domain = expression.AND([domain, [('date', '<=', opt_date['date_to'])]])
                if not opt_date.keys() & {'date_from', 'date_to'} and opt_date.get('date'):
                    domain = expression.AND([domain, [('date', '<=', opt_date['date'])]])
            # In case the line has been generated for a "group by" financial line, append the parent line's domain to the one we created
            if params.get('financial_group_line_id'):
                # In case the hierarchy is enabled, 'financial_group_line_id' might be a string such
                # as 'hierarchy_xxx'. This will obviously cause a crash at domain evaluation.
                if not (isinstance(params['financial_group_line_id'], str) and 'hierarchy_' in params['financial_group_line_id']):
                    parent_financial_report_line = self.env['account.financial.html.report.line'].browse(params['financial_group_line_id'])
                    domain = expression.AND([domain, safe_eval(parent_financial_report_line.domain)])

            if not options.get('all_entries'):
                ctx['search_default_posted'] = True

            action['domain'] = domain
        action['context'] = ctx
        return action

    def reverse(self, values):
        """Utility method used to reverse a list, this method is used during template generation in order to reverse periods for example"""
        if type(values) != list:
            return values
        else:
            inv_values = copy.deepcopy(values)
            inv_values.reverse()
        return inv_values

    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        company_ids = []
        if options.get('multi_company'):
            company_ids = [c.get('id') for c in options['multi_company'] if c.get('selected')]
            company_ids = company_ids if len(company_ids) > 0 else [c.get('id') for c in options['multi_company']]
        ctx['company_ids'] = len(company_ids) > 0 and company_ids or [self.env.company.id]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in options['partner_categories']]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view'].render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info

    def _check_report_security(self, options):
        '''The security check must be done in this method. It ensures no-one can by-passing some access rules
        (e.g. falsifying the options).

        :param options:     The report options.
        '''
        # Check the options has not been falsified in order to access not allowed companies.
        user_company_ids = self.env.user.company_ids.ids
        if options.get('multi_company'):
            group_multi_company = self.env.ref('base.group_multi_company')
            if self.env.user.id not in group_multi_company.users.ids:
                options.pop('multi_company')
            else:
                options['multi_company'] = [opt for opt in options['multi_company'] if opt['id'] in user_company_ids]

    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Check the security before updating the context to make sure the options are safe.
        self._check_report_security(options)

        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates()
        report_manager = self._get_report_manager(options)
        report = {'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,}
        lines = self._get_lines(options, line_id=line_id)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        rcontext = {'report': report,
                    'lines': {'columns_header': self.get_header(options), 'lines': lines},
                    'options': options,
                    'context': self.env.context,
                    'model': self,
                }
        if additional_context and type(additional_context) == dict:
            rcontext.update(additional_context)
        if self.env.context.get('analytic_account_ids'):
            rcontext['options']['analytic_account_ids'] = [
                {'id': acc.id, 'name': acc.name} for acc in self.env.context['analytic_account_ids']
            ]

        render_template = templates.get('main_template', 'account_reports.main_template')
        if line_id is not None:
            render_template = templates.get('line_template', 'account_reports.line_template')
        html = self.env['ir.ui.view'].render_template(
            render_template,
            values=dict(rcontext),
        )
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
        return html

    def get_html_footnotes(self, footnotes):
        template = self._get_templates().get('footnotes_template', 'account_reports.footnotes_template')
        rcontext = {'footnotes': footnotes, 'context': self.env.context}
        html = self.env['ir.ui.view'].render_template(template, values=dict(rcontext))
        return html

    def _get_reports_buttons_in_sequence(self):
        return sorted(self._get_reports_buttons(), key=lambda x: x.get('sequence', 9))

    def _get_reports_buttons(self):
        return [
            {'name': _('Print Preview'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
            {'name': _('Export (XLSX)'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
            {'name':_('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
        ]

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        new_wizard = self.env['account_reports.export.wizard'].create({'report_model': self._name,'report_id': self.id})
        view_id = self.env.ref('account_reports.view_report_export_wizard').id
        new_context = self.env.context.copy()
        new_context['account_report_generation_options'] = options
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'account_reports.export.wizard',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
            'context': new_context,
        }


    @api.model
    def get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'xlsx': 'application/vnd.ms-excel',
            'pdf': 'application/pdf',
            'xml': 'application/vnd.sun.xml.writer',
            'xaf': 'application/vnd.sun.xml.writer',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
        }
        return type_mapping.get(file_type, False)

    def _get_report_manager(self, options):
        domain = [('report_name', '=', self._name)]
        domain = (domain + [('financial_report_id', '=', self.id)]) if 'id' in dir(self) else domain
        selected_companies = []
        if options.get('multi_company'):
            selected_companies = [c['id'] for c in options['multi_company'] if c.get('selected')]
        if len(selected_companies) == 1:
            domain += [('company_id', '=', selected_companies[0])]
        existing_manager = self.env['account.report.manager'].search(domain, limit=1)
        if not existing_manager:
            existing_manager = self.env['account.report.manager'].create({'report_name': self._name, 'company_id': selected_companies and selected_companies[0] or False, 'financial_report_id': self.id if 'id' in dir(self) else False})
        return existing_manager

    @api.model
    def format_value(self, amount, currency=False, blank_if_zero=False):
        ''' Format amount to have a monetary display (with a currency symbol).
        E.g: 1000 => 1000.0 $

        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:                The formatted amount as a string.
        '''
        currency_id = currency or self.env.company.currency_id
        if currency_id.is_zero(amount):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            amount = abs(amount)

        if self.env.context.get('no_format'):
            return amount
        return formatLang(self.env, amount, currency_obj=currency_id)

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name):
        ''' Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        '''
        names = []
        if move_name != '/':
            names.append(move_name)
        if move_ref and move_ref != '/':
            names.append(move_ref)
        if line_name and line_name != '/':
            names.append(line_name)
        name = '-'.join(names)
        # TODO: check if no_format is still needed
        if len(name) > 35 and not self.env.context.get('no_format'):
            name = name[:32] + "..."
        return name

    def format_date(self, options, dt_filter='date'):
        date_from = fields.Date.from_string(options[dt_filter]['date_from'])
        date_to = fields.Date.from_string(options[dt_filter]['date_to'])
        return self._get_dates_period(options, date_from, date_to, options['date']['mode'])['string']

    def print_pdf(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'pdf',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def _replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {b'o_account_reports_no_print': b'', b'table-responsive': b'', b'<a': b'<span', b'</a>': b'</span>'}

    def get_pdf(self, options, minimal_layout=True):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body = self.env['ir.ui.view'].render_template(
            "account_reports.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">', b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
            spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                    'css': '',
                    'o': self.env.user,
                    'res_company': self.env.company,
                })
            header = self.env['ir.actions.report'].render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8') # Ensure that headers and footer are correctly encoded
            spec_paperformat_args = {}
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args
        )

    def print_xlsx(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xlsx',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def _get_super_columns(self, options):
        """
        Essentially used when getting the xlsx of a report
        Some reports may need super title cells on top of regular
        columns title, This methods retrieve the formers.
        e.g. in Trial Balance, you can compare periods (super cells)
            and each have debit/credit columns


        @params {dict} options: options for computing the report
        @return {dict}:
            {list(dict)} columns: the dict of the super columns of the xlsx report,
                the columns' string is contained into the 'string' key
            {int} merge: optional parameter. Indicates to xlsxwriter
                that it should put the contents of each column into the resulting
                cell of the merge of this [merge] number of cells
                -- only merging on one line is supported
            {int} x_offset: tells xlsxwriter it should start writing the columns from
                [x_offset] cells on the left
        """
        return {}

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)

        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = super_columns.get('merge')
            if x_merge and x_merge > 1:
                sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1
        for row in self.get_header(options):
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update({'no_format':True, 'print_mode':True, 'prefetch_fields': False})
        # deactivating the prefetching saves ~35% on get_lines running time
        lines = self.with_context(ctx)._get_lines(options)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        #write all data rows
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file

    def _get_cell_type_value(self, cell):
        if 'date' not in cell.get('class', '') or not cell.get('name'):
            # cell is not a date
            return ('text', cell.get('name', ''))
        if isinstance(cell['name'], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ('date', cell['name'])
        try:
            # the date is parsable to a xlsx compatible date
            return ('date', parse_date(cell['name'], locale=get_lang(self.env).code))
        except:
            # the date is not parsable thus is returned as text
            return ('text', cell['name'])

    def print_xml(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'xml',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_xml(self, options):
        return False

    def print_txt(self, options):
        return {
                'type': 'ir_actions_account_report_download',
                'data': {'model': self.env.context.get('model'),
                         'options': json.dumps(options),
                         'output_format': 'txt',
                         'financial_id': self.env.context.get('id'),
                         }
                }

    def get_txt(self, options):
        return False

    ####################################################
    # HOOKS
    ####################################################

    def _get_account_groups_for_asset_report(self):
        """ Get the groups of account code
        return: dict whose keys are the 2 first digits of an account (xx) or a
                range of 2 first digits (xx-yy). If it is not a range, the value
                for that key shouldbe a dict containeing the key 'name'. If it
                is a range, it should also contain a dict for the key 'children'
                that is defined the same way as this return value.
        """
        return {}
