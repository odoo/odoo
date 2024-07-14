# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import logging
import math
import re
import base64
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key

import markupsafe
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta

from odoo.addons.web.controllers.utils import clean_action
from odoo import models, fields, api, _, osv, _lt
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval
from odoo.models import check_method_name
from itertools import groupby

_logger = logging.getLogger(__name__)

ACCOUNT_CODES_ENGINE_SPLIT_REGEX = re.compile(r"(?=[+-])")

ACCOUNT_CODES_ENGINE_TERM_REGEX = re.compile(
    r"^(?P<sign>[+-]?)"\
    r"(?P<prefix>([A-Za-z\d.]*|tag\([\w.]+\))((?=\\)|(?<=[^CD])))"\
    r"(\\\((?P<excluded_prefixes>([A-Za-z\d.]+,)*[A-Za-z\d.]*)\))?"\
    r"(?P<balance_character>[DC]?)$"
)

ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX = re.compile(r"tag\(((?P<id>\d+)|(?P<ref>\w+\.\w+))\)")

# Performance optimisation: those engines always will receive None as their next_groupby, allowing more efficient batching.
NO_NEXT_GROUPBY_ENGINES = {'tax_tags', 'account_codes'}

LINE_ID_HIERARCHY_DELIMITER = '|'


class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Account Report Footnote'

    report_id = fields.Many2one('account.report')
    line_id = fields.Char(index=True)
    text = fields.Char()


class AccountReport(models.Model):
    _inherit = 'account.report'

    horizontal_group_ids = fields.Many2many(string="Horizontal Groups", comodel_name='account.report.horizontal.group')
    footnotes_ids = fields.One2many(string="Footnotes", comodel_name='account.report.footnote', inverse_name='report_id')

    # Those fields allow case-by-case fine-tuning of the engine, for custom reports.
    custom_handler_model_id = fields.Many2one(string='Custom Handler Model', comodel_name='ir.model')
    custom_handler_model_name = fields.Char(string='Custom Handler Model Name', related='custom_handler_model_id.model')

    # Account Coverage Report
    is_account_coverage_report_available = fields.Boolean(compute='_compute_is_account_coverage_report_available')

    @api.constrains('custom_handler_model_id')
    def _validate_custom_handler_model(self):
        for report in self:
            if report.custom_handler_model_id:
                custom_handler_model = self.env.registry['account.report.custom.handler']
                current_model = self.env[report.custom_handler_model_name]
                if not isinstance(current_model, custom_handler_model):
                    raise ValidationError(_(
                        "Field 'Custom Handler Model' can only reference records inheriting from [%s].",
                        custom_handler_model._name
                    ))

    def unlink(self):
        for report in self:
            action, menuitem = report._get_existing_menuitem()
            menuitem.unlink()
            action.unlink()
        return super().unlink()

    def write(self, vals):
        if 'active' in vals:
            for report in self:
                dummy, menuitem = report._get_existing_menuitem()
                menuitem.active = vals['active']
        return super().write(vals)

    ####################################################
    # MENU MANAGEMENT
    ####################################################

    def _get_existing_menuitem(self):
        self.ensure_one()
        action = self.env['ir.actions.client'] \
            .search([('name', '=', self.name), ('tag', '=', 'account_report')]) \
            .filtered(lambda act: ast.literal_eval(act.context).get('report_id') == self.id)
        menuitem = self.env['ir.ui.menu'] \
            .with_context({'active_test': False, 'ir.ui.menu.full_list': True}) \
            .search([('action', '=', f'ir.actions.client,{action.id}')])
        return action, menuitem

    def _create_menu_item_for_report(self):
        """ Adds a default menu item for this report. This is called by an action on the report, for reports created manually by the user.
        """
        self.ensure_one()

        action, menuitem = self._get_existing_menuitem()

        if menuitem:
            raise UserError(_("This report already has a menuitem."))

        if not action:
            action = self.env['ir.actions.client'].create({
                'name': self.name,
                'tag': 'account_report',
                'context': {'report_id': self.id},
            })

        self.env['ir.ui.menu'].create({
            'name': self.name,
            'parent_id': self.env['ir.model.data']._xmlid_to_res_id('account.menu_finance_reports'),
            'action': f'ir.actions.client,{action.id}',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    ####################################################
    # OPTIONS: journals
    ####################################################

    def _get_filter_journals(self, options, additional_domain=None):
        return self.env['account.journal'].with_context(active_test=False).search([
                *self.env['account.journal']._check_company_domain(self.get_report_company_ids(options)),
                *(additional_domain or []),
            ], order="company_id, name")

    def _get_filter_journal_groups(self, options, report_accepted_journals):
        groups = self.env['account.journal.group'].search([
            ('company_id', 'in', self.get_report_company_ids(options)),
            ], order='sequence')

        all_journals = self._get_filter_journals(options)
        all_journals_by_company = {}
        for journal in all_journals:
            all_journals_by_company.setdefault(journal.company_id, self.env['account.journal'])
            all_journals_by_company[journal.company_id] += journal

        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if some journals it could accept are accepted by this report
            group_accepted_journals = all_journals_by_company[journal_group.company_id] - journal_group.excluded_journal_ids
            if report_accepted_journals & group_accepted_journals:
                ret += journal_group
        return ret

    def _init_options_journals(self, options, previous_options=None, additional_journals_domain=None):
        # The additional additional_journals_domain optinal parameter allows calling this with an additional restriction on journals,
        # to regenerate the journal options accordingly.

        if not self.filter_journals:
            return

        # Collect all stuff and split them by company.
        all_journals = self._get_filter_journals(options, additional_domain=additional_journals_domain)
        all_journal_groups = self._get_filter_journal_groups(options, all_journals)
        all_journal_ids = set(all_journals.ids)

        report_companies = self.env['res.company'].browse(self.get_report_company_ids(options))
        per_company_map = {}
        for company in report_companies.sudo().parent_ids:
            per_company_map[company.id] = ({
                'available_journals': self.env['account.journal'],
                'available_journal_groups': self.env['account.journal.group'],
                'selected_journals': self.env['account.journal'],
                'selected_journal_groups': self.env['account.journal.group'],
            })

        for journal in all_journals:
            per_company_map[journal.company_id.id]['available_journals'] |= journal
        for journal_group in all_journal_groups:
            per_company_map[journal_group.company_id.id]['available_journal_groups'] |= journal_group

        # Adapt the code from previous options.
        previous_journals = previous_options.get('journals', []) if previous_options else []
        if previous_options and (not previous_journals or any(journal_opt['id'] in all_journal_ids for journal_opt in previous_journals)):
            # Reload from previous options.
            for journal_opt in previous_journals:
                if journal_opt.get('model') == 'account.journal' and journal_opt.get('selected'):
                    journal_id = int(journal_opt['id'])
                    if journal_id in all_journal_ids:
                        journal = self.env['account.journal'].browse(journal_id)
                        per_company_map[journal.company_id.id]['selected_journals'] |= journal

            # Process the action performed by the user js-side.
            journal_group_action = previous_options.get('__journal_group_action', None)
            if journal_group_action:
                action = journal_group_action['action']
                group = self.env['account.journal.group'].browse(journal_group_action['id'])
                company_vals = per_company_map[group.company_id.id]
                if action == 'add':
                    remaining_journals = company_vals['available_journals'] - group.excluded_journal_ids
                    company_vals['selected_journals'] = remaining_journals
                elif action == 'remove':
                    has_selected_journal_in_other_company = False
                    for company_id, other_company_vals in per_company_map.items():
                        if company_id == group.company_id.id:
                            continue

                        if other_company_vals['selected_journals']:
                            has_selected_journal_in_other_company = True
                            break

                    if has_selected_journal_in_other_company:
                        company_vals['selected_journals'] = company_vals['available_journals']
                    else:
                        company_vals['selected_journals'] = self.env['account.journal']

                    # When removing the last selected group in multi-company, make sure there is no selected journal left.
                    # For example, suppose company1 having j1, j2 as journals and group1 excluding j2, company2 having j3, j4.
                    # Suppose group1, j1, j3, j4 selected. If group1 is removed, we need to unselect j3 and j4 as well.
                    if all(x['selected_journals'] == x['available_journals'] for x in per_company_map.values()):
                        for company_vals in per_company_map.values():
                            company_vals['selected_journals'] = self.env['account.journal']
        else:
            # Select the first available group if nothing selected.
            has_selected_at_least_one_group = False
            for company_id, company_vals in per_company_map.items():
                if not company_vals['selected_journals'] and company_vals['available_journal_groups']:
                    first_group = company_vals['available_journal_groups'][0]
                    remaining_journals = company_vals['available_journals'] - first_group.excluded_journal_ids
                    company_vals['selected_journals'] = remaining_journals
                    has_selected_at_least_one_group = True

            # Select all journals in others groups.
            if has_selected_at_least_one_group:
                for company_id, company_vals in per_company_map.items():
                    if not company_vals['selected_journals']:
                        company_vals['selected_journals'] = company_vals['available_journals']

        # Build the options.
        journal_groups_options = []
        journal_options_per_company = defaultdict(list)
        for company_id, company_vals in per_company_map.items():

            # Groups.
            for group in company_vals['available_journal_groups']:
                remaining_journals = company_vals['available_journals'] - company_vals['selected_journals']
                selected = remaining_journals == (group.excluded_journal_ids & company_vals['available_journals'])
                journal_groups_options.append({
                    'id': group.id,
                    'model': group._name,
                    'name': group.display_name,
                    'title': group.display_name,
                    'selected': selected,
                    'journal_types': list(set(remaining_journals.mapped('type'))),
                })
                if selected:
                    company_vals['selected_journal_groups'] |= group

            # Journals.
            for journal in company_vals['available_journals']:
                journal_options_per_company[journal.company_id].append({
                    'id': journal.id,
                    'model': journal._name,
                    'name': journal.display_name,
                    'title': f"{journal.name} - {journal.code}",
                    'selected': journal in company_vals['selected_journals'],
                    'type': journal.type,
                })

        # Build the final options.
        options['journals'] = []
        if journal_groups_options:
            options['journals'].append({
                'id': 'divider',
                'name': _("Journal Groups"),
                'model': 'account.journal.group',
            })
            options['journals'] += journal_groups_options
        for company, journal_options in journal_options_per_company.items():
            if len(journal_options_per_company) > 1 or journal_groups_options:
                options['journals'].append({
                    'id': 'divider',
                    'model': company._name,
                    'name': company.display_name,
                })
            options['journals'] += journal_options

        # Compute the name to display on the widget.
        names_to_display = []

        has_globally_selected_groups = False
        has_selected_all_journals = True
        for company_id, journal_options in per_company_map.items():
            for journal_group in journal_options['selected_journal_groups']:
                names_to_display.append(journal_group.display_name)
                has_globally_selected_groups = True
            if journal_options['selected_journals'] != journal_options['available_journals']:
                has_selected_all_journals = False

        for company_id, journal_options in per_company_map.items():
            has_selected_groups = bool(journal_options['selected_journal_groups'])
            if not has_selected_groups and (not has_selected_all_journals or has_globally_selected_groups):
                for journal in journal_options['selected_journals']:
                    names_to_display.append(journal.code)

        if not names_to_display:
            names_to_display.append(_("All Journals"))
            for journal_option in options['journals']:
                if journal_option.get('model') == 'account.journal':
                    journal_option['selected'] = False

        # Abbreviate the name
        max_nb_journals_displayed = 5
        nb_remaining = len(names_to_display) - max_nb_journals_displayed
        if nb_remaining == 1:
            options['name_journal_group'] = ', '.join(names_to_display[:max_nb_journals_displayed]) + _(" and one other")
        elif nb_remaining > 1:
            options['name_journal_group'] = ', '.join(names_to_display[:max_nb_journals_displayed]) + _(" and %s others", nb_remaining)
        else:
            options['name_journal_group'] = ', '.join(names_to_display)

    @api.model
    def _get_options_journals(self, options):
        selected_journals = [
            journal for journal in options.get('journals', [])
            if journal['model'] == 'account.journal' and journal['selected']
        ]
        if not selected_journals:
            # If no journal is specifically selected, we actually want to select them all.
            # This is needed, because some reports will not use ALL available journals and filter by type.
            # Without getting them from the options, we will use them all, which is wrong.
            selected_journals = [
                journal for journal in options.get('journals', [])
                if journal['model'] == 'account.journal'
            ]
        return selected_journals

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    # ####################################################
    # OPTIONS: USER DEFINED FILTERS ON AML
    ####################################################
    def _init_options_aml_ir_filters(self, options, previous_options=None):
        options['aml_ir_filters'] = []
        if not self.filter_aml_ir_filters:
            return

        ir_filters = self.env['ir.filters'].search([('model_id', '=', 'account.move.line')])
        if not ir_filters:
            return

        aml_ir_filters = [{'id': x.id, 'name': x.name, 'selected': False} for x in ir_filters]
        previous_options_aml_ir_filters = previous_options.get('aml_ir_filters', []) if previous_options else []
        previous_options_filters_map = {filter_item['id']: filter_item for filter_item in previous_options_aml_ir_filters}

        for filter_item in aml_ir_filters:
            if filter_item['id'] in previous_options_filters_map:
                filter_item['selected'] = previous_options_filters_map[filter_item['id']]['selected']

        options['aml_ir_filters'] = aml_ir_filters

    @api.model
    def _get_options_aml_ir_filters(self, options):
        selected_filters_ids = [
            filter_item['id']
            for filter_item in options.get('aml_ir_filters', [])
            if filter_item['selected']
        ]

        if not selected_filters_ids:
            return []

        selected_ir_filters = self.env['ir.filters'].browse(selected_filters_ids)
        return osv.expression.OR([filter_record._get_eval_domain() for filter_record in selected_ir_filters])

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    @api.model
    def _get_dates_period(self, date_from, date_to, mode, period_type=None):
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
                string = _('As of %s', format_date(self.env, date_to))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s', dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals, tax_period=False):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if tax_period:
            date_from, date_to = self.env.company._get_tax_closing_period_boundaries(date_to)
            return self._get_dates_period(date_from, date_to, mode)
        if period_type in ('fiscalyear', 'today'):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode)
        if period_type in ('month', 'custom'):
            return self._get_dates_period(*date_utils.get_month(date_to), mode, period_type='month')
        if period_type == 'quarter':
            return self._get_dates_period(*date_utils.get_quarter(date_to), mode, period_type='quarter')
        if period_type == 'year':
            return self._get_dates_period(*date_utils.get_fiscal_year(date_to), mode, period_type='year')
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

        return self._get_dates_period(date_from, date_to, mode, period_type=period_type)

    def _init_options_date(self, options, previous_options=None):
        """ Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        previous_date = (previous_options or {}).get('date', {})
        previous_date_to = previous_date.get('date_to')
        previous_date_from = previous_date.get('date_from')
        previous_mode = previous_date.get('mode')
        previous_filter = previous_date.get('filter', 'custom')

        default_filter = self.default_opening_date_filter
        options_mode = 'range' if self.filter_date_range else 'single'
        date_from = date_to = period_type = False

        if previous_mode == 'single' and options_mode == 'range':
            # 'single' date mode to 'range'.
            if previous_filter:
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                options_filter = 'custom'
            else:
                options_filter = default_filter
        elif previous_mode == 'range' and options_mode == 'single':
            # 'range' date mode to 'single'.
            if previous_filter == 'custom':
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif previous_filter:
                options_filter = previous_filter
            else:
                options_filter = default_filter
        elif (previous_mode is None or previous_mode == options_mode) and previous_date:
            # Same date mode.
            if previous_filter == 'custom':
                if options_mode == 'range':
                    date_from = fields.Date.from_string(previous_date_from)
                    date_to = fields.Date.from_string(previous_date_to)
                else:
                    date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                    date_from = date_utils.get_month(date_to)[0]

                options_filter = 'custom'
            else:
                options_filter = previous_filter
        else:
            # Default.
            options_filter = default_filter

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == 'today':
                date_to = fields.Date.context_today(self)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                period_type = 'today'
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
            elif 'tax_period' in options_filter:
                date_from, date_to = self.env.company._get_tax_closing_period_boundaries(fields.Date.context_today(self))

        options['date'] = self._get_dates_period(
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
        )

        if 'last' in options_filter:
            options['date'] = self._get_dates_previous_period(options, options['date'], tax_period='tax_period' in options_filter)

        options['date']['filter'] = options_filter

    def _init_options_comparison(self, options, previous_options=None):
        """ Initialize the 'comparison' options key.

        This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if not self.filter_period_comparison:
            return

        previous_comparison = (previous_options or {}).get('comparison', {})
        previous_filter = previous_comparison.get('filter')

        if previous_filter == 'custom':
            # Try to adapt the previous 'custom' filter.
            date_from = previous_comparison.get('date_from')
            date_to = previous_comparison.get('date_to')
            number_period = 1
            options_filter = 'custom'
        else:
            # Use the 'date' options.
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            number_period = previous_comparison.get('number_period', 1) or 0
            options_filter = number_period and previous_filter or 'no_comparison'

        options['comparison'] = {
            'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
        }

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        if options_filter == 'custom':
            options['comparison']['periods'].append(self._get_dates_period(
                date_from_obj,
                date_to_obj,
                options['date']['mode'],
            ))
        elif options_filter in ('previous_period', 'same_last_year'):
            previous_period = options['date']
            for dummy in range(0, number_period):
                if options_filter == 'previous_period':
                    period_vals = self._get_dates_previous_period(options, previous_period)
                elif options_filter == 'same_last_year':
                    period_vals = self._get_dates_previous_year(options, previous_period)
                else:
                    date_from_obj = fields.Date.from_string(date_from)
                    date_to_obj = fields.Date.from_string(date_to)
                    period_vals = self._get_dates_period(date_from_obj, date_to_obj, previous_period['mode'])
                options['comparison']['periods'].append(period_vals)
                previous_period = period_vals

        if len(options['comparison']['periods']) > 0:
            options['comparison'].update(options['comparison']['periods'][0])

    def _init_options_growth_comparison(self, options, previous_options=None):
        options['show_growth_comparison'] = self._display_growth_comparison(options)

    def _get_options_date_domain(self, options, date_scope):
        date_from, date_to, allow_include_initial_balance = self._get_date_bounds_info(options, date_scope)

        scope_domain = [('date', '<=', date_to)]
        if date_from:
            if allow_include_initial_balance:
                scope_domain += [
                    '|',
                    ('date', '>=', date_from),
                    ('account_id.include_initial_balance', '=', True),
                ]
            else:
                scope_domain += [('date', '>=', date_from)]

        return scope_domain

    def _get_date_bounds_info(self, options, date_scope):
        # Default values (the ones from 'strict_range')
        date_to = options['date']['date_to']
        date_from = options['date']['date_from'] if options['date']['mode'] == 'range' else None
        allow_include_initial_balance = False

        if date_scope == 'normal':
            allow_include_initial_balance = True

        elif date_scope == 'from_beginning':
            date_from = None

        elif date_scope == 'to_beginning_of_period':
            date_tmp = fields.Date.from_string(date_from or date_to) - relativedelta(days=1)
            date_to = date_tmp.strftime('%Y-%m-%d')
            date_from = None

        elif date_scope == 'from_fiscalyear':
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)['date_from']
            date_from = date_tmp.strftime('%Y-%m-%d')

        elif date_scope == 'to_beginning_of_fiscalyear':
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)['date_from'] - relativedelta(days=1)
            date_to = date_tmp.strftime('%Y-%m-%d')
            date_from = None

        elif date_scope == 'previous_tax_period':
            eve_of_date_from = fields.Date.from_string(options['date']['date_from']) - relativedelta(days=1)
            date_from, date_to = self.env.company._get_tax_closing_period_boundaries(eve_of_date_from)

        return date_from, date_to, allow_include_initial_balance


    ####################################################
    # OPTIONS: analytic filter
    ####################################################

    def _init_options_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return


        if self.user_has_groups('analytic.group_analytic_accounting'):
            previous_analytic_accounts = (previous_options or {}).get('analytic_accounts', [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False).search([('id', 'in', analytic_account_ids)])

            options['display_analytic'] = True
            options['analytic_accounts'] = selected_analytic_accounts.ids
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

    ####################################################
    # OPTIONS: partners
    ####################################################

    def _init_options_partner(self, options, previous_options=None):
        if not self.filter_partner:
            return

        options['partner'] = True
        previous_partner_ids = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []

        selected_partner_ids = [int(partner) for partner in previous_partner_ids]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_partners = selected_partner_ids and self.env['res.partner'].with_context(active_test=False).search([('id', 'in', selected_partner_ids)]) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('name')
        options['partner_ids'] = selected_partners.ids

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
        if not options.get('all_entries'):
            return [('parent_state', '=', 'posted')]
        else:
            return [('parent_state', '!=', 'cancel')]

    ####################################################
    # OPTIONS: not reconciled entries
    ####################################################
    def _init_options_reconciled(self, options, previous_options=None):
        if self.filter_unreconciled and previous_options:
            options['unreconciled'] = previous_options.get('unreconciled', False)
        else:
            options['unreconciled'] = False

    @api.model
    def _get_options_unreconciled_domain(self, options):
        if options.get('unreconciled'):
            return ['&', ('full_reconcile_id', '=', False), ('balance', '!=', '0')]
        return []

    ####################################################
    # OPTIONS: account_type
    ####################################################

    def _init_options_account_type(self, options, previous_options=None):
        '''
        Initialize a filter based on the account_type of the line (trade/non trade, payable/receivable).
        Selects a name to display according to the selections.
        The group display name is selected according to the display name of the options selected.
        '''
        if self.filter_account_type in ('disabled', False):
            return

        account_type_list = [
            {'id': 'trade_receivable', 'name': _("Receivable"), 'selected': True},
            {'id': 'non_trade_receivable', 'name': _("Non Trade Receivable"), 'selected': False},
            {'id': 'trade_payable', 'name': _("Payable"), 'selected': True},
            {'id': 'non_trade_payable', 'name': _("Non Trade Payable"), 'selected': False},
        ]

        if self.filter_account_type == 'receivable':
            options['account_type'] = account_type_list[:2]
        elif self.filter_account_type == 'payable':
            options['account_type'] = account_type_list[2:]
        else:
            options['account_type'] = account_type_list

        if previous_options and previous_options.get('account_type'):
            previously_selected_ids = {x['id'] for x in previous_options['account_type'] if x.get('selected')}
            for opt in options['account_type']:
                opt['selected'] = opt['id'] in previously_selected_ids


    @api.model
    def _get_options_account_type_domain(self, options):
        all_domains = []
        selected_domains = []
        if not options.get('account_type') or len(options.get('account_type')) == 0:
            return []
        for opt in options.get('account_type', []):
            if opt['id'] == 'trade_receivable':
                domain = [('account_id.non_trade', '=', False), ('account_id.account_type', '=', 'asset_receivable')]
            elif opt['id'] == 'trade_payable':
                domain = [('account_id.non_trade', '=', False), ('account_id.account_type', '=', 'liability_payable')]
            elif opt['id'] == 'non_trade_receivable':
                domain = [('account_id.non_trade', '=', True), ('account_id.account_type', '=', 'asset_receivable')]
            elif opt['id'] == 'non_trade_payable':
                domain = [('account_id.non_trade', '=', True), ('account_id.account_type', '=', 'liability_payable')]
            if opt['selected']:
                selected_domains.append(domain)
            all_domains.append(domain)
        return osv.expression.OR(selected_domains or all_domains)

    ####################################################
    # OPTIONS: order column
    ####################################################

    @api.model
    def _init_options_order_column(self, options, previous_options=None):
        # options['order_column'] is in the form {'expression_label': expression label of the column to order, 'direction': the direction order ('ASC' or 'DESC')}
        options['order_column'] = None

        previous_value = previous_options and previous_options.get('order_column')
        if previous_value:
            for col in options['columns']:
                if col['sortable'] and col['expression_label'] == previous_value['expression_label']:
                    options['order_column'] = previous_value
                    break

    ####################################################
    # OPTIONS: hierarchy
    ####################################################

    def _init_options_hierarchy(self, options, previous_options=None):
        company_ids = self.get_report_company_ids(options)
        if self.filter_hierarchy != 'never' and self.env['account.group'].search(self.env['account.group']._check_company_domain(company_ids), limit=1):
            options['display_hierarchy_filter'] = True
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy == 'by_default'
        else:
            options['hierarchy'] = False
            options['display_hierarchy_filter'] = False

    @api.model
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        if not lines:
            return lines

        def get_account_group_hierarchy(account):
            # Create codes path in the hierarchy based on account.
            groups = self.env['account.group']
            if account.group_id:
                group = account.group_id
                while group:
                    groups += group
                    group = group.parent_id
            return list(groups.sorted(reverse=True))

        def create_hierarchy_line(account_group, column_totals, level, parent_id):
            line_id = self._get_generic_line_id('account.group', account_group.id if account_group else 0, parent_line_id=parent_id)
            unfolded = line_id in options.get('unfolded_lines') or options['unfold_all']
            name = account_group.display_name if account_group else _('(No Group)')
            columns = []
            for column_total, column in zip(column_totals, options['columns']):
                columns.append(self._build_column_dict(column_total, column, options=options))
            return {
                'id': line_id,
                'name': name,
                'title_hover': name,
                'unfoldable': True,
                'unfolded': unfolded,
                'level': level,
                'parent_id': parent_id,
                'columns': columns,
            }

        def compute_group_totals(line, group=None):
            return [
                hierarchy_total + (column.get('no_format') or 0.0) if isinstance(hierarchy_total, float) else hierarchy_total
                for hierarchy_total, column
                in zip(hierarchy[group]['totals'], line['columns'])
            ]

        def render_lines(account_groups, current_level, parent_line_id, skip_no_group=True):
            to_treat = [(current_level, parent_line_id, group) for group in account_groups.sorted()]

            if None in hierarchy and not skip_no_group:
                to_treat.append((current_level, parent_line_id, None))

            while to_treat:
                level_to_apply, parent_id, group = to_treat.pop(0)
                group_data = hierarchy[group]
                hierarchy_line = create_hierarchy_line(group, group_data['totals'], level_to_apply, parent_id)
                new_lines.append(hierarchy_line)
                treated_child_groups = self.env['account.group']

                for account_line in group_data['lines']:
                    for child_group in group_data['child_groups']:
                        if child_group not in treated_child_groups and child_group['code_prefix_end'] < account_line['name']:
                            render_lines(child_group, hierarchy_line['level'] + 1, hierarchy_line['id'])
                            treated_child_groups += child_group

                    markup, model, account_id = self._parse_line_id(account_line['id'])[-1]
                    account_line_id = self._get_generic_line_id(model, account_id, markup=markup, parent_line_id=hierarchy_line['id'])
                    account_line.update({
                        'id': account_line_id,
                        'parent_id': hierarchy_line['id'],
                        'level': hierarchy_line['level'] + 1,
                    })
                    new_lines.append(account_line)

                    for child_line in account_line_children_map[account_id]:
                        markup, model, res_id = self._parse_line_id(child_line['id'])[-1]
                        child_line.update({
                            'id': self._get_generic_line_id(model, res_id, markup=markup, parent_line_id=account_line_id),
                            'parent_id': account_line_id,
                            'level': account_line['level'] + 1,
                        })
                        new_lines.append(child_line)

                to_treat = [
                    (level_to_apply + 1, hierarchy_line['id'], child_group)
                    for child_group
                    in group_data['child_groups'].sorted()
                    if child_group not in treated_child_groups
                ] + to_treat

        def create_hierarchy_dict():
            return defaultdict(lambda: {
                'lines': [],
                'totals': [('' if column.get('figure_type') == 'string' else 0.0) for column in options['columns']],
                'child_groups': self.env['account.group'],
            })

        new_lines, total_lines = [], []

        # root_line_id is the id of the parent line of the lines we want to render
        root_line_id = self._build_parent_line_id(self._parse_line_id(lines[0]['id'])) or None
        last_account_line_id = account_id = None
        current_level = 0
        account_line_children_map = defaultdict(list)
        account_groups = self.env['account.group']
        root_account_groups = self.env['account.group']
        hierarchy = create_hierarchy_dict()

        for line in lines:
            markup, res_model, model_id = self._parse_line_id(line['id'])[-1]

            # Account lines are used as the basis for the computation of the hierarchy.
            if res_model == 'account.account':
                last_account_line_id = line['id']
                current_level = line['level']
                account_id = model_id
                account = self.env[res_model].browse(account_id)
                account_groups = get_account_group_hierarchy(account)

                if not account_groups:
                    hierarchy[None]['lines'].append(line)
                    hierarchy[None]['totals'] = compute_group_totals(line)
                else:
                    for i, group in enumerate(account_groups):
                        if i == 0:
                            hierarchy[group]['lines'].append(line)
                        if i == len(account_groups) - 1 and group not in root_account_groups:
                            root_account_groups += group
                        if group.parent_id and group not in hierarchy[group.parent_id]['child_groups']:
                            hierarchy[group.parent_id]['child_groups'] += group

                        hierarchy[group]['totals'] = compute_group_totals(line, group=group)

            # This is not an account line, so we check to see if it is a descendant of the last account line.
            # If so, it is added to the mapping of the lines that are related to this account.
            elif last_account_line_id and line.get('parent_id', '').startswith(last_account_line_id):
                account_line_children_map[account_id].append(line)

            # This is a total line that is not linked to an account. It is saved in order to be added at the end.
            elif markup == 'total':
                total_lines.append(line)

            # This line ends the scope of the current hierarchy and is (possibly) the root of a new hierarchy.
            # We render the current hierarchy and set up to build a new hierarchy
            else:
                render_lines(root_account_groups, current_level, root_line_id, skip_no_group=False)

                new_lines.append(line)

                # Reset the hierarchy-related variables for a new hierarchy
                root_line_id = line['id']
                last_account_line_id = account_id = None
                current_level = 0
                account_line_children_map = defaultdict(list)
                root_account_groups = self.env['account.group']
                account_groups = self.env['account.group']
                hierarchy = create_hierarchy_dict()

        render_lines(root_account_groups, current_level, root_line_id, skip_no_group=False)

        return new_lines + total_lines

    ####################################################
    # OPTIONS: prefix groups threshold
    ####################################################

    def _init_options_prefix_groups_threshold(self, options, previous_options=None):
        previous_threshold = (previous_options or {}).get('prefix_groups_threshold')
        options['prefix_groups_threshold'] = previous_threshold or self.prefix_groups_threshold

    ####################################################
    # OPTIONS: fiscal position (multi vat)
    ####################################################

    def _init_options_fiscal_position(self, options, previous_options=None):
        if self.filter_fiscal_position and self.country_id and len(options['companies']) == 1:
            vat_fpos_domain = [
                *self.env['account.fiscal.position']._check_company_domain(next(comp_id for comp_id in self.get_report_company_ids(options))),
                ('foreign_vat', '!=', False),
            ]

            vat_fiscal_positions = self.env['account.fiscal.position'].search([
                *vat_fpos_domain,
                ('country_id', '=', self.country_id.id),
            ])

            options['allow_domestic'] = self.env.company.account_fiscal_country_id == self.country_id

            accepted_prev_vals = {*vat_fiscal_positions.ids}
            if options['allow_domestic']:
                accepted_prev_vals.add('domestic')
            if len(vat_fiscal_positions) > (0 if options['allow_domestic'] else 1) or not accepted_prev_vals:
                accepted_prev_vals.add('all')

            if previous_options and previous_options.get('fiscal_position') in accepted_prev_vals:
                # Legit value from previous options; keep it
                options['fiscal_position'] = previous_options['fiscal_position']
            elif len(vat_fiscal_positions) == 1 and not options['allow_domestic']:
                # Only one foreign fiscal position: always select it, menu will be hidden
                options['fiscal_position'] = vat_fiscal_positions.id
            else:
                # Multiple possible values; by default, show the values of the company's area (if allowed), or everything
                options['fiscal_position'] = options['allow_domestic'] and 'domestic' or 'all'
        else:
            # No country, or we're displaying data from several companies: disable fiscal position filtering
            vat_fiscal_positions = []
            options['allow_domestic'] = True
            previous_fpos = previous_options and previous_options.get('fiscal_position')
            options['fiscal_position'] = previous_fpos if previous_fpos in ('all', 'domestic') else 'all'

        options['available_vat_fiscal_positions'] = [{
            'id': fiscal_pos.id,
            'name': fiscal_pos.name,
            'company_id': fiscal_pos.company_id.id,
        } for fiscal_pos in vat_fiscal_positions]

    def _get_options_fiscal_position_domain(self, options):
        def get_foreign_vat_tax_tag_extra_domain(fiscal_position=None):
            # We want to gather any line wearing a tag, whatever its fiscal position.
            # Nevertheless, if a country is using the same report for several regions (e.g. India) we need to exclude
            # the lines from the other regions to avoid reporting numbers that don't belong to the current region.
            fp_ids_to_exclude = self.env['account.fiscal.position'].search([
                ('id', '!=', fiscal_position.id if fiscal_position else False),
                ('foreign_vat', '!=', False),
                ('country_id', '=', self.env.company.account_fiscal_country_id.id),
            ]).ids

            if fiscal_position and fiscal_position.country_id == self.env.company.account_fiscal_country_id:
                # We are looking for a fiscal position inside our country which means we need to exclude
                # the local fiscal position which is represented by `False`.
                fp_ids_to_exclude.append(False)

            return [
                ('tax_tag_ids.country_id', '=', self.country_id.id),
                ('move_id.fiscal_position_id', 'not in', fp_ids_to_exclude),
            ]

        fiscal_position_opt = options.get('fiscal_position')

        if fiscal_position_opt == 'domestic':
            domain = [
                '|',
                ('move_id.fiscal_position_id', '=', False),
                ('move_id.fiscal_position_id.foreign_vat', '=', False),
            ]
            tax_tag_domain = get_foreign_vat_tax_tag_extra_domain()
            return osv.expression.OR([domain, tax_tag_domain])

        if isinstance(fiscal_position_opt, int):
            # It's a fiscal position id
            domain = [('move_id.fiscal_position_id', '=', fiscal_position_opt)]
            fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position_opt)
            tax_tag_domain = get_foreign_vat_tax_tag_extra_domain(fiscal_position)
            return osv.expression.OR([domain, tax_tag_domain])

        # 'all', or option isn't specified
        return []

    ####################################################
    # OPTIONS: MULTI COMPANY
    ####################################################

    def _init_options_companies(self, options, previous_options=None):
        if self.filter_multi_company == 'selector':
            companies = self.env.companies
        elif self.filter_multi_company == 'tax_units':
            companies = self._multi_company_tax_units_init_options(options, previous_options=previous_options)
        else:
            # Multi-company is disabled for this report ; only accept the sub-branches of the current company from the selector
            companies = self.env.company._accessible_branches()

        options['companies'] = [{'name': c.name, 'id': c.id, 'currency_id': c.currency_id.id} for c in companies]

    def _multi_company_tax_units_init_options(self, options, previous_options=None):
        """ Initializes the companies option for reports configured to compute it from tax units.
        """
        tax_units_domain = [('company_ids', 'in', self.env.company.id)]

        if self.country_id:
            tax_units_domain.append(('country_id', '=', self.country_id.id))

        available_tax_units = self.env['account.tax.unit'].search(tax_units_domain)

        # Filter available units to only consider the ones whose companies are all accessible to the user
        available_tax_units = available_tax_units.filtered(
            lambda x: all(unit_company in self.env.user.company_ids for unit_company in x.sudo().company_ids)
            # sudo() to avoid bypassing companies the current user does not have access to
        )

        options['available_tax_units'] = [{
            'id': tax_unit.id,
            'name': tax_unit.name,
            'company_ids': tax_unit.company_ids.ids
        } for tax_unit in available_tax_units]

        # Available tax_unit option values that are currently allowed by the company selector
        # A js hack ensures the page is reloaded and the selected companies modified
        # when clicking on a tax unit option in the UI, so we don't need to worry about that here.
        companies_authorized_tax_unit_opt = {
            *(available_tax_units.filtered(lambda x: set(self.env.companies) == set(x.company_ids)).ids),
            'company_only'
        }

        if previous_options and previous_options.get('tax_unit') in companies_authorized_tax_unit_opt:
            options['tax_unit'] = previous_options['tax_unit']

        else:
            # No tax_unit gotten from previous options; initialize it
            # A tax_unit will be set by default if only one tax unit is available for the report
            # (which should always be true for non-generic reports, which have a country), and the companies of
            # the unit are the only ones currently selected.
            if companies_authorized_tax_unit_opt == {'company_only'}:
                options['tax_unit'] = 'company_only'
            elif len(available_tax_units) == 1 and available_tax_units[0].id in companies_authorized_tax_unit_opt:
                options['tax_unit'] = available_tax_units[0].id
            else:
                options['tax_unit'] = 'company_only'

        # Finally initialize multi_company filter
        if options['tax_unit'] == 'company_only':
            companies = self.env.company._get_branches_with_same_vat(accessible_only=True)
        else:
            tax_unit = available_tax_units.filtered(lambda x: x.id == options['tax_unit'])
            companies = tax_unit.company_ids

        return companies

    ####################################################
    # OPTIONS: MULTI CURRENCY
    ####################################################
    def _init_options_multi_currency(self, options, previous_options=None):
        options['multi_currency'] = (
            any([company.get('currency_id') != options['companies'][0].get('currency_id') for company in options['companies']])
            or any([column.figure_type != 'monetary' for column in self.column_ids])
            or any(expression.figure_type and expression.figure_type != 'monetary' for expression in self.line_ids.expression_ids)
        )

    ####################################################
    # OPTIONS: ROUNDING UNIT
    ####################################################
    def _init_options_rounding_unit(self, options, previous_options=None):
        default = 'decimals'

        if previous_options:
            options['rounding_unit'] = previous_options.get('rounding_unit', default)
        else:
            options['rounding_unit'] = default

        options['rounding_unit_names'] = self._get_rounding_unit_names()

    def _get_rounding_unit_names(self):
        currency_symbol = self.env.company.currency_id.symbol
        rounding_unit_names = [
            ('decimals', '.%s' % currency_symbol),
            ('units', '%s' % currency_symbol),
            ('thousands', 'K%s' % currency_symbol),
            ('millions', 'M%s' % currency_symbol),
        ]

        # We want to add 'lakhs' for Indian Rupee
        if (self.env.company.currency_id == self.env.ref('base.INR')):
            # We want it between 'thousands' and 'millions'
            rounding_unit_names.insert(3, ('lakhs', 'L%s' % currency_symbol))

        return dict(rounding_unit_names)

    # ####################################################
    # OPTIONS: ALL ENTRIES
    ####################################################
    def _init_options_all_entries(self, options, previous_options=None):
        if self.filter_show_draft and previous_options:
            options['all_entries'] = previous_options.get('all_entries', False)
        else:
            options['all_entries'] = False

    ####################################################
    # OPTIONS: UNFOLDED LINES
    ####################################################
    def _init_options_unfolded(self, options, previous_options=None):
        if previous_options is None:
            previous_options = {}

        options['unfold_all'] = self.filter_unfold_all and previous_options.get('unfold_all', False)

        previous_section_source_id = previous_options.get('sections_source_id')
        if previous_options and (not previous_section_source_id or previous_section_source_id == options['sections_source_id']):
            # Only keep the unfolded lines if they belong to the same report or a section of the same report
            options['unfolded_lines'] = previous_options.get('unfolded_lines', [])
        else:
            options['unfolded_lines'] = []

    ####################################################
    # OPTIONS: HIDE LINE AT 0
    ####################################################
    def _init_options_hide_0_lines(self, options, previous_options=None):
        if self.filter_hide_0_lines != 'never':
            previous_val = (previous_options or {}).get('hide_0_lines')
            if previous_val is not None:
                options['hide_0_lines'] = previous_val
            else:
                options['hide_0_lines'] = self.filter_hide_0_lines == 'by_default'
        else:
            options['hide_0_lines'] = False

    def _filter_out_0_lines(self, lines):
        """ Returns a list containing all lines that are not zero or that are parent to non-zero lines.
            Can be used to ensure printed report does not include 0 lines, when hide_0_lines is toggled.
        """
        lines_to_hide = set()  # contain line ids to remove from lines
        has_visible_children = set()  # contain parent line ids
        # Traverse lines in reverse to keep track of visible parent lines required by children lines
        for line in reversed(lines):
            is_zero_line = all(col.get('is_zero', True) for col in line['columns'])
            if is_zero_line and line['id'] not in has_visible_children:
                lines_to_hide.add(line['id'])
            if line.get('parent_id') and line['id'] not in lines_to_hide:
                has_visible_children.add(line['parent_id'])
        return list(filter(lambda x: x['id'] not in lines_to_hide, lines))

    ####################################################
    # OPTIONS: HORIZONTAL GROUP
    ####################################################
    def _init_options_horizontal_groups(self, options, previous_options=None):
        options['available_horizontal_groups'] = [
            {
                'id': horizontal_group.id,
                'name': horizontal_group.name,
            }
            for horizontal_group in self.horizontal_group_ids
        ]
        previous_selected = (previous_options or {}).get('selected_horizontal_group_id')
        options['selected_horizontal_group_id'] = previous_selected if previous_selected in self.horizontal_group_ids.ids else None

    ####################################################
    # OPTIONS: SEARCH BAR
    ####################################################
    def _init_options_search_bar(self, options, previous_options=None):
        if self.search_bar:
            options['search_bar'] = True
            if 'default_filter_accounts' not in self._context and previous_options and 'filter_search_bar' in previous_options:
                options['filter_search_bar'] = previous_options['filter_search_bar']

    ####################################################
    # OPTIONS: COLUMN HEADERS
    ####################################################

    def _init_options_column_headers(self, options, previous_options=None):
        # Prepare column headers
        all_comparison_date_vals = [options['date']] + options.get('comparison', {}).get('periods', [])
        column_headers = [
            [
                {
                    'name': comparison_date_vals['string'],
                    'forced_options': {'date': comparison_date_vals},
                }
                for comparison_date_vals in all_comparison_date_vals
            ], # First level always consists of date comparison. Horizontal groupby are done on following levels.
        ]

        # Handle horizontal groups
        selected_horizontal_group_id = options.get('selected_horizontal_group_id')
        if selected_horizontal_group_id:
            horizontal_group = self.env['account.report.horizontal.group'].browse(selected_horizontal_group_id)

            for field_name, records in horizontal_group._get_header_levels_data():
                header_level = [
                    {
                        'name': record.display_name,
                        'horizontal_groupby_element': {field_name: record.id},
                    }
                    for record in records
                ]
                column_headers.append(header_level)

        options['column_headers'] = column_headers

    ####################################################
    # OPTIONS: COLUMNS
    ####################################################
    def _init_options_columns(self, options, previous_options=None):
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}
        all_column_group_vals_in_order = self._generate_columns_group_vals_recursively(options['column_headers'], default_group_vals)

        columns, column_groups = self._build_columns_from_column_group_vals(options, all_column_group_vals_in_order)

        options['columns'] = columns
        options['column_groups'] = column_groups
        # Debug column is only shown when there is a single column group, so that we can display all the subtotals of the line in a clear way
        options['show_debug_column'] = options['export_mode'] != 'print' \
                                       and self.user_has_groups('base.group_no_one') \
                                       and len(options['column_groups']) == 1 \
                                       and len(self.line_ids) > 0 # No debug column on fully dynamic reports by default (they can customize this)

    def _generate_columns_group_vals_recursively(self, next_levels_headers, previous_levels_group_vals):
        if next_levels_headers:
            rslt = []
            for header_element in next_levels_headers[0]:
                current_level_group_vals = {}
                for key in previous_levels_group_vals:
                    current_level_group_vals[key] = {**previous_levels_group_vals.get(key, {}), **header_element.get(key, {})}

                rslt += self._generate_columns_group_vals_recursively(next_levels_headers[1:], current_level_group_vals)
            return rslt
        else:
            return [previous_levels_group_vals]

    def _build_columns_from_column_group_vals(self, options, all_column_group_vals_in_order):
        def _generate_domain_from_horizontal_group_hash_key_tuple(group_hash_key):
            domain = []
            for field_name, field_value in group_hash_key:
                domain.append((field_name, '=', field_value))
            return domain

        columns = []
        column_groups = {}
        for column_group_val in all_column_group_vals_in_order:
            horizontal_group_key_tuple = self._get_dict_hashable_key_tuple(column_group_val['horizontal_groupby_element']) # Empty tuple if no grouping
            column_group_key = str(self._get_dict_hashable_key_tuple(column_group_val)) # Unique identifier for the column group

            column_groups[column_group_key] = {
                'forced_options': column_group_val['forced_options'],
                'forced_domain': _generate_domain_from_horizontal_group_hash_key_tuple(horizontal_group_key_tuple),
            }

            for report_column in self.column_ids:
                columns.append({
                    'name': report_column.name,
                    'column_group_key': column_group_key,
                    'expression_label': report_column.expression_label,
                    'sortable': report_column.sortable,
                    'figure_type': report_column.figure_type,
                    'blank_if_zero': report_column.blank_if_zero,
                    'style': "text-align: center; white-space: nowrap;",
                })

        return columns, column_groups

    def _get_dict_hashable_key_tuple(self, dict_to_convert):
        rslt = []
        for key, value in sorted(dict_to_convert.items()):
            if isinstance(value, dict):
                value = self._get_dict_hashable_key_tuple(value)
            rslt.append((key, value))
        return tuple(rslt)

    ####################################################
    # OPTIONS: BUTTONS
    ####################################################

    def action_open_report_form(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.report',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': self.id,
        }

    def _init_options_buttons(self, options, previous_options=None):
        options['buttons'] = [
            {'name': _('PDF'), 'sequence': 10, 'action': 'export_file', 'action_param': 'export_to_pdf', 'file_export_type': _('PDF'), 'branch_allowed': True},
            {'name': _('XLSX'), 'sequence': 20, 'action': 'export_file', 'action_param': 'export_to_xlsx', 'file_export_type': _('XLSX'), 'branch_allowed': True},
            {'name': _('Save'), 'sequence': 100, 'action': 'open_report_export_wizard'},
        ]

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        self.ensure_one()
        new_context = {
            **self._context,
            'account_report_generation_options': options,
            'default_report_id': self.id,
        }
        view_id = self.env.ref('account_reports.view_report_export_wizard').id

        # We have to create it before returning the action (and not just use a record in 'new' state), so that we can create
        # the transient records used in the m2m for the different export formats.
        new_wizard = self.with_context(new_context).env['account_reports.export.wizard'].create({'report_id': self.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'account_reports.export.wizard',
            'res_id': new_wizard.id,
            'target': 'new',
            'views': [[view_id, 'form']],
            'context': new_context,
        }

    def open_account_report_file_download_error_wizard(self, errors, content):
        self.ensure_one()

        model = 'account.report.file.download.error.wizard'
        vals = {'file_generation_errors': json.dumps(errors)}

        if content:
            vals['file_name'] = content['file_name']
            vals['file_content'] = base64.b64encode(re.sub(r'\n\s*\n', '\n', content['file_content']).encode())

        return {
            'type': 'ir.actions.act_window',
            'res_model': model,
            'res_id': self.env[model].create(vals).id,
            'target': 'new',
            'views': [(False, 'form')],
        }

    def get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'xml': 'application/xml',
            'xaf': 'application/vnd.sun.xml.writer',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
        }
        return type_mapping.get(file_type, False)

    def _init_options_section_buttons(self, options, previous_options=None):
        """ In case we're displaying a section, we want to replace its buttons by its source report's. This needs to be done last, after calling the
        custom handler, to avoid its _custom_options_initializer function to generate additional buttons.
        """
        if options['sections_source_id'] != self.id:
            # We need to re-call a full get_options in case a custom options initializer adds new buttons depending on other options.
            # This way, we're sure we always get all buttons that are needed.
            sections_source = self.env['account.report'].browse(options['sections_source_id'])
            options['buttons'] = sections_source.get_options(previous_options={**options, 'no_report_reroute': True})['buttons']

    ####################################################
    # OPTIONS: VARIANTS
    ####################################################
    def _init_options_variants(self, options, previous_options=None):
        allowed_variant_ids = set()

        previous_section_source_id = (previous_options or {}).get('sections_source_id')
        if previous_section_source_id:
            previous_section_source = self.env['account.report'].browse(previous_section_source_id)
            if self in previous_section_source.section_report_ids:
                options['variants_source_id'] = (previous_section_source.root_report_id or previous_section_source).id
                allowed_variant_ids.add(previous_section_source_id)

        if 'variants_source_id' not in options:
            options['variants_source_id'] = (self.root_report_id or self).id

        available_variants = self.env['account.report']
        options['has_inactive_variants'] = False
        allowed_country_variant_ids = {}
        all_variants = self._get_variants(options['variants_source_id'])
        for variant in all_variants.filtered(lambda x: x._is_available_for(options)):
            if not self.root_report_id and variant != self and variant.active: # Non-route reports don't reroute the variant when computing their options
                allowed_variant_ids.add(variant.id)
                if variant.country_id:
                    allowed_country_variant_ids.setdefault(variant.country_id.id, []).append(variant.id)

            if variant.active:
                available_variants += variant
            else:
                options['has_inactive_variants'] = True

        options['available_variants'] = [
            {
                'id': variant.id,
                'name': variant.display_name,
                'country_id': variant.country_id.id,  # To ease selection of default variant to open, without needing browsing again
            }
            for variant in sorted(available_variants, key=lambda x: (x.country_id and 1 or 0, x.sequence, x.id))
        ]

        previous_opt_report_id = (previous_options or {}).get('selected_variant_id')
        if previous_opt_report_id in allowed_variant_ids or previous_opt_report_id == self.id:
            options['selected_variant_id'] = previous_opt_report_id
        elif allowed_country_variant_ids:
            country_id = self.env.company.account_fiscal_country_id.id
            report_id = (allowed_country_variant_ids.get(country_id) or next(iter(allowed_country_variant_ids.values())))[0]
            options['selected_variant_id'] = report_id
        else:
            options['selected_variant_id'] = self.id

    def _get_variants(self, report_id):
        source_report = self.env['account.report'].browse(report_id)
        if source_report.root_report_id:
            # We need to get the root report in order to get all variants
            source_report = source_report.root_report_id
        return source_report + source_report.with_context(active_test=False).variant_report_ids

    ####################################################
    # OPTIONS: SECTIONS
    ####################################################
    def _init_options_sections(self, options, previous_options=None):
        if options.get('selected_variant_id'):
            options['sections_source_id'] = options['selected_variant_id']
        else:
            options['sections_source_id'] = self.id

        source_report = self.env['account.report'].browse(options['sections_source_id'])

        available_sections = source_report.section_report_ids if source_report.use_sections else self.env['account.report']
        options['sections'] = [{'name': section.name, 'id': section.id} for section in available_sections]

        if available_sections:
            section_id = (previous_options or {}).get('selected_section_id')
            if not section_id or section_id not in available_sections.ids:
                section_id = available_sections[0].id

            options['selected_section_id'] = section_id

        options['has_inactive_sections'] = bool(self.env['account.report'].with_context(active_test=False).search_count([
                ('section_main_report_ids', 'in', options['sections_source_id']),
                ('active', '=', False)
        ]))

    ####################################################
    # OPTIONS: REPORT_ID
    ####################################################
    def _init_options_report_id(self, options, previous_options=None):
        if (previous_options or {}).get('no_report_reroute'):
            # Used for exports
            options['report_id'] = self.id
        else:
            options['report_id'] = options.get('selected_section_id') or options.get('selected_variant_id') or self.id


    ####################################################
    # OPTIONS: EXPORT MODE
    ####################################################
    def _init_options_export_mode(self, options, previous_options=None):
        options['export_mode'] = (previous_options or {}).get('export_mode')

    ####################################################
    # OPTIONS: CUSTOM
    ####################################################
    def _init_options_custom(self, options, previous_options=None):
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model:
            self.env[custom_handler_model]._custom_options_initializer(self, options, previous_options)

    ####################################################
    # OPTIONS: INTEGER ROUNDING
    ####################################################
    def _custom_options_add_integer_rounding(self, options, integer_rounding, previous_options=None):
        """ Helper function to be called in a _custom_options_initializer by reports needing to use the integer_rounding feature.
        This was introduced as an improvement in stable and will become a proper _init_options in master, together with a new field on the report.
        """
        options['integer_rounding'] = integer_rounding
        if options.get('export_mode') == 'file':
            options['integer_rounding_enabled'] = True
        else:
            options['integer_rounding_enabled'] = (previous_options or {}).get('integer_rounding_enabled', True)
        return options

    ####################################################
    # OPTIONS: CORE
    ####################################################

    def get_options(self, previous_options=None):
        self.ensure_one()

        initializers_in_sequence = self._get_options_initializers_in_sequence()
        options = {}

        if (previous_options or {}).get('_running_export_test'):
            options['_running_export_test'] = True

        # We need report_id to be initialized. Compute the necessary options to check for reroute.
        for reroute_initializer_index, initializer in enumerate(initializers_in_sequence):
            initializer(options, previous_options=previous_options)

            # pylint: disable=W0143
            if initializer == self._init_options_report_id:
                break

        # Stop the computation to check for reroute once we have computed the necessary information
        if (not self.root_report_id or (self.use_sections and self.section_report_ids)) and options['report_id'] != self.id:
            # Load the variant/section instead of the root report
            variant_options = {**(previous_options or {})}
            for reroute_opt_key in ('selected_variant_id', 'selected_section_id', 'variants_source_id', 'sections_source_id'):
                opt_val = options.get(reroute_opt_key)
                if opt_val:
                    variant_options[reroute_opt_key] = opt_val

            return self.env['account.report'].browse(options['report_id']).get_options(variant_options)

        # No reroute; keep on and compute the other options
        for initializer_index in range(reroute_initializer_index + 1, len(initializers_in_sequence)):
            initializer = initializers_in_sequence[initializer_index]
            initializer(options, previous_options=previous_options)

        # Sort the buttons list by sequence, for rendering
        options_companies = self.env['res.company'].browse(self.get_report_company_ids(options))
        if not options_companies._all_branches_selected():
            for button in filter(lambda x: not x.get('branch_allowed'), options['buttons']):
                button['disabled'] = True

        options['buttons'] = sorted(options['buttons'], key=lambda x: x.get('sequence', 90))

        return options

    def _get_options_initializers_in_sequence(self):
        """ Gets all filters in the right order to initialize them, so that each filter is
        guaranteed to be after all of its dependencies in the resulting list.

        :return: a list of initializer functions, each accepting two parameters:
            - options (mandatory): The options dictionary to be modified by this initializer to include its related option's data

            - previous_options (optional, defaults to None): A dict with default options values, coming from a previous call to the report.
                                                             These values can be considered or ignored on a case-by-case basis by the initializer,
                                                             depending on functional needs.
        """
        initializer_prefix = '_init_options_'
        initializers = [
            getattr(self, attr) for attr in dir(self)
            if attr.startswith(initializer_prefix)
        ]

        # Order them in a dependency-compliant way
        forced_sequence_map = self._get_options_initializers_forced_sequence_map()
        initializers.sort(key=lambda x: forced_sequence_map.get(x, forced_sequence_map.get('default')))

        return initializers

    def _get_options_initializers_forced_sequence_map(self):
        """ By default, not specific order is ensured for the filters when calling _get_options_initializers_in_sequence.
        This function allows giving them a sequence number. It can be overridden
        to make filters depend on each other.

        :return: dict(str, int): str is the filter name, int is its sequence (lowest = first).
                                 Multiple filters may share the same sequence, their relative order is then not guaranteed.
        """
        return {
            self._init_options_companies: 10,
            self._init_options_variants: 15,
            self._init_options_sections: 16,
            self._init_options_report_id: 17,
            self._init_options_fiscal_position: 20,
            self._init_options_date: 30,
            self._init_options_horizontal_groups: 40,
            self._init_options_comparison: 50,

            'default': 200,

            self._init_options_column_headers: 990,
            self._init_options_columns: 1000,
            self._init_options_growth_comparison: 1010,
            self._init_options_order_column: 1020,
            self._init_options_hierarchy: 1030,
            self._init_options_prefix_groups_threshold: 1040,
            self._init_options_custom: 1050,
            self._init_options_section_buttons: 1060,
        }

    def _get_options_domain(self, options, date_scope):
        self.ensure_one()

        available_scopes = dict(self.env['account.report.expression']._fields['date_scope'].selection)
        if date_scope and date_scope not in available_scopes: # date_scope can be passed to None explicitly to ignore the dates
            raise UserError(_("Unknown date scope: %s", date_scope))

        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('company_id', 'in', self.get_report_company_ids(options)),
        ]
        domain += self._get_options_journals_domain(options)
        if date_scope:
            domain += self._get_options_date_domain(options, date_scope)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        domain += self._get_options_unreconciled_domain(options)
        domain += self._get_options_fiscal_position_domain(options)
        domain += self._get_options_account_type_domain(options)
        domain += self._get_options_aml_ir_filters(options)

        if self.only_tax_exigible:
            domain += self.env['account.move.line']._get_tax_exigible_domain()

        return domain

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _query_get(self, options, date_scope, domain=None):
        domain = self._get_options_domain(options, date_scope) + (domain or [])

        if options.get('forced_domain'):
            # That option key is set when splitting options between column groups
            domain += options['forced_domain']

        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query.get_sql()

    ####################################################
    # LINE IDS MANAGEMENT HELPERS
    ####################################################
    def _get_generic_line_id(self, model_name, value, markup='', parent_line_id=None):
        """ Generates a generic line id from the provided parameters.

        Such a generic id consists of a string repeating 1 to n times the following pattern:
        markup-model-value, each occurence separated by a LINE_ID_HIERARCHY_DELIMITER character from the previous one.

        Each pattern corresponds to a level of hierarchy in the report, so that
        the n-1 patterns starting the id of a line actually form the id of its generator line.
        EX: a~b~c|d~e~f|g~h~i => This line is a subline generated by a~b~c|d~e~f where | is the LINE_ID_HIERARCHY_DELIMITER.

        Each pattern consists of the three following elements:
        - markup:  a (possibly empty) string allowing finer identification of the line
                   (like the name of the field for account.accounting.reports)

        - model:   the model this line has been generated for, or an empty string if there is none

        - value:   the groupby value for this line (typically the id of a record
                   or the value of a field), or an empty string if there isn't any.
        """
        self.ensure_one()

        if parent_line_id:
            parent_id_list = self._parse_line_id(parent_line_id)
        else:
            parent_id_list = [(None, 'account.report', self.id)]

        return self._build_line_id(parent_id_list + [(markup, model_name, value)])

    @api.model
    def _get_model_info_from_id(self, line_id):
        """ Parse the provided generic report line id.

        :param line_id: the report line id (i.e. markup~model~value|markup2~model2~value2 where | is the LINE_ID_HIERARCHY_DELIMITER)
        :return: tuple(model, id) of the report line. Each of those values can be None if the id contains no information about them.
        """
        last_id_tuple = self._parse_line_id(line_id)[-1]
        return last_id_tuple[-2:]

    @api.model
    def _build_line_id(self, current):
        """ Build a generic line id string from its list representation, converting
        the None values for model and value to empty strings.
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        def convert_none(x):
            return x if x not in (None, False) else ''
        return LINE_ID_HIERARCHY_DELIMITER.join(f'{convert_none(markup)}~{convert_none(model)}~{convert_none(value)}' for markup, model, value in current)

    @api.model
    def _build_parent_line_id(self, current):
        """Build the parent_line id based on the current position in the report.

        For instance, if current is [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)], it will return
        markup1~account.account~5
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        return self._build_line_id(current[:-1])

    @api.model
    def _parse_line_id(self, line_id):
        """Parse the provided string line id and convert it to its list representation.
        Empty strings for model and value will be converted to None.

        For instance if line_id is markup1~account.account~5|markup2~res.partner~8 (where | is the LINE_ID_HIERARCHY_DELIMITER),
        it will return [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)]
        :param line_id (str): the generic line id to parse
        """
        return line_id and [
            # When there is a model, value is an id, so we cast it to and int. Else, we keep the original value (for groupby lines on
            # non-relational fields, for example).
            (markup, model or None, int(value) if model and value else (value or None))
            for markup, model, value in (key.split('~') for key in line_id.split(LINE_ID_HIERARCHY_DELIMITER))
        ] or []

    @api.model
    def _get_unfolded_lines(self, lines, parent_line_id):
        """ Return a list of all children lines for specified parent_line_id.
        NB: It will return the parent_line itself!

        For instance if parent_line_ids is '~account.report.line~84|groupby:currency_id~res.currency~174'
        (where | is the LINE_ID_HIERARCHY_DELIMITER), it will return every subline for this currency.
        :param lines: list of report lines
        :param parent_line_id: id of a specified line
        :return: A list of all children lines for a specified parent_line_id
        """
        return [
            line for line in lines
            if line['id'].startswith(parent_line_id)
        ]

    @api.model
    def _get_res_id_from_line_id(self, line_id, target_model_name):
        """ Parses the provided generic line id and returns the most local (i.e. the furthest on the right) record id it contains which
        corresponds to the provided model name. If line_id does not contain anything related to target_model_name, None will be returned.

        For example, parsing ~account.move~1|~res.partner~2|~account.move~3 (where | is the LINE_ID_HIERARCHY_DELIMITER)
        with target_model_name='account.move' will return 3.
        """
        dict_result = self._get_res_ids_from_line_id(line_id, [target_model_name])
        return dict_result[target_model_name] if dict_result else None


    @api.model
    def _get_res_ids_from_line_id(self, line_id, target_model_names):
        """ Parses the provided generic line id and returns the most local (i.e. the furthest on the right) record ids it contains which
        correspond to the provided model names, in the form {model_name: res_id}. If a model is not present in line_id, its model will be absent
        from the resulting dict.

        For example, parsing ~account.move~1|~res.partner~2|~account.move~3 with target_model_names=['account.move', 'res.partner'] will return
        {'account.move': 3, 'res.partner': 2}.
        """
        result = {}
        models_to_find = set(target_model_names)
        for dummy, model, value in reversed(self._parse_line_id(line_id)):
            if model in models_to_find:
                result[model] = value
                models_to_find.remove(model)

        return result

    @api.model
    def _get_markup(self, line_id):
        """ Directly returns the markup associated with the provided line_id.
        """
        return self._parse_line_id(line_id)[-1][0] if line_id else None

    def _build_subline_id(self, parent_line_id, subline_id_postfix):
        """ Creates a new subline id by concatanating parent_line_id with the provided id postfix.
        """
        return f"{parent_line_id}{LINE_ID_HIERARCHY_DELIMITER}{subline_id_postfix}"

    ####################################################
    # CARET OPTIONS MANAGEMENT
    ####################################################

    def _get_caret_options(self):
        if self.custom_handler_model_id:
            return self.env[self.custom_handler_model_name]._caret_options_initializer()
        return self._caret_options_initializer_default()

    def _caret_options_initializer_default(self):
        return {
            'account.account': [
                {'name': _("General Ledger"), 'action': 'caret_option_open_general_ledger'},
            ],

            'account.move': [
                {'name': _("View Journal Entry"), 'action': 'caret_option_open_record_form'},
            ],

            'account.move.line': [
                {'name': _("View Journal Entry"), 'action': 'caret_option_open_record_form', 'action_param': 'move_id'},
            ],

            'account.payment': [
                {'name': _("View Payment"), 'action': 'caret_option_open_record_form', 'action_param': 'payment_id'},
            ],

            'account.bank.statement': [
                {'name': _("View Bank Statement"), 'action': 'caret_option_open_statement_line_reco_widget'},
            ],

            'res.partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
            ],
        }

    def caret_option_open_record_form(self, options, params):
        model, record_id = self._get_model_info_from_id(params['line_id'])
        record = self.env[model].browse(record_id)
        target_record = record[params['action_param']] if 'action_param' in params else record

        view_id = self._resolve_caret_option_view(target_record)

        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')], # view_id will be False in case the default view is needed
            'res_model': target_record._name,
            'res_id': target_record.id,
            'context': self._context,
        }

        if view_id is not None:
            action['view_id'] = view_id

        return action

    def _get_caret_option_view_map(self):
        return {
            'account.payment': 'account.view_account_payment_form',
            'res.partner': 'base.view_partner_form',
            'account.move': 'account.view_move_form',
        }

    def _resolve_caret_option_view(self, target):
        '''Retrieve the target view of the caret option.

        :param target:  The target record of the redirection.
        :return: The id of the target view.
        '''
        view_map = self._get_caret_option_view_map()

        view_xmlid = view_map.get(target._name)
        if not view_xmlid:
            return None

        return self.env['ir.model.data']._xmlid_lookup(view_xmlid)[1]

    def caret_option_open_general_ledger(self, options, params):
        record_id = None
        # When coming from a specific account, the unfold must only be retained
        # on the specified account. Better performance and more ergonomic
        # as it opens what client asked. And "Unfold All" is 1 clic away.
        options["unfold_all"] = False
        for dummy, model, model_id in reversed(self._parse_line_id(params['line_id'])):
            if model == 'account.account':
                record_id = model_id
                break

        if record_id is None:
            raise UserError(_("'Open General Ledger' caret option is only available form report lines targetting accounts."))

        general_ledger = self.env.ref('account_reports.general_ledger_report')
        account_line_id = general_ledger._get_generic_line_id('account.account', record_id)
        account_id = self.env['account.account'].browse(record_id)
        gl_options = general_ledger.get_options(options)
        gl_options['unfolded_lines'] = [account_line_id]

        action_vals = self.env['ir.actions.actions']._for_xml_id('account_reports.action_account_report_general_ledger')
        action_vals['params'] = {
            'options': gl_options,
            'ignore_session': True,
        }
        action_vals['context'] = dict(ast.literal_eval(action_vals['context']), default_filter_accounts=account_id.code)

        return action_vals

    def caret_option_open_statement_line_reco_widget(self, options, params):
        model, record_id = self._get_model_info_from_id(params['line_id'])
        record = self.env[model].browse(record_id)
        if record._name == 'account.bank.statement.line':
            return record.action_open_recon_st_line()
        elif record._name == 'account.bank.statement':
            return record.action_open_bank_reconcile_widget()
        raise UserError(_("'View Bank Statement' caret option is only available for report lines targeting bank statements."))

    ####################################################
    # MISC
    ####################################################

    def _get_custom_handler_model(self):
        """ Check whether the current report has a custom handler and if it does, return its name.
            Otherwise, try to fall back on the root report.
        """
        return self.custom_handler_model_name or self.root_report_id.custom_handler_model_name or None

    def dispatch_report_action(self, options, action, action_param=None, on_sections_source=False):
        """ Dispatches calls made by the client to either the report itself, or its custom handler if it exists.
            The action should be a public method, by definition, but a check is made to make sure
            it is not trying to call a private method.
        """
        self.ensure_one()

        if on_sections_source:
            report_to_call = self.env['account.report'].browse(options['sections_source_id'])
            options = report_to_call.get_options(previous_options={**options, 'no_report_reroute': True})
            return report_to_call.dispatch_report_action(options, action, action_param=action_param, on_sections_source=False)

        if options['report_id'] != self.id:
            raise UserError(_("Trying to dispatch an action on a report not compatible with the provided options."))

        check_method_name(action)
        args = [options, action_param] if action_param is not None else [options]
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model and hasattr(self.env[custom_handler_model], action):
            return getattr(self.env[custom_handler_model], action)(*args)
        return getattr(self, action)(*args)

    def _get_custom_report_function(self, function_name, prefix):
        """ Returns a report function from its name, first checking it to ensure it's private (and raising if it isn't).
            This helper is used by custom report fields containing function names.
            The function will be called on the report's custom handler if it exists, or on the report itself otherwise.
        """
        self.ensure_one()
        function_name_prefix = f'_report_{prefix}_'
        if not function_name.startswith(function_name_prefix):
            raise UserError(_("Method '%s' must start with the '%s' prefix.", function_name, function_name_prefix))

        if self.custom_handler_model_id:
            handler = self.env[self.custom_handler_model_name]
            if hasattr(handler, function_name):
                return getattr(handler, function_name)

        if not hasattr(self, function_name):
            raise UserError(_("Invalid method %r", function_name))
        # Call the check method without the private prefix to check for others security risks.
        return getattr(self, function_name)

    def _get_lines(self, options, all_column_groups_expression_totals=None, warnings=None):
        self.ensure_one()

        if warnings is not None:
            self._generate_common_warnings(options, warnings)

        if options['report_id'] != self.id:
            # Should never happen; just there to prevent BIG issues and directly spot them
            raise UserError(_("Inconsistent report_id in options dictionary. Options says %s; report is %s.", options['report_id'], self.id))

        # Necessary to ensure consistency of the data if some of them haven't been written in database yet
        self.env.flush_all()

        # Merge static and dynamic lines in a common list
        if all_column_groups_expression_totals is None:
            all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(
                self.line_ids.expression_ids,
                options,
                warnings=warnings,
            )

        dynamic_lines = self._get_dynamic_lines(options, all_column_groups_expression_totals, warnings=warnings)

        lines = []
        line_cache = {} # {report_line: report line dict}
        hide_if_zero_lines = self.env['account.report.line']

        # There are two types of lines:
        # - static lines: the ones generated from self.line_ids
        # - dynamic lines: the ones generated from a call to the functions referred to by self.dynamic_lines_generator
        # This loops combines both types of lines together within the lines list
        for line in self.line_ids: # _order ensures the sequence of the lines
            # Inject all the dynamic lines whose sequence is inferior to the next static line to add
            while dynamic_lines and line.sequence > dynamic_lines[0][0]:
                lines.append(dynamic_lines.pop(0)[1])
            parent_generic_id = line_cache[line.parent_id]['id'] if line.parent_id else None # The parent line has necessarily been treated in a previous iteration
            line_dict = self._get_static_line_dict(options, line, all_column_groups_expression_totals, parent_id=parent_generic_id)
            line_cache[line] = line_dict

            if line.hide_if_zero:
                hide_if_zero_lines += line

            lines.append(line_dict)

        for dummy, left_dynamic_line in dynamic_lines:
            lines.append(left_dynamic_line)

        # Manage growth comparison
        if self._display_growth_comparison(options):
            for line in lines:
                first_value, second_value = line['columns'][0]['no_format'], line['columns'][1]['no_format']

                if not first_value and not second_value:  # For layout lines and such, with no values
                    line['growth_comparison_data'] = {'name': '0.0%', 'growth': 0}
                else:
                    green_on_positive = True
                    model, line_id = self._get_model_info_from_id(line['id'])

                    if model == 'account.report.line' and line_id:
                        report_line = self.env['account.report.line'].browse(line_id)
                        compared_expression = report_line.expression_ids.filtered(
                            lambda expr: expr.label == line['columns'][0]['expression_label']
                        )
                        green_on_positive = compared_expression.green_on_positive

                    line['growth_comparison_data'] = self._compute_growth_comparison_column(
                        options, first_value, second_value, green_on_positive=green_on_positive
                    )

        # Manage hide_if_zero lines:
        # - If they have column values: hide them if all those values are 0 (or empty)
        # - If they don't: hide them if all their children's column values are 0 (or empty)
        # Also, hide all the children of a hidden line.
        hidden_lines_dict_ids = set()
        for line in hide_if_zero_lines:
            children_to_check = line
            current = line
            while current:
                children_to_check |= current
                current = current.children_ids

            all_children_zero = True
            hide_candidates = set()
            for child in children_to_check:
                child_line_dict_id = line_cache[child]['id']

                if child_line_dict_id in hidden_lines_dict_ids:
                    continue
                elif all(col.get('is_zero', True) for col in line_cache[child]['columns']):
                    hide_candidates.add(child_line_dict_id)
                else:
                    all_children_zero = False
                    break

            if all_children_zero:
                hidden_lines_dict_ids |= hide_candidates

        lines[:] = filter(lambda x: x['id'] not in hidden_lines_dict_ids and x.get('parent_id') not in hidden_lines_dict_ids, lines)

        # Create the hierarchy of lines if necessary
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)

        # Handle totals below sections for static lines
        lines = self._add_totals_below_sections(lines, options)

        # Unfold lines (static or dynamic) if necessary and add totals below section to dynamic lines
        lines = self._fully_unfold_lines_if_needed(lines, options)

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(self, options, lines, warnings=warnings)

        if options.get('export_mode') == 'print' and options.get('hide_0_lines'):
            lines = self._filter_out_0_lines(lines)

        return lines

    @api.model
    def format_column_values(self, options, lines):
        self._format_column_values(options, lines, force_format=True)

        return lines

    def _format_column_values(self, options, line_dict_list, force_format=False):
        for line_dict in line_dict_list:
            for column_dict in line_dict['columns']:
                if not column_dict:
                    continue

                if 'name' in column_dict and not force_format:
                    # Columns which have already received a name are assumed to be already formatted; nothing needs to be done for them.
                    # This gives additional flexibility to custom reports, if needed.
                    continue

                column_dict['name'] = self.format_value(
                    options,
                    column_dict.get('no_format'),
                    currency=column_dict.get('currency'),
                    blank_if_zero=column_dict.get('blank_if_zero'),
                    figure_type=column_dict.get('figure_type'),
                    digits=column_dict.get('digits')
                )

    def _generate_common_warnings(self, options, warnings):
        # Display a warning if we're displaying only the data of the current company, but it's also part of a tax unit
        if options.get('available_tax_units') and options['tax_unit'] == 'company_only':
            warnings['account_reports.common_warning_tax_unit'] = {}

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            if self.env['account.move'].search_count(
                [('state', '=', 'draft'), ('date', '<=', options['date']['date_to'])],
                limit=1,
            ):
                warnings['account_reports.common_warning_draft_in_period'] = {}

    def _fully_unfold_lines_if_needed(self, lines, options):
        def line_need_expansion(line_dict):
            return line_dict.get('unfolded') and line_dict.get('expand_function')

        custom_unfold_all_batch_data = None

        # If it's possible to batch unfold and we're unfolding all lines, compute the batch, so that individual expansions are more efficient
        if options['unfold_all'] and self.custom_handler_model_id:
            lines_to_expand_by_function = {}
            for line_dict in lines:
                if line_need_expansion(line_dict):
                    lines_to_expand_by_function.setdefault(line_dict['expand_function'], []).append(line_dict)

            custom_unfold_all_batch_data = self.env[self.custom_handler_model_name]._custom_unfold_all_batch_data_generator(self, options, lines_to_expand_by_function)

        i = 0
        while i < len(lines):
            # We iterate in such a way that if the lines added by an expansion need expansion, they will get it as well
            line_dict = lines[i]
            if line_need_expansion(line_dict):
                groupby = line_dict.get('groupby')
                progress = line_dict.get('progress')
                to_insert = self._expand_unfoldable_line(line_dict['expand_function'], line_dict['id'], groupby, options, progress, 0,
                                                         unfold_all_batch_data=custom_unfold_all_batch_data)
                lines = lines[:i+1] + to_insert + lines[i+1:]
            i += 1

        return lines

    def _generate_total_below_section_line(self, section_line_dict):
        return {
            **section_line_dict,
            'id': self._get_generic_line_id(None, None, parent_line_id=section_line_dict['id'], markup='total'),
            'level': section_line_dict['level'] if section_line_dict['level'] != 0 else 1, # Total line should not be level 0
            'name': _("Total %s", section_line_dict['name']),
            'parent_id': section_line_dict['id'],
            'unfoldable': False,
            'unfolded': False,
            'caret_options': None,
            'action_id': None,
            'page_break': False, # If the section's line possesses a page break, we don't want the total to have it.
        }

    def _get_static_line_dict(self, options, line, all_column_groups_expression_totals, parent_id=None):
        line_id = self._get_generic_line_id('account.report.line', line.id, parent_line_id=parent_id)
        columns = self._build_static_line_columns(line, options, all_column_groups_expression_totals)
        has_children = (any(col['has_sublines'] for col in columns) or bool(line.children_ids))
        groupby = line._get_groupby(options)

        rslt = {
            'id': line_id,
            'name': line.name,
            'groupby': groupby,
            'unfoldable': line.foldable and has_children,
            'unfolded': bool((not line.foldable and (line.children_ids or groupby)) or line_id in options['unfolded_lines']) or (has_children and options['unfold_all']),
            'columns': columns,
            'level': line.hierarchy_level,
            'page_break': line.print_on_new_page,
            'action_id': line.action_id.id,
            'expand_function': groupby and '_report_expand_unfoldable_line_with_groupby' or None,
        }

        if parent_id:
            rslt['parent_id'] = parent_id

        if options['export_mode'] == 'file':
            rslt['code'] = line.code

        if options['show_debug_column']:
            first_group_key = list(options['column_groups'].keys())[0]
            column_group_totals = all_column_groups_expression_totals[first_group_key]
            # Only consider the first column group, as show_debug_column is only true if there is but one.

            engine_selection_labels = dict(self.env['account.report.expression']._fields['engine']._description_selection(self.env))
            expressions_detail = defaultdict(lambda: [])
            col_expression_to_figure_type = {
                column.get('expression_label'): column.get('figure_type') for column in options['columns']
            }
            for expression in line.expression_ids.filtered(lambda x: not x.label.startswith('_default')):
                engine_label = engine_selection_labels[expression.engine]
                figure_type = expression.figure_type or col_expression_to_figure_type.get(expression.label) or 'none'
                expressions_detail[engine_label].append((
                    expression.label,
                    {'formula': expression.formula, 'subformula': expression.subformula, 'value': self._format_value(options, column_group_totals[expression]['value'], figure_type=figure_type, blank_if_zero=False)}
                ))

            # Sort results so that they can be rendered nicely in the UI
            for details in expressions_detail.values():
                details.sort(key=lambda x: x[0])
            sorted_expressions_detail = sorted(expressions_detail.items(), key=lambda x: x[0])
            try:
                rslt['debug_popup_data'] = json.dumps({'expressions_detail': sorted_expressions_detail})
            except TypeError:
                raise UserError(_("Invalid subformula in expression %r of line %r: %s", expression.label, expression.report_line_id.name, expression.subformula))

        return rslt

    @api.model
    def _build_static_line_columns(self, line, options, all_column_groups_expression_totals):
        line_expressions_map = {expr.label: expr for expr in line.expression_ids}
        columns = []
        for column_data in options['columns']:
            current_group_expression_totals = all_column_groups_expression_totals[column_data['column_group_key']]
            target_line_res_dict = {expr.label: current_group_expression_totals[expr] for expr in line.expression_ids if not expr.label.startswith('_default')}

            column_expr_label = column_data['expression_label']
            column_res_dict = target_line_res_dict.get(column_expr_label, {})
            column_value = column_res_dict.get('value')
            column_has_sublines = column_res_dict.get('has_sublines', False)
            column_expression = line_expressions_map.get(column_expr_label, self.env['account.report.expression'])
            figure_type = column_expression.figure_type or column_data['figure_type']

            # Handle info popup
            info_popup_data = {}

            # Check carryover
            carryover_expr_label = '_carryover_%s' % column_expr_label
            carryover_value = target_line_res_dict.get(carryover_expr_label, {}).get('value', 0)
            if self.env.company.currency_id.compare_amounts(0, carryover_value) != 0:
                info_popup_data['carryover'] = self._format_value(options, carryover_value, figure_type='monetary')

                carryover_expression = line_expressions_map[carryover_expr_label]
                if carryover_expression.carryover_target:
                    info_popup_data['carryover_target'] = carryover_expression._get_carryover_target_expression(options).display_name
                # If it's not set, it means the carryover needs to target the same expression

            applied_carryover_value = target_line_res_dict.get('_applied_carryover_%s' % column_expr_label, {}).get('value', 0)
            if self.env.company.currency_id.compare_amounts(0, applied_carryover_value) != 0:
                info_popup_data['applied_carryover'] = self._format_value(options, applied_carryover_value, figure_type='monetary')
                info_popup_data['allow_carryover_audit'] = self.user_has_groups('base.group_no_one')
                info_popup_data['expression_id'] = line_expressions_map['_applied_carryover_%s' % column_expr_label]['id']
                info_popup_data['column_group_key'] = column_data['column_group_key']

            # Handle manual edition popup
            edit_popup_data = {}
            formatter_params = {}
            if column_expression.engine == 'external' and column_expression.subformula \
                and len(options['companies']) == 1 \
                and (not options['available_vat_fiscal_positions'] or options['fiscal_position'] != 'all'):

                # Compute rounding for manual values
                rounding = None
                if figure_type == 'integer':
                    rounding = 0
                else:
                    rounding_opt_match = re.search(r"\Wrounding\W*=\W*(?P<rounding>\d+)", column_expression.subformula)
                    if rounding_opt_match:
                        rounding = int(rounding_opt_match.group('rounding'))
                    elif figure_type == 'monetary':
                        rounding = self.env.company.currency_id.decimal_places

                if 'editable' in column_expression.subformula:
                    edit_popup_data = {
                        'column_group_key': column_data['column_group_key'],
                        'target_expression_id': column_expression.id,
                        'rounding': rounding,
                        'figure_type': figure_type,
                        'column_value': column_value,
                    }

                formatter_params['digits'] = rounding

            # Build result
            if column_value is not None: #In case column value is zero, we still want to go through the condition
                foreign_currency_id = target_line_res_dict.get(f'_currency_{column_expr_label}', {}).get('value')
                if foreign_currency_id:
                    formatter_params['currency'] = self.env['res.currency'].browse(foreign_currency_id)

            column_data = self._build_column_dict(
                column_value,
                column_data,
                options=options,
                column_expression=column_expression if column_expression else None,
                has_sublines=column_has_sublines,
                report_line_id=line.id,
                **formatter_params,
            )

            if info_popup_data:
                column_data['info_popup_data'] = json.dumps(info_popup_data)

            if edit_popup_data:
                column_data['edit_popup_data'] = json.dumps(edit_popup_data)

            columns.append(column_data)

        return columns

    def _build_column_dict(
            self, col_value, col_data,
            options=None, currency=False, digits=1,
            column_expression=None, has_sublines=False,
            report_line_id=None,
    ):
        # Empty column
        if col_value is None and col_data is None:
            return {}

        col_data = col_data or {}
        column_expression = column_expression or self.env['account.report.expression']
        options = options or {}

        blank_if_zero = column_expression.blank_if_zero or col_data.get('blank_if_zero', False)
        figure_type = column_expression.figure_type or col_data.get('figure_type', 'string')

        return {
            'auditable': col_value is not None and column_expression.auditable,
            'blank_if_zero': blank_if_zero,
            'column_group_key': col_data.get('column_group_key'),
            'currency': currency.id if currency else None,
            'currency_symbol': self.env.company.currency_id.symbol if options.get('multi_currency') else None,
            'digits': digits,
            'expression_label': col_data.get('expression_label'),
            'figure_type': figure_type,
            'green_on_positive': column_expression.green_on_positive,
            'has_sublines': has_sublines,
            'is_zero': col_value is None or (
                isinstance(col_value, (int, float))
                and figure_type in ('float', 'integer', 'monetary')
                and self.is_zero(col_value, currency=currency, figure_type=figure_type, digits=digits)
            ),
            'name': self._format_value(options, col_value, currency=currency, blank_if_zero=blank_if_zero, figure_type=figure_type, digits=digits),
            'no_format': col_value,
            'report_line_id': report_line_id,
            'sortable': col_data.get('sortable', False),
        }

    def _get_dynamic_lines(self, options, all_column_groups_expression_totals, warnings=None):
        if self.custom_handler_model_id:
            return self.env[self.custom_handler_model_name]._dynamic_lines_generator(self, options, all_column_groups_expression_totals, warnings=warnings)
        return []

    def _compute_expression_totals_for_each_column_group(self, expressions, options, groupby_to_expand=None, forced_all_column_groups_expression_totals=None, offset=0, limit=None, include_default_vals=False, warnings=None):
        """
            Main computation function for static lines.

            :param expressions: The account.report.expression objects to evaluate.

            :param options: The options dict for this report, obtained from get_options().

            :param groupby_to_expand: The full groupby string for the grouping we want to evaluate. If None, the aggregated value will be computed.
                                      For example, when evaluating a group by partner_id, which further will be divided in sub-groups by account_id,
                                      then id, the full groupby string will be: 'partner_id, account_id, id'.

            :param forced_all_column_groups_expression_totals: The expression totals already computed for this report, to which we will add the
                                                               new totals we compute for expressions (or update the existing ones if some
                                                               expressions are already in forced_all_column_groups_expression_totals). This is
                                                               a dict in the same format as returned by this function.
                                                               This parameter is for example used when adding manual values, where only
                                                               the expressions possibly depending on the new manual value
                                                               need to be updated, while we want to keep all the other values as-is.

            :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                           the load more feature.

            :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                          the load more feature.

            :return: dict(column_group_key, expressions_totals), where:
                - column group key is string identifying each column group in a unique way ; as in options['column_groups']
                - expressions_totals is a dict in the format returned by _compute_expression_totals_for_single_column_group
        """

        def add_expressions_to_groups(expressions_to_add, grouped_formulas, force_date_scope=None):
            """ Groups the expressions that should be computed together.
            """
            for expression in expressions_to_add:
                engine = expression.engine

                if engine not in grouped_formulas:
                    grouped_formulas[engine] = {}

                date_scope = force_date_scope or self._standardize_date_scope_for_date_range(expression.date_scope)
                groupby_data = expression.report_line_id._parse_groupby(options, groupby_to_expand=groupby_to_expand)

                next_groupby = groupby_data['next_groupby'] if engine not in NO_NEXT_GROUPBY_ENGINES else None
                grouping_key = (date_scope, groupby_data['current_groupby'], next_groupby)

                if grouping_key not in grouped_formulas[engine]:
                    grouped_formulas[engine][grouping_key] = {}

                formula = expression.formula

                if expression.engine == 'aggregation' and expression.formula == 'sum_children':
                    formula = ' + '.join(
                        f'_expression:{child_expr.id}'
                        for child_expr in expression.report_line_id.children_ids.expression_ids.filtered(lambda e: e.label == expression.label)
                    )

                if formula not in grouped_formulas[engine][grouping_key]:
                    grouped_formulas[engine][grouping_key][formula] = expression
                else:
                    grouped_formulas[engine][grouping_key][formula] |= expression

        if groupby_to_expand and any(not expression.report_line_id._get_groupby(options) for expression in expressions):
            raise UserError(_("Trying to expand groupby results on lines without a groupby value."))

        # Group formulas for batching (when possible)
        grouped_formulas = {}
        if expressions and not include_default_vals:
            expressions = expressions.filtered(lambda x: not x.label.startswith('_default'))
        for expression in expressions:
            add_expressions_to_groups(expression, grouped_formulas)

            if expression.engine == 'aggregation' and expression.subformula == 'cross_report':
                # Always expand aggregation expressions, in case their subexpressions are not in expressions parameter
                # (this can happen in cross report, or when auditing an individual aggregation expression)
                expanded_cross = expression._expand_aggregations()
                forced_date_scope = self._standardize_date_scope_for_date_range(expression.date_scope)
                add_expressions_to_groups(expanded_cross, grouped_formulas, force_date_scope=forced_date_scope)

        # Treat each formula batch for each column group
        all_column_groups_expression_totals = {}
        for group_key, group_options in self._split_options_per_column_group(options).items():
            if forced_all_column_groups_expression_totals:
                forced_column_group_totals = forced_all_column_groups_expression_totals.get(group_key, None)
            else:
                forced_column_group_totals = None

            current_group_expression_totals = self._compute_expression_totals_for_single_column_group(
                group_options,
                grouped_formulas,
                forced_column_group_expression_totals=forced_column_group_totals,
                offset=offset,
                limit=limit,
                warnings=warnings,
            )
            all_column_groups_expression_totals[group_key] = current_group_expression_totals

        return all_column_groups_expression_totals

    def _standardize_date_scope_for_date_range(self, date_scope):
        """ Depending on the fact the report accepts date ranges or not, different date scopes might mean the same thing.
        This function is used so that, in those cases, only one of these date_scopes' values is used, to avoid useless creation
        of multiple computation batches and improve the overall performance as much as possible.
        """
        if not self.filter_date_range and date_scope in {'normal', 'strict_range'}:
            return 'from_beginning'
        else:
            return date_scope

    def _split_options_per_column_group(self, options):
        """ Get a specific option dict per column group, each enforcing the comparison and horizontal grouping associated
        with the column group. Each of these options dict will contain a new key 'owner_column_group', with the column group key of the
        group it was generated for.

        :param options: The report options upon which the returned options be be based.

        :return:        A dict(column_group_key, options_dict), where column_group_key is the string identifying each column group (the keys
                        of options['column_groups'], and options_dict the generated options for this group.
        """
        options_per_group = {}
        for group_key in options['column_groups']:
            group_options = self._get_column_group_options(options, group_key)
            options_per_group[group_key] = group_options

        return options_per_group

    def _get_column_group_options(self, options, group_key):
        column_group = options['column_groups'][group_key]
        return {
            **options,
            **column_group['forced_options'],
            'forced_domain': options.get('forced_domain', []) + column_group['forced_domain'] + column_group['forced_options'].get('forced_domain', []),
            'owner_column_group': group_key,
        }

    def _compute_expression_totals_for_single_column_group(self, column_group_options, grouped_formulas, forced_column_group_expression_totals=None, offset=0, limit=None, warnings=None):
        """ Evaluates expressions for a single column group.

            :param column_group_options: The options dict obtained from _split_options_per_column_group() for the column group to evaluate.

            :param grouped_formulas: A dict(engine, formula_dict), where:
                                     - engine is a string identifying a report engine, in the same format as in account.report.expression's engine
                                       field's technical labels.
                                     - formula_dict is a dict in the same format as _compute_formula_batch's formulas_dict parameter,
                                       containing only aggregation formulas.

            :param forced_column_group_expression_totals: The expression totals previously computed, in the same format as this function's result.
                                                          If provided, the result of this function will be an updated version of this parameter,
                                                          recomputing the expressions in grouped_fomulas.

            :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                           the load more feature.

            :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                          the load more feature.

            :return: A dict(expression, {'value': value, 'has_sublines': has_sublines}), where:
                     - expression is one of the account.report.expressions that got evaluated

                     - value is the result of that evaluation. Two cases are possible:
                        - if we're evaluating a groupby: value will then be a in the form [(groupby_key, group_val)], where
                            - groupby_key is the key used in the SQL GROUP BY clause to generate this result
                            - group_val: The result computed by the engine for this group. Typically a float.

                        - else: value will directly be the result computed for this expression

                     - has_sublines: [optional key, will default to False if absent]
                                       Whether or not this result corresponds to 1 or more subelements in the database (typically move lines).
                                       This is used to know whether an unfoldable line has results to unfold in the UI.
        """
        def inject_formula_results(formula_results, column_group_expression_totals, cross_report_expression_totals=None):
            for (_key, expressions), result in formula_results.items():
                for expression in expressions:
                    subformula_error_format = _lt("Invalid subformula in expression %r of line %r: %s", expression.label, expression.report_line_id.name, expression.subformula)
                    if expression.engine not in ('aggregation', 'external') and expression.subformula:
                        # aggregation subformulas behave differently (cross_report is markup ; if_below, if_above and force_between need evaluation)
                        # They are directly handled in aggregation engine
                        result_value_key = expression.subformula
                    else:
                        result_value_key = 'result'

                    # The expression might be signed, so we can't just access the dict key, and directly evaluate it instead.

                    if isinstance(result, list):
                        # Happens when expanding a groupby line, to compute its children.
                        # We then want to keep a list(grouping key, total) as the final result of each total
                        expression_value = []
                        expression_has_sublines = False
                        for key, result_dict in result:
                            try:
                                expression_value.append((key, safe_eval(result_value_key, result_dict)))
                            except (ValueError, SyntaxError):
                                raise UserError(subformula_error_format)
                            expression_has_sublines = expression_has_sublines or result_dict.get('has_sublines')
                    else:
                        # For non-groupby lines, we directly set the total value for the line.
                        try:
                            expression_value = safe_eval(result_value_key, result)
                        except (ValueError, SyntaxError):
                            raise UserError(subformula_error_format)
                        expression_has_sublines = result.get('has_sublines')

                    if column_group_options.get('integer_rounding_enabled'):
                        in_monetary_column = any(
                            col['expression_label'] == expression.label
                            for col in column_group_options['columns']
                            if col['figure_type'] in ('monetary', 'monetary_without_symbol')
                        )

                        if (in_monetary_column and not expression.figure_type) or expression.figure_type in ('monetary', 'monetary_without_symbol'):
                            expression_value = float_round(expression_value, precision_digits=0, rounding_method=column_group_options['integer_rounding'])

                    expression_result = {
                        'value': expression_value,
                        'has_sublines': expression_has_sublines,
                    }

                    if expression.report_line_id.report_id == self:
                        if expression in column_group_expression_totals:
                            # This can happen because of a cross report aggregation referencing an expression of its own report,
                            # but forcing a different date_scope onto it. This case is not supported for now ; splitting the aggregation can be
                            # used as a workaround.
                            raise UserError(_(
                                "Expression labelled '%s' of line '%s' is being overwritten when computing the current report. "
                                "Make sure the cross-report aggregations of this report only reference terms belonging to other reports.",
                                expression.label, expression.report_line_id.name
                            ))
                        column_group_expression_totals[expression] = expression_result
                    elif cross_report_expression_totals is not None:
                        # Entering this else means this expression needs to be evaluated because of a cross_report aggregation
                        cross_report_expression_totals[expression] = expression_result

        # Batch each engine that can be
        column_group_expression_totals = dict(forced_column_group_expression_totals) if forced_column_group_expression_totals else {}
        cross_report_expr_totals_by_scope = {}
        batchable_engines = [
            selection_val[0]
            for selection_val in self.env['account.report.expression']._fields['engine'].selection
            if selection_val[0] != 'aggregation'
        ]
        for engine in batchable_engines:
            for (date_scope, current_groupby, next_groupby), formulas_dict in grouped_formulas.get(engine, {}).items():
                formula_results = self._compute_formula_batch(column_group_options, engine, date_scope, formulas_dict, current_groupby, next_groupby,
                                                              offset=offset, limit=limit, warnings=warnings)
                inject_formula_results(
                    formula_results,
                    column_group_expression_totals,
                    cross_report_expression_totals=cross_report_expr_totals_by_scope.setdefault(date_scope, {})
                )

        # Now that everything else has been computed, resolve aggregation expressions
        # (they can't be treated as the other engines, as if we batch them per date_scope, we'll not be able
        # to compute expressions depending on other expressions with a different date scope).
        aggregation_formulas_dict = {}
        for (date_scope, _current_groupby, _next_groupby), formulas_dict in grouped_formulas.get('aggregation', {}).items():
            for formula, expressions in formulas_dict.items():
                for expression in expressions:
                    # group_by are ignored by this engine, so we merge every grouped entry into a common dict
                    forced_date_scope = date_scope if expression.subformula == 'cross_report' or expression.report_line_id.report_id != self else None
                    aggreation_formula_dict_key = (formula, forced_date_scope)
                    aggregation_formulas_dict.setdefault(aggreation_formula_dict_key, self.env['account.report.expression'])
                    aggregation_formulas_dict[aggreation_formula_dict_key] |= expression

        if aggregation_formulas_dict:
            aggregation_formula_results = self._compute_totals_no_batch_aggregation(column_group_options, aggregation_formulas_dict, column_group_expression_totals, cross_report_expr_totals_by_scope)
            inject_formula_results(aggregation_formula_results, column_group_expression_totals)

        return column_group_expression_totals

    def _compute_totals_no_batch_aggregation(self, column_group_options, formulas_dict, other_current_report_expr_totals, other_cross_report_expr_totals_by_scope):
        """ Computes expression totals for 'aggregation' engine, after all other engines have been evaluated.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formulas_dict: A dict {(formula, forced_date_scope): expressions}, containing only aggregation formulas.
                              forced_date_scope will only be set in case of cross_report expressions. Else, it will be None

        :param other_current_report_expr_totals: The expressions_totals obtained after computing all non-aggregation engines, for the expressions
                                                 belonging directly to self (so, not the ones referenced by a cross_report aggreation).
                                                 This is a dict in the same format as _compute_expression_totals_for_single_column_group's result
                                                 (the only difference being it does not contain any aggregation expression yet).

        :param other_cross_report_expr_totals: A dict(forced_date_scope, expression_totals), where expression_totals is in the same form as
                                               _compute_expression_totals_for_single_column_group's result. This parameter contains the results
                                               of the non-aggregation expressions used by cross_report expressions ; they all belong to different
                                               reports than self. The forced_date_scope corresponds to the original date_scope set on the
                                               cross_report expression referencing them. The same expressions can be referenced multiple times
                                               under different date scopes.

        :return : A dict((formula, expressions), result), where result is in the form {'result': numeric_value}
        """
        def _resolve_subformula_on_dict(result, line_codes_expression_map, subformula):
            split_subformula = subformula.split('.')
            if len(split_subformula) > 1:
                line_code, expression_label = split_subformula
                return result[line_codes_expression_map[line_code][expression_label]]

            if subformula.startswith('_expression:'):
                expression_id = int(subformula.split(':')[1])
                return result[expression_id]

            # Wrong subformula; the KeyError is caught in the function below
            raise KeyError()

        def _check_is_float(to_test):
            try:
                float(to_test)
                return True
            except ValueError:
                return False

        def add_expression_to_map(expression, expression_res, figure_types_cache, current_report_eval_dict, current_report_codes_map, other_reports_eval_dict, other_reports_codes_map, cross_report=False):
            """
                Process an expression and its result, updating various dictionaries with relevant information.
                Parameters:
                - expression (object): The expression object to process.
                - expression_res (dict): The result of the expression.
                - figure_types_cache (dict): {report : {label: figure_type}}.
                - current_report_eval_dict (dict): {expression_id: value}.
                - current_report_codes_map (dict): {line_code: {expression_label: expression_id}}.
                - other_reports_eval_dict (dict): {forced_date_scope: {expression_id: value}}.
                - other_reports_codes_map (dict): {forced_date_scope: {line_code: {expression_label: expression_id}}}.
                - cross_report: A boolean to know if we are processsing cross_report expression.
            """

            expr_report = expression.report_line_id.report_id
            report_default_figure_types = figure_types_cache.setdefault(expr_report, {})
            expression_label = report_default_figure_types.get(expression.label, '_not_in_cache')
            if expression_label == '_not_in_cache':
                report_default_figure_types[expression.label] = expr_report.column_ids.filtered(
                    lambda x: x.expression_label == expression.label).figure_type

            default_figure_type = figure_types_cache[expr_report][expression.label]
            figure_type = expression.figure_type or default_figure_type
            value = expression_res['value']
            if figure_type == 'monetary' and value:
                value = self.env.company.currency_id.round(value)

            if cross_report:
                other_reports_eval_dict.setdefault(forced_date_scope, {})[expression.id] = value
            else:
                current_report_eval_dict[expression.id] = value

        current_report_eval_dict = {} # {expression_id: value}
        other_reports_eval_dict = {} # {forced_date_scope: {expression_id: value}}
        current_report_codes_map = {} # {line_code: {expression_label: expression_id}}
        other_reports_codes_map = {} # {forced_date_scope: {line_code: {expression_label: expression_id}}}

        figure_types_cache = {}  # {report : {label: figure_type}}
        for expression, expression_res in other_current_report_expr_totals.items():
            add_expression_to_map(expression, expression_res, figure_types_cache, current_report_eval_dict, current_report_codes_map, other_reports_eval_dict, other_reports_codes_map)
            if expression.report_line_id.code:
                current_report_codes_map.setdefault(expression.report_line_id.code, {})[expression.label] = expression.id

        for forced_date_scope, scope_expr_totals in other_cross_report_expr_totals_by_scope.items():
            for expression, expression_res in scope_expr_totals.items():
                add_expression_to_map(expression, expression_res, figure_types_cache, current_report_eval_dict, current_report_codes_map, other_reports_eval_dict, other_reports_codes_map, True)
                if expression.report_line_id.code:
                    other_reports_codes_map.setdefault(forced_date_scope, {}).setdefault(expression.report_line_id.code, {})[expression.label] = expression.id

        # Complete current_report_eval_dict with the formulas of uncomputed aggregation lines
        aggregations_terms_to_evaluate = set() # Those terms are part of the formulas to evaluate; we know they will get a value eventually
        for (formula, forced_date_scope), expressions in formulas_dict.items():
            for expression in expressions:
                aggregations_terms_to_evaluate.add(f"_expression:{expression.id}") # In case it needs to be called by sum_children

                if expression.report_line_id.code:
                    if expression.report_line_id.report_id == self:
                        current_report_codes_map.setdefault(expression.report_line_id.code, {})[expression.label] = expression.id
                    else:
                        other_reports_codes_map.setdefault(forced_date_scope, {}).setdefault(expression.report_line_id.code, {})[expression.label] = expression.id

                    aggregations_terms_to_evaluate.add(f"{expression.report_line_id.code}.{expression.label}")

                    if not expression.subformula:
                        # Expressions with bounds cannot be replaced by their formula in formulas calling them (otherwize, bounds would be ignored).
                        # Same goes for cross_report, otherwise the forced_date_scope will be ignored, leading to an impossibility to get evaluate the expression.
                        if expression.report_line_id.report_id == self:
                            eval_dict = current_report_eval_dict
                        else:
                            eval_dict = other_reports_eval_dict.setdefault(forced_date_scope, {})

                        eval_dict[expression.id] = formula

        rslt = {}
        to_treat = [(formula, formula, forced_date_scope) for (formula, forced_date_scope) in formulas_dict.keys()] # Formed like [(expanded formula, original unexpanded formula)]
        term_separator_regex = r'(?<!\de)[+-]|[ ()/*]'
        term_replacement_regex = r"(^|(?<=[ ()+/*-]))%s((?=[ ()+/*-])|$)"
        while to_treat:
            formula, unexpanded_formula, forced_date_scope = to_treat.pop(0)

            full_eval_dict = {**current_report_eval_dict, **other_reports_eval_dict.get(forced_date_scope, {})}
            full_codes_map = {**current_report_codes_map, **other_reports_codes_map.get(forced_date_scope, {})}

            # Evaluate the formula
            terms_to_eval = [term for term in re.split(term_separator_regex, formula) if term and not _check_is_float(term)]
            if terms_to_eval:
                # The formula can't be evaluated as-is. Replace the terms by their value or formula,
                # and enqueue the formula back; it'll be tried anew later in the loop.
                for term in terms_to_eval:
                    try:
                        expanded_term = _resolve_subformula_on_dict(
                            full_eval_dict,
                            full_codes_map,
                            term,
                        )
                    except KeyError:
                        if term in aggregations_terms_to_evaluate:
                            # Then, the term is probably an aggregation with bounds that still needs to be computed. We need to keep on looping
                            continue
                        else:
                            raise UserError(_("Could not expand term %s while evaluating formula %s", term, unexpanded_formula))

                    formula = re.sub(term_replacement_regex % re.escape(term), f'({expanded_term})', formula)

                to_treat.append((formula, unexpanded_formula, forced_date_scope))

            else:
                # The formula contains only digits and operators; it can be evaluated
                try:
                    formula_result = expr_eval(formula)
                except ZeroDivisionError:
                    # Arbitrary choice; for clarity of the report. A 0 division could typically happen when there is no result in the period.
                    formula_result = 0

                for expression in formulas_dict[(unexpanded_formula, forced_date_scope)]:
                    # Apply subformula
                    if expression.subformula and expression.subformula.startswith('if_other_expr_'):
                        other_expr_criterium_match = re.match(
                            r"^(?P<criterium>\w+)\("
                            r"(?P<line_code>\w+)[.](?P<expr_label>\w+),[ ]*"
                            r"(?P<bound_params>.*)\)$",
                            expression.subformula
                        )
                        if not other_expr_criterium_match:
                            raise UserError(_("Wrong format for if_other_expr_above/if_other_expr_below formula: %s", expression.subformula))

                        criterium_code = other_expr_criterium_match['line_code']
                        criterium_label = other_expr_criterium_match['expr_label']
                        criterium_expression_id = full_codes_map.get(criterium_code, {}).get(criterium_label)
                        criterium_val = full_eval_dict.get(criterium_expression_id)

                        if not criterium_expression_id:
                            raise UserError(_("This subformula references an unknown expression: %s", expression.subformula))

                        if not isinstance(criterium_val, (float, int)):
                            # The criterium expression has not be evaluated yet. Postpone the evaluation of this formula, and skip this expression
                            # for now. We still try to evaluate other expressions using this formula if any; this means those expressions will
                            # be processed a second time later, giving the same result. This is a rare corner case, and not so costly anyway.
                            to_treat.append((formula, unexpanded_formula, forced_date_scope))
                            continue

                        bound_subformula = other_expr_criterium_match['criterium'].replace('other_expr_', '') # e.g. 'if_other_expr_above' => 'if_above'
                        bound_params = other_expr_criterium_match['bound_params']
                        bound_value = self._aggregation_apply_bounds(column_group_options, f"{bound_subformula}({bound_params})", criterium_val)
                        expression_result = formula_result * int(bool(bound_value))

                    else:
                        expression_result = self._aggregation_apply_bounds(column_group_options, expression.subformula, formula_result)

                    if column_group_options.get('integer_rounding_enabled'):
                        expression_result = float_round(expression_result, precision_digits=0, rounding_method=column_group_options['integer_rounding'])

                    # Store result
                    standardized_expression_scope = self._standardize_date_scope_for_date_range(expression.date_scope)
                    if (forced_date_scope == standardized_expression_scope or not forced_date_scope) and expression.report_line_id.report_id == self:
                        # This condition ensures we don't return necessary subcomputations in the final result
                        rslt[(unexpanded_formula, expression)] = {'result': expression_result}

                    # Handle recursive aggregations (explicit or through the sum_children shortcut).
                    # We need to make the result of our computation available to other aggregations, as they are still waiting in to_treat to be evaluated.
                    if expression.report_line_id.report_id == self:
                        current_report_eval_dict[expression.id] = expression_result
                    else:
                        other_reports_eval_dict.setdefault(forced_date_scope, {})[expression.id] = expression_result

        return rslt

    def _aggregation_apply_bounds(self, column_group_options, subformula, unbound_value):
        """ Applies the bounds of the provided aggregation expression to an unbounded value that got computed for it and returns the result.
        Bounds can be defined as subformulas of aggregation expressions, with the following possible values:

            - if_above(CUR(bound_value)):
                                    => Result will be 0 if it's <= the provided bound value; else it'll be unbound_value

            - if_below(CUR(bound_value)):
                                    => Result will be 0 if it's >= the provided bound value; else it'll be unbound_value

            - if_between(CUR(bound_value1), CUR(bound_value2)):
                                    => Result will be unbound_value if it's strictly between the provided bounds. Else, it will
                                       be brought back to the closest bound.

            - round(decimal_places):
                                    => Result will be round(unbound_value, decimal_places)

            (where CUR is a currency code, and bound_value* are float amounts in CUR currency)
        """
        if not subformula:
            return unbound_value

        # So an expression can't have bounds and be cross_reports, for simplicity.
        # To do that, just split the expression in two parts.
        if subformula and subformula.startswith('round'):
            precision_string = re.match(r"round\((?P<precision>\d+)\)", subformula)['precision']
            return round(unbound_value, int(precision_string))

        if subformula != 'cross_report':
            company_currency = self.env.company.currency_id
            date_to = column_group_options['date']['date_to']

            match = re.match(
                r"(?P<criterium>\w*)"
                r"\((?P<currency_1>[A-Z]{3})\((?P<amount_1>[-]?\d+(\.\d+)?)\)"
                r"(,(?P<currency_2>[A-Z]{3})\((?P<amount_2>[-]?\d+(\.\d+)?)\))?\)$",
                subformula.replace(' ', '')
            )
            group_values = match.groupdict()

            # Convert the provided bounds into company currency
            currency_code_1 = group_values.get('currency_1')
            currency_code_2 = group_values.get('currency_2')
            currency_codes = [
                currency_code
                for currency_code in [currency_code_1, currency_code_2]
                if currency_code and currency_code != company_currency.name
            ]

            if currency_codes:
                currencies = self.env['res.currency'].with_context(active_test=False).search([('name', 'in', currency_codes)])
            else:
                currencies = self.env['res.currency']

            amount_1 = float(group_values['amount_1'] or 0)
            amount_2 = float(group_values['amount_2'] or 0)
            for currency in currencies:
                if currency != company_currency:
                    if currency.name == currency_code_1:
                        amount_1 = currency._convert(amount_1, company_currency, self.env.company, date_to)
                    if amount_2 and currency.name == currency_code_2:
                        amount_2 = currency._convert(amount_2, company_currency, self.env.company, date_to)

            # Evaluate result
            criterium = group_values['criterium']
            if criterium == 'if_below':
                if company_currency.compare_amounts(unbound_value, amount_1) >= 0:
                    return 0
            elif criterium == 'if_above':
                if company_currency.compare_amounts(unbound_value, amount_1) <= 0:
                    return 0
            elif criterium == 'if_between':
                if company_currency.compare_amounts(unbound_value, amount_1) < 0 or company_currency.compare_amounts(unbound_value, amount_2) > 0:
                    return 0
            else:
                raise UserError(_("Unknown bound criterium: %s", criterium))

        return unbound_value

    def _compute_formula_batch(self, column_group_options, formula_engine, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Evaluates a batch of formulas.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formula_engine: A string identifying a report engine. Must be one of account.report.expression's engine field's technical labels.

        :param date_scope: The date_scope under which to evaluate the fomulas. Must be one of account.report.expression's date_scope field's
                           technical labels.

        :param formulas_dict: A dict in the dict(formula, expressions), where:
                                - formula: a formula to be evaluated with the engine referred to by parent dict key
                                - expressions: a recordset of all the expressions to evaluate using formula (possibly with distinct subformulas)

        :param current_groupby: The groupby to evaluate, or None if there isn't any. In case of multi-level groupby, only contains the element
                                that needs to be computed (so, if unfolding a line doing 'partner_id,account_id,id'; current_groupby will only be
                                'partner_id'). Subsequent groupby will be in next_groupby.

        :param next_groupby: Full groupby string of the groups that will have to be evaluated next for these expressions, or None if there isn't any.
                             For example, in the case depicted in the example of current_groupby, next_groupby will be 'account_id,id'.

        :param offset: The SQL offset to use when computing the result of these expressions.

        :param limit: The SQL limit to apply when computing these expressions' result.

        :return: The result might have two different formats depending on the situation:
            - if we're computing a groupby: {(formula, expressions): [(grouping_key, {'result': value, 'has_sublines': boolean}), ...], ...}
            - if we're not: {(formula, expressions): {'result': value, 'has_sublines': boolean}, ...}
            'result' key is the default; different engines might use one or multiple other keys instead, depending of the subformulas they allow
            (e.g. 'sum', 'sum_if_pos', ...)
        """
        engine_function_name = f'_compute_formula_batch_with_engine_{formula_engine}'
        return getattr(self, engine_function_name)(
            column_group_options, date_scope, formulas_dict, current_groupby, next_groupby,
            offset=offset, limit=limit, warnings=warnings,
        )

    def _compute_formula_batch_with_engine_tax_tags(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Report engine.

        The formulas made for this report simply consist of a tag label. When an expression using this engine is created, it also creates two
        account.account.tag objects, namely -tag and +tag, where tag is the chosen formula. The balance of the expressions using this engine is
        computed by gathering all the move lines using their tags, and applying the sign of their tag to their balance, together with a -1 factor
        if the tax_tag_invert field of the move line is True.

        This engine does not support any subformula.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))
        all_expressions = self.env['account.report.expression']
        for expressions in formulas_dict.values():
            all_expressions |= expressions
        tags = all_expressions._get_matching_tags()

        currency_table_query = self._get_query_currency_table(options)
        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        tables, where_clause, where_params = self._query_get(options, date_scope)
        tail_query, tail_params = self._get_engine_query_tail(offset, limit)
        if self.pool['account.account.tag'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            acc_tag_name = f"COALESCE(acc_tag.name->>'{lang}', acc_tag.name->>'en_US')"
        else:
            acc_tag_name = 'acc_tag.name'
        sql = f"""
            SELECT
                SUBSTRING({acc_tag_name}, 2, LENGTH({acc_tag_name}) - 1) AS formula,
                SUM(ROUND(COALESCE(account_move_line.balance, 0) * currency_table.rate, currency_table.precision)
                    * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                    * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                ) AS balance,
                COUNT(account_move_line.id) AS aml_count
                {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}

            FROM {tables}

            JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
            JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
                AND acc_tag.id IN %s
            JOIN {currency_table_query}
                ON currency_table.company_id = account_move_line.company_id

            WHERE {where_clause}

            GROUP BY SUBSTRING({acc_tag_name}, 2, LENGTH({acc_tag_name}) - 1)
                {f', {groupby_sql}' if groupby_sql else ''}

            {tail_query}
        """

        params = [tuple(tags.ids)] + where_params + tail_params
        self._cr.execute(sql, params)

        rslt = {formula_expr: [] if current_groupby else {'result': 0, 'has_sublines': False} for formula_expr in formulas_dict.items()}
        for query_res in self._cr.dictfetchall():

            formula = query_res['formula']
            rslt_dict = {'result': query_res['balance'], 'has_sublines': query_res['aml_count'] > 0}
            if current_groupby:
                rslt[(formula, formulas_dict[formula])].append((query_res['grouping_key'], rslt_dict))
            else:
                rslt[(formula, formulas_dict[formula])] = rslt_dict

        return rslt

    def _compute_formula_batch_with_engine_domain(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                      then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                      keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """
        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        'sum': 0,
                        'sum_if_pos': 0,
                        'sum_if_neg': 0,
                        'count_rows': 0,
                        'has_sublines': False,
                    }
            return formula_rslt

        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        ct_query = self._get_query_currency_table(options)

        rslt = {}

        for formula, expressions in formulas_dict.items():
            try:
                line_domain = literal_eval(formula)
            except (ValueError, SyntaxError):
                raise UserError(_("Invalid domain formula in expression %r of line %r: %s", expressions.label, expressions.report_line_id.name, formula))
            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)

            tail_query, tail_params = self._get_engine_query_tail(offset, limit)
            query = f"""
                SELECT
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                    COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                    {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                {tail_query}
            """

            # Fetch the results.
            formula_rslt = []
            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            total_sum = 0
            for query_res in all_query_res:
                res_sum = query_res['sum']
                total_sum += res_sum
                totals = {
                    'sum': res_sum,
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'count_rows': query_res['count_rows'],
                    'has_sublines': query_res['count_rows'] > 0,
                }
                formula_rslt.append((query_res.get('grouping_key', None), totals))

            # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
            expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
            for expression in expressions:
                subformula_without_sign = expression.subformula.replace('-', '').strip()
                if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                else:
                    expressions_by_sign_policy['no_sign_check'] += expression

            # Then we have to check the total of the line and only give results if its sign matches the desired policy.
            # This is important for groupby managements, for which we can't just check the sign query_res by query_res
            if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
                sign_policy_with_value = 'sum_if_pos' if self.env.company.currency_id.compare_amounts(total_sum, 0.0) >= 0 else 'sum_if_neg'
                # >= instead of > is intended; usability decision: 0 is considered positive

                formula_rslt_with_sign = [(grouping_key, {**totals, sign_policy_with_value: totals['sum']}) for grouping_key, totals in formula_rslt]

                for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                    policy_expressions = expressions_by_sign_policy[sign_policy]

                    if policy_expressions:
                        if sign_policy == sign_policy_with_value:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby(formula_rslt_with_sign)
                        else:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby([])

            if expressions_by_sign_policy['no_sign_check']:
                rslt[(formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(formula_rslt)

        return rslt

    def _compute_formula_batch_with_engine_account_codes(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        r""" Report engine.

        Formulas made for this engine target account prefixes. Each of the prefix used in the formula will be evaluated as the sum of the move
        lines made on the accounts matching it. Those prefixes can be used together with arithmetic operations to perform them on the obtained
        results.
        Example: '123 - 456' will substract the balance of all account starting with 456 from the one of all accounts starting with 123.

        It is also possible to exclude some subprefixes, with \ operator.
        Example: '123\(1234)' will match prefixes all accounts starting with '123', except the ones starting with '1234'

        To only match the balance of an account is it's positive (debit) or negative (credit), the letter D or C can be put just next to the prefix:
        Example '123D': will give the total balance of accounts starting with '123' if it's positive, else it will be evaluated as 0.

        Multiple subprefixes can be excluded if needed.
        Example: '123\(1234,1236)

        All these syntaxes can be mixed together.
        Example: '123D\(1235) + 56 - 416C'

        Note: if C or D character needs to be part of the prefix, it is possible to differentiate them of debit and credit match characters
        by using an empty prefix exclusion.
        Example 1: '123D\' will take the total balance of accounts starting with '123D'
        Example 2: '123D\C' will return the balance of accounts starting with '123D' if it's negative, 0 otherwise.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        # Gather the account code prefixes to compute the total from
        prefix_details_by_formula = {}  # in the form {formula: [(1, prefix1), (-1, prefix2)]}
        prefixes_to_compute = set()
        for formula in formulas_dict:
            prefix_details_by_formula[formula] = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(' ', '')):
                if token:
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)

                    if not token_match:
                        raise UserError(_("Invalid token '%s' in account_codes formula '%s'", token, formula))

                    parsed_token = token_match.groupdict()

                    if not parsed_token:
                        raise UserError(_("Could not parse account_code formula from token '%s'", token))

                    multiplicator = -1 if parsed_token['sign'] == '-' else 1
                    excluded_prefixes_match = token_match['excluded_prefixes']
                    excluded_prefixes = excluded_prefixes_match.split(',') if excluded_prefixes_match else []
                    prefix = token_match['prefix']

                    # We group using both prefix and excluded_prefixes as keys, for the case where two expressions would
                    # include the same prefix, but exlcude different prefixes (example 104\(1041) and 104\(1042))
                    prefix_key = (prefix, *excluded_prefixes)
                    prefix_details_by_formula[formula].append((multiplicator, prefix_key, token_match['balance_character']))
                    prefixes_to_compute.add((prefix, tuple(excluded_prefixes)))

        # Create the subquery for the WITH linking our prefixes with account.account entries
        all_prefixes_queries = []
        prefix_params = []
        prefilter = self.env['account.account']._check_company_domain(self.get_report_company_ids(options))
        for prefix, excluded_prefixes in prefixes_to_compute:
            account_domain = [
                *prefilter,
            ]

            tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix)

            if tag_match:
                if tag_match['ref']:
                    tag_id = self.env['ir.model.data']._xmlid_to_res_id(tag_match['ref'])
                else:
                    tag_id = int(tag_match['id'])

                account_domain.append(('tag_ids', 'in', [tag_id]))
            else:
                account_domain.append(('code', '=like', f'{prefix}%'))

            excluded_prefixes_domains = []

            for excluded_prefix in excluded_prefixes:
                excluded_prefixes_domains.append([('code', '=like', f'{excluded_prefix}%')])

            if excluded_prefixes_domains:
                account_domain.append('!')
                account_domain += osv.expression.OR(excluded_prefixes_domains)

            prefix_tables, prefix_where_clause, prefix_where_params = self.env['account.account']._where_calc(account_domain).get_sql()

            prefix_params.append(prefix)
            for excluded_prefix in excluded_prefixes:
                prefix_params.append(excluded_prefix)

            prefix_select_query = ', '.join(['%s'] * (len(excluded_prefixes) + 1)) # +1 for prefix
            prefix_select_query = f'ARRAY[{prefix_select_query}]'

            all_prefixes_queries.append(f"""
                SELECT
                    {prefix_select_query} AS prefix,
                    account_account.id AS account_id
                FROM {prefix_tables}
                WHERE {prefix_where_clause}
            """)
            prefix_params += prefix_where_params

        # Build a map to associate each account with the prefixes it matches
        accounts_prefix_map = defaultdict(list)
        self._cr.execute(' UNION ALL '.join(all_prefixes_queries), prefix_params)
        for prefix, account_id in self._cr.fetchall():
            accounts_prefix_map[account_id].append(tuple(prefix))

        # Run main query
        tables, where_clause, where_params = self._query_get(options, date_scope)

        currency_table_query = self._get_query_currency_table(options)
        extra_groupby_sql = f', account_move_line.{current_groupby}' if current_groupby else ''
        extra_select_sql = f', account_move_line.{current_groupby} AS grouping_key' if current_groupby else ''
        tail_query, tail_params = self._get_engine_query_tail(offset, limit)

        query = f"""
            SELECT
                account_move_line.account_id AS account_id,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS sum,
                COUNT(account_move_line.id) AS aml_count
                {extra_select_sql}
            FROM {tables}
            JOIN {currency_table_query} ON currency_table.company_id = account_move_line.company_id
            WHERE {where_clause}
            GROUP BY account_move_line.account_id{extra_groupby_sql}
            {tail_query}
        """
        self._cr.execute(query, where_params + tail_params)

        # Parse result
        rslt = {}

        res_by_prefix_account_id = {}
        for query_res in self._cr.dictfetchall():
            # Done this way so that we can run similar code for groupby and non-groupby
            grouping_key = query_res['grouping_key'] if current_groupby else None
            account_id = query_res['account_id']
            for prefix_key in accounts_prefix_map[account_id]:
                res_by_prefix_account_id.setdefault(prefix_key, {})\
                                        .setdefault(account_id, [])\
                                        .append((grouping_key, {'result': query_res['sum'], 'has_sublines': query_res['aml_count'] > 0}))

        for formula, prefix_details in prefix_details_by_formula.items():
            rslt_key = (formula, formulas_dict[formula])
            rslt_destination = rslt.setdefault(rslt_key, [] if current_groupby else {'result': 0, 'has_sublines': False})
            for multiplicator, prefix_key, balance_character in prefix_details:
                res_by_account_id = res_by_prefix_account_id.get(prefix_key, {})

                for account_results in res_by_account_id.values():
                    account_total_value = sum(group_val['result'] for (group_key, group_val) in account_results)
                    comparator = self.env.company.currency_id.compare_amounts(account_total_value, 0.0)

                    # Manage balance_character.
                    if not balance_character or (balance_character == 'D' and comparator >= 0) or (balance_character == 'C' and comparator < 0):

                        for group_key, group_val in account_results:
                            rslt_group = {
                                **group_val,
                                'result': multiplicator * group_val['result'],
                            }

                            if current_groupby:
                                rslt_destination.append((group_key, rslt_group))
                            else:
                                rslt_destination['result'] += rslt_group['result']
                                rslt_destination['has_sublines'] = rslt_destination['has_sublines'] or rslt_group['has_sublines']

        return rslt

    def _compute_formula_batch_with_engine_external(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Report engine.

        This engine computes its result from the account.report.external.value objects that are linked to the expression.

        Two different formulas are possible:
        - sum: if the result must be the sum of all the external values in the period.
        - most_recent: it the result must be the value of the latest external value in the period, which can be a number or a text

        No subformula is allowed for this engine.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        if current_groupby or next_groupby or offset or limit:
            raise UserError(_("'external' engine does not support groupby, limit nor offset."))

        # Date clause
        date_from, date_to, dummy = self._get_date_bounds_info(options, date_scope)
        external_value_domain = [('date', '<=', date_to)]
        if date_from:
            external_value_domain.append(('date', '>=', date_from))

        # Company clause
        external_value_domain.append(('company_id', 'in', self.get_report_company_ids(options)))

        # Fiscal Position clause
        fpos_option = options['fiscal_position']
        if fpos_option == 'domestic':
            external_value_domain.append(('foreign_vat_fiscal_position_id', '=', False))
        elif fpos_option != 'all':
            # Then it's a fiscal position id
            external_value_domain.append(('foreign_vat_fiscal_position_id', '=', int(fpos_option)))

        # Do the computation
        dummy, where_clause, where_params = self.env['account.report.external.value']._where_calc(external_value_domain).get_sql()
        currency_table_query = self._get_query_currency_table(options)

        # We have to execute two separate queries, one for text values and one for numeric values
        num_queries, num_query_params = [], []
        string_queries, string_query_params = [], []
        monetary_queries, monetary_query_params = [], []
        for formula, expressions in formulas_dict.items():
            query_end = ''
            if formula == 'most_recent':
                query_end = """
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """
            string_query = f"""
                    SELECT %s, text_value
                    FROM account_report_external_value
                    WHERE {where_clause} AND target_report_expression_id = %s
                """
            monetary_query = f"""
                SELECT
                    %s,
                    COALESCE(SUM(COALESCE(ROUND(CAST(value AS numeric) * currency_table.rate, currency_table.precision), 0)), 0)
                FROM account_report_external_value
                    JOIN {currency_table_query} ON currency_table.company_id = account_report_external_value.company_id
                WHERE {where_clause} AND target_report_expression_id = %s
                {query_end}
            """
            num_query = f"""
                    SELECT %s, SUM(COALESCE(value, 0))
                      FROM account_report_external_value
                     WHERE {where_clause} AND target_report_expression_id = %s
               {query_end}
            """

            for expression in expressions:
                params = [
                    expression.id,
                    *where_params,
                    expression.id,
                ]
                if expression.figure_type == "string":
                    string_queries.append(string_query)
                    string_query_params += params
                elif expression.figure_type == "monetary":
                    monetary_queries.append(monetary_query)
                    monetary_query_params += params
                else:
                    num_queries.append(num_query)
                    num_query_params += params

        # Convert to dict to have expression ids as keys
        query_results_dict = {}
        for query_list, query_params in ((num_queries, num_query_params), (string_queries, string_query_params), (monetary_queries, monetary_query_params)):
            if query_list:
                query = '(' + ') UNION ALL ('.join(query_list) + ')'
                self._cr.execute(query, query_params)
                query_results = self._cr.fetchall()
                query_results_dict.update(dict(query_results))

        # Build result dict
        rslt = {}
        for formula, expressions in formulas_dict.items():
            for expression in expressions:
                expression_value = query_results_dict.get(expression.id)
                # If expression_value is None, we have no previous value for this expression (set default at 0.0)
                expression_value = expression_value or ('' if expression.figure_type == 'string' else 0.0)
                rslt[(formula, expression)] = {'result': expression_value, 'has_sublines': False}

        return rslt

    def _compute_formula_batch_with_engine_custom(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        rslt = {}
        for formula, expressions in formulas_dict.items():
            custom_engine_function = self._get_custom_report_function(formula, 'custom_engine')
            rslt[(formula, expressions)] = custom_engine_function(
                expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit, warnings=warnings)
        return rslt

    def _get_engine_query_tail(self, offset, limit):
        """ Helper to generate the OFFSET, LIMIT and ORDER conditions of formula engines' queries.
        """
        params = []
        query_tail = ""

        if offset:
            query_tail += " OFFSET %s"
            params.append(offset)

        if limit:
            query_tail += " LIMIT %s"
            params.append(limit)

        return query_tail, params

    def _generate_carryover_external_values(self, options):
        """ Generates the account.report.external.value objects corresponding to this report's carryover under the provided options.

        In case of multicompany setup, we need to split the carryover per company, for ease of audit, and so that the carryover isn't broken when
        a company leaves a tax unit.

        We first generate the carryover for the wholy-aggregated report, so that we can see what final result we want.
        Indeed due to force_between, if_above and if_below conditions, each carryover might be different from the sum of the individidual companies'
        carryover values. To handle this case, we generate each company's carryover values separately, then do a carryover adjustment on the
        main company (main for tax units, first one selected else) in order to bring their total to the result we computed for the whole unit.
        """
        self.ensure_one()

        if len(options['column_groups']) > 1:
            # The options must be forged in order to generate carryover values. Entering this conditions means this hasn't been done in the right way.
            raise UserError(_("Carryover can only be generated for a single column group."))

        # Get the expressions to evaluate from the report
        carryover_expressions = self.line_ids.expression_ids.filtered(lambda x: x.label.startswith('_carryover_'))
        expressions_to_evaluate = carryover_expressions._expand_aggregations()

        # Expression totals for all selected companies
        expression_totals_per_col_group = self._compute_expression_totals_for_each_column_group(expressions_to_evaluate, options)
        expression_totals = expression_totals_per_col_group[list(options['column_groups'].keys())[0]]
        carryover_values = {expression: expression_totals[expression]['value'] for expression in carryover_expressions}

        if len(options['companies']) == 1:
            company = self.env['res.company'].browse(self.get_report_company_ids(options))
            self._create_carryover_for_company(options, company, {expr: result for expr, result in carryover_values.items()})
        else:
            multi_company_carryover_values_sum = defaultdict(lambda: 0)

            column_group_key = next(col_group_key for col_group_key in options['column_groups'])
            for company_opt in options['companies']:
                company = self.env['res.company'].browse(company_opt['id'])
                company_options = {**options, 'companies': [{'id': company.id, 'name': company.name}]}
                company_expressions_totals = self._compute_expression_totals_for_each_column_group(expressions_to_evaluate, company_options)
                company_carryover_values = {expression: company_expressions_totals[column_group_key][expression]['value'] for expression in carryover_expressions}
                self._create_carryover_for_company(options, company, company_carryover_values)

                for carryover_expr, carryover_val in company_carryover_values.items():
                    multi_company_carryover_values_sum[carryover_expr] += carryover_val

            # Adjust multicompany amounts on main company
            main_company = self._get_sender_company_for_export(options)
            for expr in carryover_expressions:
                difference = carryover_values[expr] - multi_company_carryover_values_sum[expr]
                self._create_carryover_for_company(options, main_company, {expr: difference}, label=_("Carryover adjustment for tax unit"))

    @api.model
    def _generate_default_external_values(self, date_from, date_to, is_tax_report=False):
        """ Generates the account.report.external.value objects for the given dates.
        If is_tax_report, the values are only created for tax reports, else for all other reports.
        """
        options_dict = {}
        default_expr_by_report = defaultdict(list)
        tax_report = self.env.ref('account.generic_tax_report')
        company = self.env.company
        previous_options = {
            'date': {
                'date_from': date_from,
                'date_to': date_to,
            }
        }

        # Get all the default expressions from all reports
        default_expressions = self.env['account.report.expression'].search([('label', '=like', '_default_%')])
        # Options depend on the report, also we need to filter out tax report/other reports depending on is_tax_report
        # Hence we need to group the default expressions by report
        for expr in default_expressions:
            report = expr.report_line_id.report_id
            if is_tax_report == (tax_report in (report + report.root_report_id + report.section_main_report_ids.root_report_id)):
                if report not in options_dict:
                    options = report.with_context(allowed_company_ids=[company.id]).get_options(previous_options)
                    options_dict[report] = options

                if report._is_available_for(options_dict[report]):
                    default_expr_by_report[report].append(expr)

        external_values_create_vals = []
        for report, report_default_expressions in default_expr_by_report.items():
            options = options_dict[report]
            fpos_options = {options['fiscal_position']}

            for available_fp in options['available_vat_fiscal_positions']:
                fpos_options.add(available_fp['id'])

            # remove 'all' from fiscal positions if we have several of them - all will then include the sum of other fps
            # but if there aren't any other fps, we need to keep 'all'
            if len(fpos_options) > 1 and 'all' in fpos_options:
                fpos_options.remove('all')

            # The default values should be created for every fiscal position available
            for fiscal_pos in fpos_options:
                fiscal_pos_id = int(fiscal_pos) if fiscal_pos not in {'domestic', 'all'} else None
                fp_options = {**options, 'fiscal_position': fiscal_pos}

                expressions_to_compute = {}
                for default_expression in report_default_expressions:
                    # The default expression needs to have the same label as the target external expression, e.g. '_default_balance'
                    target_label = default_expression.label[len('_default_'):]
                    target_external_expression = default_expression.report_line_id.expression_ids.filtered(lambda x: x.label == target_label)
                    # If the value has been created before/modified manually, we shouldn't create anything
                    # and we won't recompute expression totals for them
                    external_value = self.env['account.report.external.value'].search([
                        ('company_id', '=', company.id),
                        ('date', '>=', date_from),
                        ('date', '<=', date_to),
                        ('foreign_vat_fiscal_position_id', '=', fiscal_pos_id),
                        ('target_report_expression_id', '=', target_external_expression.id),
                    ])

                    if not external_value:
                        expressions_to_compute[default_expression] = target_external_expression.id

                # Evaluate the expressions for the report to fetch the value of the default expression
                # These have to be computed for each fiscal position
                expression_totals_per_col_group = report.with_company(company)\
                    ._compute_expression_totals_for_each_column_group(expressions_to_compute, fp_options, include_default_vals=True)
                expression_totals = expression_totals_per_col_group[list(fp_options['column_groups'].keys())[0]]

                for expression, target_expression in expressions_to_compute.items():
                    external_values_create_vals.append({
                        'name': _("Manual value"),
                        'value': expression_totals[expression]['value'],
                        'date': date_to,
                        'target_report_expression_id': target_expression,
                        'foreign_vat_fiscal_position_id': fiscal_pos_id,
                        'company_id': company.id,
                    })

        self.env['account.report.external.value'].create(external_values_create_vals)

    @api.model
    def _get_sender_company_for_export(self, options):
        """ Return the sender company when generating an export file from this report.
            :return: self.env.company if not using a tax unit, else the main company of that unit
        """
        if options.get('tax_unit', 'company_only') != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.main_company_id

        report_companies = self.env['res.company'].browse(self.get_report_company_ids(options))
        options_main_company = report_companies[0]

        if options.get('tax_unit') is not None and options_main_company._get_branches_with_same_vat() == report_companies:
            # The line with the smallest number of parents in the VAT sub-hierarchy is assumed to be the root
            return report_companies.sorted(lambda x: len(x.parent_ids))[0]
        elif options_main_company._all_branches_selected():
            return options_main_company.root_id

        return options_main_company

    def _create_carryover_for_company(self, options, company, carryover_per_expression, label=None):
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        fiscal_position_opt = options['fiscal_position']

        if carryover_per_expression and fiscal_position_opt == 'all':
            # Not supported, as it wouldn't make sense, and would make the code way more complicated (because of if_below/if_above/force_between,
            # just in the same way as it is explained below for multi company)
            raise UserError(_("Cannot generate carryover values for all fiscal positions at once!"))

        external_values_create_vals = []
        for expression, carryover_value in carryover_per_expression.items():
            if not company.currency_id.is_zero(carryover_value):
                target_expression = expression._get_carryover_target_expression(options)
                external_values_create_vals.append({
                    'name': label or _("Carryover from %s to %s", format_date(self.env, date_from), format_date(self.env, date_to)),
                    'value': carryover_value,
                    'date': date_to,
                    'target_report_expression_id': target_expression.id,
                    'foreign_vat_fiscal_position_id': fiscal_position_opt if isinstance(fiscal_position_opt, int) else None,
                    'carryover_origin_expression_label': expression.label,
                    'carryover_origin_report_line_id': expression.report_line_id.id,
                    'company_id': company.id,
                })

        self.env['account.report.external.value'].create(external_values_create_vals)

    def get_default_report_filename(self, options, extension):
        """The default to be used for the file when downloading pdf,xlsx,..."""
        self.ensure_one()

        sections_source_id = options['sections_source_id']
        if sections_source_id != self.id:
            sections_source = self.env['account.report'].browse(sections_source_id)
        else:
            sections_source = self

        return f"{sections_source.name.lower().replace(' ', '_')}.{extension}"

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].sudo().browse([action_id])
        action_type = action.type
        action = self.env[action.type].sudo().browse([action_id])
        action_read = clean_action(action.read()[0], env=action.env)

        if action_type == 'ir.actions.client':
            # Check if we are opening another report. If so, generate options for it from the current options.
            if action.tag == 'account_report':
                target_report = self.env['account.report'].browse(ast.literal_eval(action_read['context'])['report_id'])
                new_options = target_report.get_options(previous_options=options)
                action_read.update({'params': {'options': new_options, 'ignore_session': True}})

        if params.get('id'):
            # Add the id of the calling object in the action's context
            if isinstance(params['id'], int):
                # id of the report line might directly be the id of the model we want.
                model_id = params['id']
            else:
                # It can also be a generic account.report id, as defined by _get_generic_line_id
                model_id = self._get_model_info_from_id(params['id'])[1]

            context = action_read.get('context') and literal_eval(action_read['context']) or {}
            context.setdefault('active_id', model_id)
            action_read['context'] = context

        return action_read

    def action_audit_cell(self, options, params):
        report_line = self.env['account.report.line'].browse(params['report_line_id'])
        expression_label = params['expression_label']
        expression = report_line.expression_ids.filtered(lambda x: x.label == expression_label)
        column_group_options = self._get_column_group_options(options, params['column_group_key'])

        # Audit of external values
        if expression.engine == 'external':
            date_from, date_to, dummy = self._get_date_bounds_info(column_group_options, expression.date_scope)
            external_values_domain = [('target_report_expression_id', '=', expression.id), ('date', '<=', date_to)]
            if date_from:
                external_values_domain.append(('date', '>=', date_from))

            if expression.formula == 'most_recent':
                tables, where_clause, where_params = self.env['account.report.external.value']._where_calc(external_values_domain).get_sql()
                self._cr.execute(f"""
                    SELECT ARRAY_AGG(id)
                    FROM {tables}
                    WHERE {where_clause}
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """, where_params)
                record_ids = self._cr.fetchone()
                if record_ids:
                    external_values_domain = [('id', 'in', record_ids[0])]

            return {
                'name': _("Manual values"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.report.external.value',
                'view_mode': 'list',
                'views': [(False, 'list')],
                'domain': external_values_domain,
            }

        # Audit of move lines
        # If we're auditing a groupby line, we need to make sure to restrict the result of what we audit to the right group values
        column = next(col for col in report_line.report_id.column_ids if col.expression_label == expression_label)
        if column.custom_audit_action_id:
            action_dict = column.custom_audit_action_id._get_action_dict()
        else:
            action_dict = {
                'name': _("Journal Items"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.line',
                'view_mode': 'list',
                'views': [(False, 'list')],
            }

        action = clean_action(action_dict, env=self.env)
        action['domain'] = self._get_audit_line_domain(column_group_options, expression, params)
        return action

    def action_view_all_variants(self, options, params):
        return {
            'name': _('All Report Variants'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.report',
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
            'context': {
                'active_test': False,
            },
            'domain': [('id', 'in', self._get_variants(options['variants_source_id']).filtered(
                lambda x: x._is_available_for(options)
            ).mapped('id'))],
        }

    def _get_audit_line_domain(self, column_group_options, expression, params):
        groupby_domain = self._get_audit_line_groupby_domain(params['calling_line_dict_id'])
        # Aggregate all domains per date scope, then create the final domain.
        audit_or_domains_per_date_scope = {}
        for expression_to_audit in expression._expand_aggregations():
            expression_domain = self._get_expression_audit_aml_domain(expression_to_audit, column_group_options)

            if expression_domain is None:
                continue

            date_scope = expression.date_scope if expression.subformula == 'cross_report' else expression_to_audit.date_scope
            audit_or_domains = audit_or_domains_per_date_scope.setdefault(date_scope, [])
            audit_or_domains.append(osv.expression.AND([
                expression_domain,
                groupby_domain,
            ]))

        if audit_or_domains_per_date_scope:
            domain = osv.expression.OR([
                osv.expression.AND([
                    osv.expression.OR(audit_or_domains),
                    self._get_options_domain(column_group_options, date_scope),
                    groupby_domain,
                ])
                for date_scope, audit_or_domains in audit_or_domains_per_date_scope.items()
            ])
        else:
            # Happens when no expression was provided (empty recordset), or if none of the expressions had a standard engine
            domain = osv.expression.AND([
                self._get_options_domain(column_group_options, 'strict_range'),
                groupby_domain,
            ])

        # Analytic Filter
        if column_group_options.get("analytic_accounts"):
            domain = osv.expression.AND([
                domain,
                [("analytic_distribution", "in", column_group_options["analytic_accounts"])],
            ])

        return domain

    def _get_audit_line_groupby_domain(self, calling_line_dict_id):
        parsed_line_dict_id = self._parse_line_id(calling_line_dict_id)
        groupby_domain = []
        for markup, dummy, model_id in parsed_line_dict_id:
            groupby_match = re.match("groupby:(?P<groupby_field>.*)", markup)
            if groupby_match:
                groupby_domain.append((groupby_match['groupby_field'], '=', model_id))
        return groupby_domain

    def _get_expression_audit_aml_domain(self, expression_to_audit, options):
        """ Returns the domain used to audit a single provided expression.

        'account_codes' engine's D and C formulas can't be handled by a domain: we make the choice to display
        everything for them (so, audit shows all the lines that are considered by the formula). To avoid confusion from the user
        when auditing such lines, a default group by account can be used in the tree view.
        """
        if expression_to_audit.engine == 'account_codes':
            formula = expression_to_audit.formula.replace(' ', '')

            account_codes_domains = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(' ', '')):
                if token:
                    match_dict = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token).groupdict()
                    tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(match_dict['prefix'])
                    account_codes_domain = []

                    if tag_match:
                        if tag_match['ref']:
                            tag_id = self.env['ir.model.data']._xmlid_to_res_id(tag_match['ref'])
                        else:
                            tag_id = int(tag_match['id'])

                        account_codes_domain.append(('account_id.tag_ids', 'in', [tag_id]))
                    else:
                        account_codes_domain.append(('account_id.code', '=like', f"{match_dict['prefix']}%"))

                    excluded_prefix_str = match_dict['excluded_prefixes']
                    if excluded_prefix_str:
                        for excluded_prefix in excluded_prefix_str.split(','):
                            # "'not like', prefix%" doesn't work
                            account_codes_domain += ['!', ('account_id.code', '=like', f"{excluded_prefix}%")]

                    account_codes_domains.append(account_codes_domain)

            return osv.expression.OR(account_codes_domains)

        if expression_to_audit.engine == 'tax_tags':
            tags = self.env['account.account.tag']._get_tax_tags(expression_to_audit.formula, expression_to_audit.report_line_id.report_id.country_id.id)
            return [('tax_tag_ids', 'in', tags.ids)]

        if expression_to_audit.engine == 'domain':
            return ast.literal_eval(expression_to_audit.formula)

        return None

    def open_journal_items(self, options, params):
        ''' Open the journal items view with the proper filters and groups '''
        record_model, record_id = self._get_model_info_from_id(params.get('line_id'))
        view_id = self.env.ref(params['view_ref']).id if params.get('view_ref') else None

        ctx = {
            'search_default_group_by_account': 1,
            'search_default_posted': 0 if options.get('all_entries') else 1,
            'date_from': options.get('date').get('date_from'),
            'date_to': options.get('date').get('date_to'),
            'search_default_journal_id': params.get('journal_id', False),
            'expand': 1,
        }

        if options['date'].get('date_from'):
            ctx['search_default_date_between'] = 1
        else:
            ctx['search_default_date_before'] = 1

        journal_type = params.get('journal_type')
        if journal_type:
            type_to_view_param = {
                'bank': {
                    'filter': 'search_default_bank',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id
                },
                'cash': {
                    'filter': 'search_default_cash',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id
                },
                'general': {
                    'filter': 'search_default_misc_filter',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_misc').id
                },
                'sale': {
                    'filter': 'search_default_sales',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_sales_purchases').id
                },
                'purchase': {
                    'filter': 'search_default_purchases',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_sales_purchases').id
                },
            }
            ctx.update({
                type_to_view_param[journal_type]['filter']: 1,
            })
            view_id = type_to_view_param[journal_type]['view_id']

        action_domain = [('display_type', 'not in', ('line_section', 'line_note'))]

        if record_id is None:
            # Default filters don't support the 'no set' value. For this case, we use a domain on the action instead
            model_fields_map = {
                'account.account': 'account_id',
                'res.partner': 'partner_id',
                'account.journal': 'journal_id',
            }
            model_field = model_fields_map.get(record_model)
            if model_field:
                action_domain += [(model_field, '=', False)]
        else:
            model_default_filters = {
                'account.account': 'search_default_account_id',
                'res.partner': 'search_default_partner_id',
                'account.journal': 'search_default_journal_id',
            }
            model_filter = model_default_filters.get(record_model)
            if model_filter:
                ctx.update({
                    'active_id': record_id,
                    model_filter: [record_id],
                })

        if options:
            for account_type in options.get('account_type', []):
                ctx.update({
                    f"search_default_{account_type['id']}": account_type['selected'] and 1 or 0,
                })

            if options.get('journals') and 'search_default_journal_id' not in ctx:
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if len(selected_journals) == 1:
                    ctx['search_default_journal_id'] = selected_journals

            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                ctx.update({
                    'search_default_analytic_accounts': 1,
                    'analytic_ids': analytic_ids,
                })

        return {
            'name': self._get_action_name(params, record_model, record_id),
            'view_mode': 'tree,pivot,graph,kanban',
            'res_model': 'account.move.line',
            'views': [(view_id, 'list')],
            'type': 'ir.actions.act_window',
            'domain': action_domain,
            'context': ctx,
        }

    def open_unposted_moves(self, options, params=None):
        ''' Open the list of draft journal entries that might impact the reporting'''
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        action['domain'] = [('state', '=', 'draft'), ('date', '<=', options['date']['date_to'])]
        #overwrite the context to avoid default filtering on 'misc' journals
        action['context'] = {}
        return action

    def _get_generated_deferral_entries_domain(self, options):
        """Get the search domain for the generated deferral entries of the current period.

        :param options: the report's `options` dict containing `date_from`, `date_to` and `deferred_report_type`
        :return: a search domain that can be used to get the deferral entries
        """
        if options.get('deferred_report_type') == 'expense':
            account_types = ('expense', 'expense_depreciation', 'expense_direct_cost')
        else:
            account_types = ('income', 'income_other')
        date_to = fields.Date.from_string(options['date']['date_to'])
        date_to_next_reversal = fields.Date.to_string(date_to + datetime.timedelta(days=1))
        return [
            ('company_id', '=', self.env.company.id),
            # We exclude the reversal entries of the previous period that fall on the first day of this period
            ('date', '>', options['date']['date_from']),
            # We include the reversal entries of the current period that fall on the first day of the next period
            ('date', '<=', date_to_next_reversal),
            ('deferred_original_move_ids', '!=', False),
            ('line_ids.account_id.account_type', 'in', account_types),
            ('state', '!=', 'cancel'),
        ]

    def open_deferral_entries(self, options, params):
        domain = self._get_generated_deferral_entries_domain(options)
        deferral_line_ids = self.env['account.move'].search(domain).line_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entries'),
            'res_model': 'account.move.line',
            'domain': [('id', 'in', deferral_line_ids)],
            'views': [(False, 'tree'), (False, 'form')],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            }
        }

    def action_modify_manual_value(self, options, column_group_key, new_value_str, target_expression_id, rounding, json_friendly_column_group_totals):
        """ Edit a manual value from the report, updating or creating the corresponding account.report.external.value object.

        :param options: The option dict the report is evaluated with.

        :param column_group_key: The string identifying the column group into which the change as manual value needs to be done.

        :param new_value_str: The new value to be set, as a string.

        :param rounding: The number of decimal digits to round with.

        :param json_friendly_column_group_totals: The expression totals by column group already computed for this report, in the format returned
                                                  by _get_json_friendly_column_group_totals. These will be used to reevaluate the report, recomputing
                                                  only the expressions depending on the newly-modified manual value, and keeping all the results
                                                  from the previous computations for the other ones.
        """
        self.ensure_one()

        if len(options['companies']) > 1:
            raise UserError(_("Editing a manual report line is not allowed when multiple companies are selected."))

        if options['fiscal_position'] == 'all' and options['available_vat_fiscal_positions']:
            raise UserError(_("Editing a manual report line is not allowed in multivat setup when displaying data from all fiscal positions."))

        target_column_group_options = self._get_column_group_options(options, column_group_key)
        expressions_to_recompute = self.line_ids.expression_ids.filtered(lambda x: x.engine in ('external', 'aggregation')) # Only those lines' values can be impacted

        # Create the manual value
        target_expression = self.env['account.report.expression'].browse(target_expression_id)
        date_from, date_to, dummy = self._get_date_bounds_info(target_column_group_options, target_expression.date_scope)
        fiscal_position_id = target_column_group_options['fiscal_position'] if isinstance(target_column_group_options['fiscal_position'], int) else False

        external_values_domain = [
            ('target_report_expression_id', '=', target_expression.id),
            ('company_id', '=', self.env.company.id),
            ('foreign_vat_fiscal_position_id', '=', fiscal_position_id),
        ]

        if target_expression.formula == 'most_recent':
            value_to_adjust = 0
            existing_value_to_modify = self.env['account.report.external.value'].search([
                *external_values_domain,
                ('date', '=', date_to),
            ])

            # There should be at most 1
            if len(existing_value_to_modify) > 1:
                raise UserError(_("Inconsistent data: more than one external value at the same date for a 'most_recent' external line."))
        else:
            existing_external_values = self.env['account.report.external.value'].search([
                *external_values_domain,
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ], order='date ASC')
            existing_value_to_modify = existing_external_values[-1] if existing_external_values and str(existing_external_values[-1].date) == date_to  else None
            value_to_adjust = sum(existing_external_values.filtered(lambda x: x != existing_value_to_modify).mapped('value'))

        if not new_value_str and target_expression.figure_type != 'string':
            new_value_str = '0'

        try:
            float(new_value_str)
            is_number = True
        except ValueError:
            is_number = False

        if target_expression.figure_type == 'string':
            value_to_set = new_value_str
        else:
            if not is_number:
                raise UserError(_("%s is not a numeric value", new_value_str))
            if target_expression.figure_type == 'boolean':
                rounding = 0
            value_to_set = float_round(float(new_value_str) - value_to_adjust, precision_digits=rounding)

        field_name = 'value' if target_expression.figure_type != 'string' else 'text_value'

        if existing_value_to_modify:
            existing_value_to_modify[field_name] = value_to_set
            existing_value_to_modify.flush_recordset()
        else:
            self.env['account.report.external.value'].create({
                'name': _("Manual value"),
                field_name: value_to_set,
                'date': date_to,
                'target_report_expression_id': target_expression.id,
                'company_id': self.env.company.id,
                'foreign_vat_fiscal_position_id': fiscal_position_id,
            })

        # We recompute values for each column group, not only the one we modified a value in; this is important in case some date_scope is used to
        # retrieve the manual value from a previous period.

        # json_friendly_column_group_totals contains ids instead of expressions (because it comes from js) ; we need to convert them back to records
        all_column_groups_expression_totals = {}

        for column_group_key, expression_totals in json_friendly_column_group_totals.items():
            all_column_groups_expression_totals[column_group_key] = {}
            for expr_id, expr_totals in expression_totals.items():
                expression = self.env['account.report.expression'].browse(int(expr_id))  # Should already be in cache, so acceptable
                if expression not in expressions_to_recompute:
                    all_column_groups_expression_totals[column_group_key][expression] = expr_totals

        recomputed_expression_totals = self._compute_expression_totals_for_each_column_group(
            expressions_to_recompute, options, forced_all_column_groups_expression_totals=all_column_groups_expression_totals)

        return {
            'lines': self._get_lines(options, all_column_groups_expression_totals=recomputed_expression_totals),
            'column_groups_totals': self._get_json_friendly_column_group_totals(recomputed_expression_totals),
        }

    def action_display_inactive_sections(self, options):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Enable Sections"),
            'view_mode': 'tree,form',
            'res_model': 'account.report',
            'domain': [('section_main_report_ids', 'in', options['sections_source_id']), ('active', '=', False)],
            'views': [(False, 'list'), (False, 'form')],
            'context': {
                'tree_view_ref': 'account_reports.account_report_add_sections_tree',
                'active_test': False,
            },
        }

    @api.model
    def sort_lines(self, lines, options, result_as_index=False):
        ''' Sort report lines based on the 'order_column' key inside the options.
        The value of options['order_column'] is an integer, positive or negative, indicating on which column
        to sort and also if it must be an ascending sort (positive value) or a descending sort (negative value).
        Note that for this reason, its indexing is made starting at 1, not 0.
        If this key is missing or falsy, lines is returned directly.

        This method has some limitations:
        - The selected_column must have 'sortable' in its classes.
        - All lines are sorted expect those having the 'total' class.
        - This only works when each line has an unique id.
        - All lines inside the selected_column must have a 'no_format' value.

        Example:

        parent_line_1           balance=11
            child_line_1        balance=1
            child_line_2        balance=3
            child_line_3        balance=2
            child_line_4        balance=7
            child_line_5        balance=4
            child_line_6        (total line)
        parent_line_2           balance=10
            child_line_7        balance=5
            child_line_8        balance=6
            child_line_9        (total line)


        The resulting lines will be:

        parent_line_2           balance=10
            child_line_7        balance=5
            child_line_8        balance=6
            child_line_9        (total line)
        parent_line_1           balance=11
            child_line_1        balance=1
            child_line_3        balance=2
            child_line_2        balance=3
            child_line_5        balance=4
            child_line_4        balance=7
            child_line_6        (total line)

        :param lines:   The report lines.
        :param options: The report options.
        :return:        Lines sorted by the selected column.
        '''
        def needs_to_be_at_bottom(line_elem):
            return self._get_markup(line_elem.get('id')) in ('total', 'load_more')

        def compare_values(a_line, b_line):
            type_seq = {
                type(None): 0,
                bool: 1,
                float: 2,
                int: 2,
                str: 3,
                datetime.date: 4,
                datetime.datetime: 5,
            }

            a_line_dict = lines[a_line] if result_as_index else a_line
            b_line_dict = lines[b_line] if result_as_index else b_line
            a_total = needs_to_be_at_bottom(a_line_dict)
            b_total = needs_to_be_at_bottom(b_line_dict)

            if a_total:
                if b_total:  # a_total & b_total
                    return 0
                else:    # a_total & !b_total
                    return -1 if descending else 1
            if b_total:  # => !a_total & b_total
                return 1 if descending else -1

            a_val = a_line_dict['columns'][column_index].get('no_format')
            b_val = b_line_dict['columns'][column_index].get('no_format')
            type_a, type_b = type_seq[type(a_val)], type_seq[type(b_val)]

            if type_a == type_b:
                return 0 if a_val == b_val else 1 if a_val > b_val else -1
            else:
                return type_a - type_b

        def merge_tree(tree_elem, ls):
            nonlocal descending  # The direction of the sort is needed to compare total lines
            ls.append(tree_elem)

            elem = tree[lines[tree_elem]['id']] if result_as_index else tree[tree_elem['id']]

            for tree_subelem in sorted(elem, key=comp_key, reverse=descending):
                merge_tree(tree_subelem, ls)

        descending = options['order_column']['direction'] == 'DESC' # To keep total lines at the end, used in compare_values & merge_tree scopes

        for index, col in enumerate(options['columns']):
            if options['order_column']['expression_label'] == col['expression_label']:
                column_index = index # To know from which column to sort, used in merge_tree scope
                break

        comp_key = cmp_to_key(compare_values)
        sorted_list = []
        tree = defaultdict(list)
        non_total_parents = set()

        for index, line in enumerate(lines):
            line_parent = line.get('parent_id') or None

            if result_as_index:
                tree[line_parent].append(index)
            else:
                tree[line_parent].append(line)

            line_markup = self._get_markup(line['id'])

            if line_markup != 'total':
                non_total_parents.add(line_parent)

        if None not in tree and len(non_total_parents) == 1:
            # Happens when unfolding a groupby line, to sort its children.
            sorting_root = next(iter(non_total_parents))
        else:
            sorting_root = None

        for line in sorted(tree[sorting_root], key=comp_key, reverse=descending):
            merge_tree(line, sorted_list)

        return sorted_list

    def get_footnotes(self, options):
        self.ensure_one()

        footnotes = {}

        for footnote in self.env['account.report.footnote'].search_read([('report_id', '=', options['report_id'])]):
            footnotes[footnote['line_id']] = footnote

        return footnotes

    def get_report_information(self, options):
        """
        return a dictionary of information that will be consumed by the AccountReport component.
        """
        self.ensure_one()

        warnings = {}
        all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(self.line_ids.expression_ids, options, warnings=warnings)

        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = self._get_json_friendly_column_group_totals(all_column_groups_expression_totals)

        return {
            'caret_options': self._get_caret_options(),
            'column_headers_render_data': self._get_column_headers_render_data(options),
            'column_groups_totals': json_friendly_column_group_totals,
            'context': self.env.context,
            'custom_display': self.env[self.custom_handler_model_name]._get_custom_display_config() if self.custom_handler_model_name else {},
            'filters': {
                'show_all': self.filter_unfold_all,
                'show_analytic': options.get('display_analytic', False),
                'show_analytic_groupby': options.get('display_analytic_groupby', False),
                'show_analytic_plan_groupby': options.get('display_analytic_plan_groupby', False),
                'show_draft': self.filter_show_draft,
                'show_hierarchy': options.get('display_hierarchy_filter', False),
                'show_period_comparison': self.filter_period_comparison,
                'show_totals': self.env.company.totals_below_sections and not options.get('ignore_totals_below_sections'),
                'show_unreconciled': self.filter_unreconciled,
                'show_hide_0_lines': self.filter_hide_0_lines,
            },
            'footnotes': self.get_footnotes(options),
            'groups': {
                'analytic_accounting': self.user_has_groups('analytic.group_analytic_accounting'),
                'account_readonly': self.user_has_groups('account.group_account_readonly'),
                'account_user': self.user_has_groups('account.group_account_user'),
            },
            'lines': self._get_lines(options, all_column_groups_expression_totals=all_column_groups_expression_totals, warnings=warnings),
            'warnings': warnings,
            'report': {
                'company_name': self.env.company.name,
                'company_country_code': self.env.company.country_code,
                'company_currency_symbol': self.env.company.currency_id.symbol,
                'name': self.name,
                'root_report_id': self.root_report_id,
            }
        }

    def _get_json_friendly_column_group_totals(self, all_column_groups_expression_totals):
        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = {}
        for column_group_key, expressions_totals in all_column_groups_expression_totals.items():
            json_friendly_column_group_totals[column_group_key] = {expression.id: totals for expression, totals in expressions_totals.items()}
        return json_friendly_column_group_totals

    def _is_available_for(self, options):
        """ Called on report variants to know whether they are available for the provided options or not, computed for their root report,
        computing their availability_condition field.

        Note that only the options initialized by the init_options with a more prioritary sequence than _init_options_variants are guaranteed to
        be in the provided options' dict (since this function is called by _init_options_variants, while resolving a call to get_options()).
        """
        self.ensure_one()

        companies = self.env['res.company'].browse(self.get_report_company_ids(options))

        if self.availability_condition == 'country':
            countries = companies.account_fiscal_country_id
            if self.filter_fiscal_position:
                foreign_vat_fpos = self.env['account.fiscal.position'].search([
                    ('foreign_vat', '!=', False),
                    ('company_id', 'in', companies.ids),
                ])
                countries += foreign_vat_fpos.country_id

            return not self.country_id or self.country_id in countries

        elif self.availability_condition == 'coa':
            # When restricting to 'coa', the report is only available is all the companies have the same CoA as the report
            return {self.chart_template} == set(companies.mapped('chart_template'))

        return True

    def _get_column_headers_render_data(self, options):
        column_headers_render_data = {}

        # We only want to consider the columns that are visible in the current report and don't rely on self.column_ids
        # since custom reports could alter them (e.g. for multi-currency purposes)
        columns = [col for col in options['columns'] if col['column_group_key'] == next(k for k in options['column_groups'])]

        # Compute the colspan of each header level, aka the number of single columns it contains at the base of the hierarchy
        level_colspan_list = column_headers_render_data['level_colspan'] = []
        for i in range(len(options['column_headers'])):
            colspan = max(len(columns), 1)
            for column_header in options['column_headers'][i + 1:]:
                colspan *= len(column_header)
            level_colspan_list.append(colspan)

        # Compute the number of times each header level will have to be repeated, and its colspan to properly handle horizontal groups/comparisons
        column_headers_render_data['level_repetitions'] = []
        for i in range(len(options['column_headers'])):
            colspan = 1
            for column_header in options['column_headers'][:i]:
                colspan *= len(column_header)
            column_headers_render_data['level_repetitions'].append(colspan)

        # Custom reports have the possibility to define custom subheaders that will be displayed between the generic header and the column names.
        column_headers_render_data['custom_subheaders'] = options.get('custom_columns_subheaders', []) * len(options['column_groups'])

        return column_headers_render_data

    def _get_action_name(self, params, record_model=None, record_id=None):
        if not (record_model or record_id):
            record_model, record_id = self._get_model_info_from_id(params.get('line_id'))
        return params.get('name') or self.env[record_model].browse(record_id).display_name or ''

    def _format_lines_for_display(self, lines, options):
        """
        This method should be overridden in a report in order to apply specific formatting when printing
        the report lines.

        Used for example by the carryover functionnality in the generic tax report.
        :param lines: A list with the lines for this report.
        :param options: The options for this report.
        :return: The formatted list of lines
        """
        return lines

    def get_expanded_lines(self, options, line_dict_id, groupby, expand_function_name, progress, offset):
        lines = self._expand_unfoldable_line(expand_function_name, line_dict_id, groupby, options, progress, offset)
        lines = self._fully_unfold_lines_if_needed(lines, options)

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(self, options, lines)

        return lines
    def _expand_unfoldable_line(self, expand_function_name, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        if not expand_function_name:
            raise UserError(_("Trying to expand a line without an expansion function."))

        if not progress:
            progress = {column_group_key: 0 for column_group_key in options['column_groups']}

        expand_function = self._get_custom_report_function(expand_function_name, 'expand_unfoldable_line')
        expansion_result = expand_function(line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=unfold_all_batch_data)

        rslt = expansion_result['lines']
        if expansion_result.get('has_more'):
            # We only add load_more line for groupby
            next_offset = offset + expansion_result['offset_increment']
            rslt.append(self._get_load_more_line(next_offset, line_dict_id, expand_function_name, groupby, expansion_result.get('progress', 0), options))

        # In some specific cases, we may want to add lines that are always at the end. So they need to be added after the load more line.
        if expansion_result.get('after_load_more_lines'):
            rslt.extend(expansion_result['after_load_more_lines'])

        return self._add_totals_below_sections(rslt, options)

    def _add_totals_below_sections(self, lines, options):
        """ Returns a new list, corresponding to lines with the required total lines added as sublines of the sections it contains.
        """
        if not self.env.company.totals_below_sections or options.get('ignore_totals_below_sections'):
            return lines

        # Gather the lines needing the totals
        lines_needing_total_below = set()
        for line_dict in lines:
            line_markup = self._get_markup(line_dict['id'])

            if line_markup != 'total':
                # If we are on the first level of an expandable line, we arelady generate its total
                if line_dict.get('unfoldable') or (line_dict.get('unfolded') and line_dict.get('expand_function')):
                    lines_needing_total_below.add(line_dict['id'])

                # All lines that are parent of other lines need to receive a total
                line_parent_id = line_dict.get('parent_id')
                if line_parent_id:
                    lines_needing_total_below.add(line_parent_id)

        # Inject the totals
        if lines_needing_total_below:
            lines_with_totals_below = []
            totals_below_stack = []
            for line_dict in lines:
                while totals_below_stack and not line_dict['id'].startswith(totals_below_stack[-1]['parent_id'] + LINE_ID_HIERARCHY_DELIMITER):
                    lines_with_totals_below.append(totals_below_stack.pop())

                lines_with_totals_below.append(line_dict)

                if line_dict['id'] in lines_needing_total_below and any(col.get('no_format') is not None for col in line_dict['columns']):
                    totals_below_stack.append(self._generate_total_below_section_line(line_dict))

            while totals_below_stack:
                lines_with_totals_below.append(totals_below_stack.pop())

            return lines_with_totals_below

        return lines

    @api.model
    def _get_load_more_line(self, offset, parent_line_id, expand_function_name, groupby, progress, options):
        """ Returns a 'Load more' line allowing to reach the subsequent elements of an unfolded line with an expand function if the maximum
        limit of sublines is reached (we load them by batch, using the load_more_limit field's value).

        :param offset: The offset to be passed to the expand function to generate the next results, when clicking on this 'load more' line.

        :param parent_line_id: The generic id of the line this load more line is created for.

        :param expand_function_name: The name of the expand function this load_more is created for (so, the one of its parent).

        :param progress: A json-formatted dict(column_group_key, value) containing the progress value for each column group, as it was
                         returned by the expand function. This is for example used by reports such as the general ledger, whose lines display a c
                         cumulative sum of their balance and the one of all the previous lines under the same parent. In this case, progress
                         will be the total sum of all the previous lines before the load_more line, that the subsequent lines will need to use as
                         base for their own cumulative sum.

        :param options: The options dict corresponding to this report's state.
        """
        return {
            'id': self._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='load_more'),
            'name': _("Load more..."),
            'parent_id': parent_line_id,
            'expand_function': expand_function_name,
            'columns': [{} for col in options['columns']],
            'unfoldable': False,
            'unfolded': False,
            'offset': offset,
            'groupby': groupby, # We keep the groupby value from the parent, so that it can be propagated through js
            'progress': progress,
        }

    def _report_expand_unfoldable_line_with_groupby(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # The line we're expanding might be an inner groupby; we first need to find the report line generating it
        report_line_id = None
        for dummy, model, model_id in reversed(self._parse_line_id(line_dict_id)):
            if model == 'account.report.line':
                report_line_id = model_id
                break

        if report_line_id is None:
            raise UserError(_("Trying to expand a group for a line which was not generated by a report line: %s", line_dict_id))

        line = self.env['account.report.line'].browse(report_line_id)

        if ',' not in groupby and options['export_mode'] is None:
            # if ',' not in groupby, then its a terminal groupby (like 'id' in 'partner_id, id'), so we can use the 'load more' feature if necessary
            # When printing, we want to ignore the limit.
            limit_to_load = self.load_more_limit or None
        else:
            # Else, we disable it
            limit_to_load = None
            offset = 0

        rslt_lines = line._expand_groupby(line_dict_id, groupby, options, offset=offset, limit=limit_to_load, load_one_more=bool(limit_to_load), unfold_all_batch_data=unfold_all_batch_data)
        lines_to_load = rslt_lines[:self.load_more_limit] if limit_to_load else rslt_lines

        if not limit_to_load and options['export_mode'] is None:
            lines_to_load = self._regroup_lines_by_name_prefix(options, rslt_lines, '_report_expand_unfoldable_line_groupby_prefix_group', line.hierarchy_level,
                                                               groupby=groupby, parent_line_dict_id=line_dict_id)

        return {
            'lines': lines_to_load,
            'offset_increment': len(lines_to_load),
            'has_more': len(lines_to_load) < len(rslt_lines) if limit_to_load else False,
        }

    def _regroup_lines_by_name_prefix(self, options, lines_to_group, expand_function_name, parent_level, matched_prefix='', groupby=None, parent_line_dict_id=None):
        """ Postprocesses a list of report line dictionaries in order to regroup them by name prefix and reduce the overall number of lines
        if their number is above a provided threshold (set in the report configuration).

        The lines regrouped under a common prefix will be removed from the returned list of lines; only the prefix line will stay, folded.
        Its expand function must ensure the right sublines are reloaded when unfolding it.

        :param options: Option dict for this report.
        :lines_to_group: The lines list to regroup by prefix if necessary. They must all have the same parent line (which might be no line at all).
        :expand_function_name: Name of the expand function to be called on created prefix group lines, when unfolding them
        :parent_level: Level of the parent line, which generated the lines in lines_to_group. It will be used to compute the level of the prefix group lines.
        :matched_prefix': A string containing the parent prefix that's already matched. For example, when computing prefix 'ABC', matched_prefix will be 'AB'.
        :groupby: groupby value of the parent line, which generated the lines in lines_to_group.
        :parent_line_dict_id: id of the parent line, which generated the lines in lines_to_group.

        :return: lines_to_group, grouped by prefix if it was necessary.
        """
        threshold = options['prefix_groups_threshold']

        # When grouping by prefix, we ignore the totals
        lines_to_group_without_totals = list(filter(lambda x: self._get_markup(x['id']) != 'total', lines_to_group))

        if options['export_mode'] == 'print' or threshold <= 0 or len(lines_to_group_without_totals) < threshold:
            # No grouping needs to be done
            return lines_to_group

        char_index = len(matched_prefix)
        prefix_groups = defaultdict(list)
        rslt = []
        for line in lines_to_group_without_totals:
            line_name = line['name'].strip()

            if len(line_name) - 1 < char_index:
                rslt.append(line)
            else:
                prefix_groups[line_name[char_index].lower()].append(line)

        float_figure_types = {'monetary', 'integer', 'float'}
        unfold_all = options['export_mode'] == 'print' or options.get('unfold_all')
        for prefix_key, prefix_sublines in sorted(prefix_groups.items(), key=lambda x: x[0]):
            # Compute the total of this prefix line, summming all of its content
            prefix_expression_totals_by_group = {}
            for column_index, column_data in enumerate(options['columns']):
                if column_data['figure_type'] in float_figure_types:
                    # Then we want to sum this column's value in our children
                    for prefix_subline in prefix_sublines:
                        prefix_expr_label_result = prefix_expression_totals_by_group.setdefault(column_data['column_group_key'], {})
                        prefix_expr_label_result.setdefault(column_data['expression_label'], 0)
                        prefix_expr_label_result[column_data['expression_label']] += (prefix_subline['columns'][column_index]['no_format'] or 0)

            column_values = []
            for column in options['columns']:
                col_value = prefix_expression_totals_by_group.get(column['column_group_key'], {}).get(column['expression_label'])

                column_values.append(self._build_column_dict(col_value, column, options=options))

            line_id = self._get_generic_line_id(None, None, parent_line_id=parent_line_dict_id, markup=f"groupby_prefix_group:{prefix_key}")

            sublines_nber = len(prefix_sublines)
            prefix_to_display = prefix_key.upper()

            if re.match(r'\s', prefix_to_display[-1]):
                # In case the last character of the prefix to_display is blank, replace it by "[ ]", to make the space more visible to the user.
                prefix_to_display = f'{prefix_to_display[:-1]}[ ]'

            if sublines_nber == 1:
                prefix_group_line_name = f"{matched_prefix}{prefix_to_display} " + _("(1 line)")
            else:
                prefix_group_line_name = f"{matched_prefix}{prefix_to_display} " + _("(%s lines)", sublines_nber)

            prefix_group_line = {
                'id': line_id,
                'name': prefix_group_line_name,
                'unfoldable': True,
                'unfolded': unfold_all or line_id in options['unfolded_lines'],
                'columns': column_values,
                'groupby': groupby,
                'level': parent_level + 1,
                'parent_id': parent_line_dict_id,
                'expand_function': expand_function_name,
            }
            rslt.append(prefix_group_line)

        return rslt

    def _report_expand_unfoldable_line_groupby_prefix_group(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        """ Expand function used by prefix_group lines generated for groupby lines.
        """
        report_line_id = None
        parent_groupby_count = 0
        for markup, model, model_id in reversed(self._parse_line_id(line_dict_id)):
            if model == 'account.report.line':
                report_line_id = model_id
                break
            elif markup.startswith('groupby'): # for groupby: and groupby_prefix_group:
                parent_groupby_count += 1

        if report_line_id is None:
            raise UserError(_("Trying to expand a group for a line which was not generated by a report line: %s", line_dict_id))

        report_line = self.env['account.report.line'].browse(report_line_id)


        matched_prefix = self._get_prefix_groups_matched_prefix_from_line_id(line_dict_id)
        first_groupby = groupby.split(',')[0]
        expand_options = {
            **options,
            'forced_domain': options.get('forced_domain', []) + [(f"{f'{first_groupby}.' if first_groupby != 'id' else ''}name", '=ilike', f'{matched_prefix}%')]
        }
        expanded_groupby_lines = report_line._expand_groupby(line_dict_id, groupby, expand_options)
        parent_level = report_line.hierarchy_level + parent_groupby_count * 2

        lines = self._regroup_lines_by_name_prefix(
            options,
            expanded_groupby_lines,
            '_report_expand_unfoldable_line_groupby_prefix_group',
            parent_level,
            groupby=groupby,
            matched_prefix=matched_prefix,
            parent_line_dict_id=line_dict_id,
        )

        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }

    @api.model
    def _get_prefix_groups_matched_prefix_from_line_id(self, line_dict_id):
        matched_prefix = ''
        for markup, dummy1, dummy2 in self._parse_line_id(line_dict_id):
            if markup and markup.startswith('groupby_prefix_group'):
                prefix_piece = markup.split(':')[1]
                matched_prefix += prefix_piece.upper()
            else:
                # Might happen if a groupby is grouped by prefix, then a subgroupby is grouped by another subprefix.
                # In this case, we want to reset the prefix group to only consider the one used in the subgroupby.
                matched_prefix = ''

        return matched_prefix

    @api.model
    def format_value(self, options, value, currency=None, blank_if_zero=False, figure_type=None, digits=1):
        currency_id = int(currency or 0)
        currency = self.env['res.currency'].browse(currency_id)

        return self._format_value(options=options, value=value, currency=currency, blank_if_zero=blank_if_zero, figure_type=figure_type, digits=digits)

    def _format_value(self, options, value, currency=None, blank_if_zero=False, figure_type=None, digits=1):
        """ Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want.
        """
        if value is None:
            return ''

        if figure_type == 'none':
            return value

        if isinstance(value, str) or figure_type == 'string':
            return str(value)

        if figure_type == 'monetary':
            if options.get('multi_currency'):
                digits = None
                currency = currency or self.env.company.currency_id
            else:
                digits = (currency or self.env.company.currency_id).decimal_places
                currency = None
        elif figure_type == 'integer':
            currency = None
            digits = 0
        elif figure_type == 'boolean':
            return _("Yes") if bool(value) else _("No")
        elif figure_type in ('date', 'datetime'):
            return format_date(self.env, value)
        else:
            currency = None

        if self.is_zero(value, currency=currency, figure_type=figure_type, digits=digits):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            value = abs(value)

        if self._context.get('no_format'):
            return value

        formatted_amount = formatLang(self.env, value, digits=digits, currency_obj=currency, rounding_method='HALF-UP', rounding_unit=options.get('rounding_unit'))

        if figure_type == 'percentage':
            return f"{formatted_amount}%"

        return formatted_amount

    @api.model
    def is_zero(self, amount, currency=False, figure_type=None, digits=1):
        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            return currency.is_zero(amount)

        if figure_type == 'integer':
            digits = 0
        return float_is_zero(amount, precision_digits=digits)

    def format_date(self, options, dt_filter='date'):
        date_from = fields.Date.from_string(options[dt_filter]['date_from'])
        date_to = fields.Date.from_string(options[dt_filter]['date_to'])
        return self._get_dates_period(date_from, date_to, options['date']['mode'])['string']

    def export_file(self, options, file_generator):
        self.ensure_one()

        export_options = {**options, 'export_mode': 'file'}

        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'options': json.dumps(export_options),
                'file_generator': file_generator,
            }
        }

    def export_to_pdf(self, options):
        self.ensure_one()

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        print_options = self.get_options(previous_options={**options, 'export_mode': 'print'})
        if print_options['sections']:
            reports_to_print = self.env['account.report'].browse([section['id'] for section in print_options['sections']])
        else:
            reports_to_print = self

        reports_options = []
        for report in reports_to_print:
            reports_options.append(report.get_options(previous_options={**print_options, 'selected_section_id': report.id}))

        grouped_reports_by_format = groupby(
            zip(reports_to_print, reports_options),
            key=lambda report: len(report[1]['columns']) > 5
        )

        footer = self.env['ir.actions.report']._render_template("account_reports.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())))

        action_report = self.env['ir.actions.report']
        files_stream = []
        for is_landscape, reports_with_options in grouped_reports_by_format:
            bodies = []

            for report, report_options in reports_with_options:
                bodies.append(report._get_pdf_export_html(
                    report_options,
                    report._filter_out_folded_children(report._get_lines(report_options)),
                    additional_context={'base_url': base_url}
                ))

            files_stream.append(
                io.BytesIO(action_report._run_wkhtmltopdf(
                    bodies,
                    footer=footer.decode(),
                    landscape=is_landscape or self._context.get('force_landscape_printing'),
                    specific_paperformat_args={
                        'data-report-margin-top': 10,
                        'data-report-header-spacing': 10,
                        'data-report-margin-bottom': 15,
                    }
                )
            ))

        if len(files_stream) > 1:
            result_stream = action_report._merge_pdfs(files_stream)
            result = result_stream.getvalue()
            # Close the different stream
            result_stream.close()
            for file_stream in files_stream:
                file_stream.close()
        else:
            result = files_stream[0].read()

        return {
            'file_name': self.get_default_report_filename(options, 'pdf'),
            'file_content': result,
            'file_type': 'pdf',
        }

    def _get_pdf_export_html(self, options, lines, additional_context=None, template=None):
        report_info = self.get_report_information(options)

        custom_print_templates = report_info['custom_display'].get('pdf_export', {})
        template = custom_print_templates.get('pdf_export_main', 'account_reports.pdf_export_main')

        render_values = {
            'report': self,
            'report_title': self.name,
            'options': options,
            'table_start': markupsafe.Markup('<tbody>'),
            'table_end': markupsafe.Markup('''
                </tbody></table>
                <div style="page-break-after: always"></div>
                <table class="o_table table-hover">
            '''),
            'column_headers_render_data': self._get_column_headers_render_data(options),
            'custom_templates': custom_print_templates,
        }
        if additional_context:
            render_values.update(additional_context)

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        lines = self._format_lines_for_display(lines, options)

        render_values['lines'] = lines

        # Manage footnotes.
        footnotes_to_render = []
        number = 0
        for line in lines:
            footnote_data = report_info['footnotes'].get(str(line.get('id')))
            if footnote_data:
                number += 1
                line['footnote'] = str(number)
                footnotes_to_render.append({'id': footnote_data['id'], 'number': number, 'text': footnote_data['text']})

        render_values['footnotes'] = footnotes_to_render

        options['css_custom_class'] = report_info['custom_display'].get('css_custom_class', '')

        # Render.
        return self.env['ir.qweb']._render(template, render_values)

    def _filter_out_folded_children(self, lines):
        """ Returns a list containing all the lines of the provided list that need to be displayed when printing,
        hence removing the children whose parent is folded (especially useful to remove total lines).
        """
        rslt = []
        folded_lines = set()
        for line in lines:
            if line.get('unfoldable') and not line.get('unfolded'):
                folded_lines.add(line['id'])

            if 'parent_id' not in line or line['parent_id'] not in folded_lines:
                rslt.append(line)
        return rslt

    def export_to_xlsx(self, options, response=None):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })

        print_options = self.get_options(previous_options={**options, 'export_mode': 'print'})
        if print_options['sections']:
            reports_to_print = self.env['account.report'].browse([section['id'] for section in print_options['sections']])
        else:
            reports_to_print = self

        reports_options = []
        for report in reports_to_print:
            report_options = report.get_options(previous_options={**print_options, 'selected_section_id': report.id})
            reports_options.append(report_options)
            report._inject_report_into_xlsx_sheet(report_options, workbook, workbook.add_worksheet(report.name[:31]))

        self._add_options_xlsx_sheet(workbook, reports_options)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': self.get_default_report_filename(options, 'xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))

        # For reports with lines generated for accounts, the account name and codes are shown in a single column.
        # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            if line_model == 'account.account':
                # Reuse the _split_code_name to split the name and code in two values.
                account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])

        # Set the first column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the second column.
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 11)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

        y_offset = 0
        # 1 and not 0 to leave space for the line name. original_x_offset allows making place for the code column if needed.
        x_offset = original_x_offset + 1

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_style)
                x_offset += colspan
            if options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_style)
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        # Add lines.
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

            # write the first column, with a specific style to manage the indentation
            x_offset = original_x_offset + 1
            if lines[y]['id'] in account_lines_split_names:
                code, name = account_lines_split_names[lines[y]['id']]
                sheet.write(y + y_offset, x_offset - 2, code, col1_style)
                sheet.write(y + y_offset, x_offset - 1, name, col1_style)
            else:
                if lines[y].get('parent_id') and lines[y]['parent_id'] in account_lines_split_names:
                    sheet.write(y + y_offset, x_offset - 2, account_lines_split_names[lines[y]['parent_id']][0], col1_style)
                cell_type, cell_value = self._get_cell_type_value(lines[y])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x_offset - 1, cell_value, date_default_col1_style)
                else:
                    sheet.write(y + y_offset, x_offset - 1, cell_value, col1_style)

            #write all the remaining cells
            columns = lines[y]['columns']
            if options['show_growth_comparison'] and 'growth_comparison_data' in lines[y]:
                columns += [lines[y].get('growth_comparison_data')]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

    def _add_options_xlsx_sheet(self, workbook, options_list):
        """Adds a new sheet for xlsx report exports with a summary of all filters and options activated at the moment of the export."""
        filters_sheet = workbook.add_worksheet(_("Filters"))
        # Set first and second column widths.
        filters_sheet.set_column(0, 0, 20)
        filters_sheet.set_column(1, 1, 50)
        name_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        y_offset = 0

        if len(options_list) == 1:
            self.env['account.report'].browse(options_list[0]['report_id'])._inject_report_options_into_xlsx_sheet(options_list[0], filters_sheet, y_offset)
            return

        # Find uncommon keys
        options_sets = list(map(set, options_list))
        common_keys = set.intersection(*options_sets)
        all_keys = set.union(*options_sets)
        uncommon_options_keys = all_keys - common_keys
        # Try to find the common filter values between all reports to avoid duplication.
        common_options_values = {}
        for key in common_keys:
            first_value = options_list[0][key]
            if all(options[key] == first_value for options in options_list[1:]):
                common_options_values[key] = first_value
            else:
                uncommon_options_keys.add(key)

        # Write common options to the sheet.
        filters_sheet.write(y_offset, 0, _("All"), name_style)
        y_offset += 1
        y_offset = self._inject_report_options_into_xlsx_sheet(common_options_values, filters_sheet, y_offset)

        for report_options in options_list:
            report = self.env['account.report'].browse(report_options['report_id'])

            filters_sheet.write(y_offset, 0, _("%s", report.name), name_style)
            y_offset += 1
            new_offset = report._inject_report_options_into_xlsx_sheet(report_options, filters_sheet, y_offset, uncommon_options_keys)

            if y_offset == new_offset:
                y_offset -= 1
                # Clear the report name's cell since it didn't add any data to the xlsx.
                filters_sheet.write(y_offset, 0, " ")
            else:
                y_offset = new_offset

    def _inject_report_options_into_xlsx_sheet(self, options, sheet, y_offset, options_to_print=None):
        """
        Injects the report options into the filters sheet.

        :param options: Dictionary containing report options.
        :param sheet: XLSX sheet to inject options into.
        :param y_offset: Offset for the vertical position in the sheet.
        :param options_to_print: Optional list of names to print. If not provided, all printable options will be included.
        """
        def write_filter_lines(filter_title, filter_lines, y_offset):
            sheet.write(y_offset, 0, filter_title)
            for line in filter_lines:
                sheet.write(y_offset, 1, line)
                y_offset += 1
            return y_offset

        def should_print_option(option_key):
            """Check if the option should be printed based on options_to_print."""
            return not options_to_print or option_key in options_to_print

        # Company
        if should_print_option('companies'):
            companies = options['companies']
            title = _("Companies") if len(companies) > 1 else _("Company")
            lines = [company['name'] for company in companies]
            y_offset = write_filter_lines(title, lines, y_offset)

        # Journals
        if should_print_option('journals') and (journals := options.get('journals')):
            journal_titles = [journal.get('title') for journal in journals if journal.get('selected')]
            if journal_titles:
                y_offset = write_filter_lines(_("Journals"), journal_titles, y_offset)

        # Partners
        if should_print_option('selected_partner_ids') and (partner_names := options.get('selected_partner_ids')):
            y_offset = write_filter_lines(_("Partners"), partner_names, y_offset)

        # Partner categories
        if should_print_option('selected_partner_categories') and (partner_categories := options.get('selected_partner_categories')):
            y_offset = write_filter_lines(_("Partner Categories"), partner_categories, y_offset)

        # Horizontal groups
        if should_print_option('selected_horizontal_group_id') and (group_id := options.get('selected_horizontal_group_id')):
            for horizontal_group in options['available_horizontal_groups']:
                if horizontal_group['id'] == group_id:
                    filter_name = horizontal_group['name']
                    y_offset = write_filter_lines(_("Horizontal Group"), [filter_name], y_offset)
                    break

        # Currency
        if should_print_option('company_currency') and options.get('company_currency'):
            y_offset = write_filter_lines(_("Company Currency"), [options['company_currency']['currency_name']], y_offset)

        # Filters
        if should_print_option('aml_ir_filters'):
            if options.get('aml_ir_filters') and any(opt['selected'] for opt in options['aml_ir_filters']):
                filter_names = [opt['name'] for opt in options['aml_ir_filters'] if opt['selected']]
                y_offset = write_filter_lines(_("Filters"), filter_names, y_offset)

        # Extra options
        # Array of tuples for the extra options: (name, option_key, condition)
        extra_options = [
            (_("With Draft Entries"), 'all_entries', self.filter_show_draft),
            (_("Only Show Unreconciled Entries"), 'unreconciled', self.filter_unreconciled),
            (_("Including Analytic Simulations"), 'include_analytic_without_aml', True)
        ]
        filter_names = [
            name for name, option_key, condition in extra_options
            if (not options_to_print or option_key in options_to_print) and condition and options.get(option_key)
        ]
        if filter_names:
            y_offset = write_filter_lines(_("Options"), filter_names, y_offset)

        return y_offset

    def _get_cell_type_value(self, cell):
        if 'date' not in cell.get('class', '') or not cell.get('name'):
            # cell is not a date
            return ('text', cell.get('name', ''))
        if isinstance(cell['name'], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ('date', cell['name'])
        try:
            # the date is parsable to a xlsx compatible date
            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            return ('date', datetime.datetime.strptime(cell['name'], lg.date_format))
        except:
            # the date is not parsable thus is returned as text
            return ('text', cell['name'])

    def get_vat_for_export(self, options, raise_warning=True):
        """ Returns the VAT number to use when exporting this report with the provided
        options. If a single fiscal_position option is set, its VAT number will be
        used; else the current company's will be, raising an error if its empty.
        """
        self.ensure_one()

        if self.filter_multi_company == 'tax_units' and options['tax_unit'] != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.vat

        if options['fiscal_position'] in {'all', 'domestic'}:
            company = self._get_sender_company_for_export(options)
            if not company.vat and raise_warning:
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('No VAT number associated with your company. Please define one.'), action.id, _("Company Settings"))
            return company.vat

        fiscal_position = self.env['account.fiscal.position'].browse(options['fiscal_position'])
        return fiscal_position.foreign_vat

    @api.model
    def get_report_company_ids(self, options):
        """ Returns a list containing the ids of the companies to be used to
        render this report, following the provided options.
        """
        return [comp_data['id'] for comp_data in options['companies']]

    @api.model
    def _get_query_currency_table(self, options):
        company_ids = self.get_report_company_ids(options)
        conversion_date = options['date']['date_to']
        return self.env['res.currency']._get_query_currency_table(company_ids, conversion_date)

    def _get_partner_and_general_ledger_initial_balance_line(self, options, parent_line_id, eval_dict, account_currency=None, level_shift=0):
        """ Helper to generate dynamic 'initial balance' lines, used by general ledger and partner ledger.
        """
        line_columns = []
        for column in options['columns']:
            col_value = eval_dict[column['column_group_key']].get(column['expression_label'])
            col_expr_label = column['expression_label']

            if col_value is None or (col_expr_label == 'amount_currency' and not account_currency):
                line_columns.append(self._build_column_dict(None, None))
            else:
                line_columns.append(self._build_column_dict(
                    col_value,
                    column,
                    options=options,
                    currency=account_currency if col_expr_label == 'amount_currency' else None,
                ))

        if not any(column.get('no_format') for column in line_columns):
            return None

        return {
            'id': self._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='initial'),
            'name': _("Initial Balance"),
            'level': 3 + level_shift,
            'parent_id': parent_line_id,
            'columns': line_columns,
        }

    def _compute_growth_comparison_column(self, options, value1, value2, green_on_positive=True):
        ''' Helper to get the additional columns due to the growth comparison feature. When only one comparison is
        requested, an additional column is there to show the percentage of growth based on the compared period.
        :param options:             The report options.
        :param value1:              The value in the current period.
        :param value2:              The value in the compared period.
        :param green_on_positive:   A flag customizing the value with a green color depending if the growth is positive.
        :return:                    The new columns to add to line['columns'].
        '''
        if float_is_zero(value2, precision_rounding=0.1):
            return {'name': _('n/a'), 'growth': 0}
        else:
            values_diff = value1 - value2
            growth = round(values_diff / value2 * 100, 1)

            # In case the comparison is made on a negative figure, the color should be the other
            # way around. For example:
            #                       2018         2017           %
            # Product Sales      1000.00     -1000.00     -200.0%
            #
            # The percentage is negative, which is mathematically correct, but my sales increased
            # => it should be green, not red!
            if float_is_zero(growth, precision_rounding=0.1):
                return {'name': '0.0%', 'growth': 0}
            else:
                return {
                    'name': str(growth) + '%',
                    'growth': -1 if ((values_diff > 0) ^ green_on_positive) else 1,
                }

    def _display_growth_comparison(self, options):
        ''' Helper determining if the growth comparison feature should be displayed or not.
        :param options: The report options.
        :return:        A boolean.
        '''
        return self.filter_growth_comparison \
               and options.get('comparison') \
               and len(options['comparison'].get('periods', [])) == 1 \
               and options['selected_horizontal_group_id'] is None \
               and len(options['columns']) == 2

    @api.model
    def _check_groupby_fields(self, groupby_fields_name: list[str] | str):
        """ Checks that each string in the groupby_fields_name list is a valid groupby value for an accounting report (so: it must be a field from
        account.move.line).
        """
        if isinstance(groupby_fields_name, str | bool):
            groupby_fields_name = groupby_fields_name.split(',') if groupby_fields_name else []
        for field_name in (fname.strip() for fname in groupby_fields_name):
            groupby_field = self.env['account.move.line']._fields.get(field_name)
            if not groupby_field:
                raise UserError(_("Field %s does not exist on account.move.line.", field_name))
            if not groupby_field.store:
                raise UserError(_("Field %s of account.move.line is not stored, and hence cannot be used in a groupby expression", field_name))

    # ============ Accounts Coverage Debugging Tool - START ================
    @api.depends('country_id', 'chart_template', 'root_report_id')
    def _compute_is_account_coverage_report_available(self):
        for report in self:
            report.is_account_coverage_report_available = (
                (
                    self.availability_condition == 'country' and self.env.company.account_fiscal_country_id == self.country_id
                    or
                    self.availability_condition == 'coa' and self.env.company.chart_template == self.chart_template
                    or
                    self.availability_condition == 'always'
                )
                and
                self.root_report_id in (self.env.ref('account_reports.profit_and_loss'), self.env.ref('account_reports.balance_sheet'))
            )

    def action_download_xlsx_accounts_coverage_report(self):
        """
        Generate an XLSX file that can be used to debug the
        report by issuing the following warnings if applicable:
        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """
        self.ensure_one()
        if not self.is_account_coverage_report_available:
            raise UserError(_("The Accounts Coverage Report is not available for this report."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(_('Accounts coverage'))
        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 1, 75)
        worksheet.set_column(2, 2, 80)
        worksheet.freeze_panes(1, 0)

        headers = [_("Account Code / Tag"), _("Error message"), _("Report lines mentioning the account code"), '#FFFFFF']
        lines = [headers] + self._generate_accounts_coverage_report_xlsx_lines()
        for i, line in enumerate(lines):
            worksheet.write_row(i, 0, line[:-1], workbook.add_format({'bg_color': line[-1]}))

        workbook.close()
        attachment_id = self.env['ir.attachment'].create({
            'name': f"{self.display_name} - {_('Accounts Coverage Report')}",
            'datas': base64.encodebytes(output.getvalue())
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "download",
        }

    def _generate_accounts_coverage_report_xlsx_lines(self):
        """
        Generate the lines of the XLSX file that can be used to debug the
        report by issuing the following warnings if applicable:
        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """
        def get_account_domain(prefix):
            # Helper function to get the right domain to find the account
            # This function verifies if we have to look for a tag or if we have
            # to look for an account code.
            if tag_matching := ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix):
                if tag_matching['ref']:
                    account_tag_id = self.env['ir.model.data']._xmlid_to_res_id(tag_matching['ref'])
                else:
                    account_tag_id = int(tag_matching['id'])
                return 'tag_ids', 'in', (account_tag_id,)
            else:
                return 'code', '=like', f'{prefix}%'

        self.ensure_one()

        all_reported_accounts = self.env["account.account"]  # All accounts mentioned in the report (including those reported without using the account code)
        accounts_by_expressions = {}    # {expression_id: account.account objects}
        reported_account_codes = []     # [{'prefix': ..., 'balance': ..., 'exclude': ..., 'line': ...}, ...]
        non_existing_codes = defaultdict(lambda: self.env["account.report.line"])  # {non_existing_account_code: {lines_with_that_code,}}
        lines_per_non_linked_tag = defaultdict(lambda: self.env['account.report.line'])
        lines_using_bad_operator_per_tag = defaultdict(lambda: self.env['account.report.line'])
        candidate_duplicate_codes = defaultdict(lambda: self.env["account.report.line"])  # {candidate_duplicate_account_code: {lines_with_that_code,}}
        duplicate_codes = defaultdict(lambda: self.env["account.report.line"])  # {verified duplicate_account_code: {lines_with_that_code,}}
        duplicate_codes_same_line = defaultdict(lambda: self.env["account.report.line"])  # {duplicate_account_code: {line_with_that_code_multiple_times,}}
        common_account_domain = [
            *self.env['account.account']._check_company_domain(self.env.company),
            ('deprecated', '=', False),
        ]

        # tag_ids already linked to an account - avoid several search_count to know if the tag is used or not
        tag_ids_linked_to_account = set(self.env['account.account'].search([('tag_ids', '!=', False)]).tag_ids.ids)

        expressions = self.line_ids.expression_ids._expand_aggregations()
        for i, expr in enumerate(expressions):
            reported_accounts = self.env["account.account"]
            if expr.engine == "domain":
                domain = literal_eval(expr.formula.strip())
                accounts_domain = []
                for j, operand in enumerate(domain):
                    if isinstance(operand, tuple):
                        operand = list(operand)
                        # Skip tuples that will not be used in the new domain to retrieve the reported accounts
                        if not operand[0].startswith('account_id.'):
                            if domain[j - 1] in ("&", "|", "!"):  # Remove the operator linked to the tuple if it exists
                                accounts_domain.pop()
                            continue
                        operand[0] = operand[0].replace('account_id.', '')
                        # Check that the code exists in the CoA
                        if operand[0] == 'code' and not self.env["account.account"].search_count([operand]):
                            non_existing_codes[operand[2]] |= expr.report_line_id
                        elif operand[0] == 'tag_ids':
                            tag_ids = operand[2]
                            if not isinstance(tag_ids, (list, tuple, set)):
                                tag_ids = [tag_ids]

                            if operand[1] in ('=', 'in'):
                                tag_ids_to_browse = [tag_id for tag_id in tag_ids if tag_id not in tag_ids_linked_to_account]
                                for tag in self.env['account.account.tag'].browse(tag_ids_to_browse):
                                    lines_per_non_linked_tag[f'{tag.name} ({tag.id})'] |= expr.report_line_id
                            else:
                                for tag in self.env['account.account.tag'].browse(tag_ids):
                                    lines_using_bad_operator_per_tag[f'{tag.name} ({tag.id}) - Operator: {operand[1]}'] |= expr.report_line_id

                    accounts_domain.append(operand)
                reported_accounts += self.env['account.account'].search(accounts_domain)
            elif expr.engine == "account_codes":
                account_codes = []
                for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(expr.formula.replace(' ', '')):
                    if not token:
                        continue
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                    if not token_match:
                        continue

                    parsed_token = token_match.groupdict()
                    account_codes.append({
                        'prefix': parsed_token['prefix'],
                        'balance': parsed_token['balance_character'],
                        'exclude': parsed_token['excluded_prefixes'].split(',') if parsed_token['excluded_prefixes'] else [],
                        'line': expr.report_line_id,
                    })

                for account_code in account_codes:
                    reported_account_codes.append(account_code)
                    exclude_domain_accounts = [get_account_domain(exclude_code) for exclude_code in account_code['exclude']]
                    reported_accounts += self.env["account.account"].search([
                        *common_account_domain,
                        get_account_domain(account_code['prefix']),
                        *[excl_domain for excl_tuple in exclude_domain_accounts for excl_domain in ("!", excl_tuple)],
                    ])

                    # Check that the code exists in the CoA or that the tag is linked to an account
                    prefixes_to_check = [account_code['prefix']] + account_code['exclude']
                    for prefix_to_check in prefixes_to_check:
                        account_domain = get_account_domain(prefix_to_check)
                        if not self.env["account.account"].search_count([
                            *common_account_domain,
                            account_domain,
                        ]):
                            # Identify if we're working with account codes or account tags
                            if account_domain[0] == 'code':
                                non_existing_codes[prefix_to_check] |= account_code['line']
                            elif account_domain[0] == 'tag_ids':
                                lines_per_non_linked_tag[prefix_to_check] |= account_code['line']

            all_reported_accounts |= reported_accounts
            accounts_by_expressions[expr.id] = reported_accounts

            # Check if an account is reported multiple times in the same line of the report
            if len(reported_accounts) != len(set(reported_accounts)):
                seen = set()
                for reported_account in reported_accounts:
                    if reported_account not in seen:
                        seen.add(reported_account)
                    else:
                        duplicate_codes_same_line[reported_account.code] |= expr.report_line_id

            # Check if the account is reported in multiple lines of the report
            for expr2 in expressions[:i + 1]:
                reported_accounts2 = accounts_by_expressions[expr2.id]
                for duplicate_account in (reported_accounts & reported_accounts2):
                    if len(expr.report_line_id | expr2.report_line_id) > 1 \
                       and expr.date_scope == expr2.date_scope \
                       and expr.subformula == expr2.subformula:
                        candidate_duplicate_codes[duplicate_account.code] |= expr.report_line_id | expr2.report_line_id

        # Check that the duplicates are not false positives because of the balance character
        for candidate_duplicate_code, candidate_duplicate_lines in candidate_duplicate_codes.items():
            seen_balance_chars = []
            for reported_account_code in reported_account_codes:
                if candidate_duplicate_code.startswith(reported_account_code['prefix']) and reported_account_code['balance']:
                    seen_balance_chars.append(reported_account_code['balance'])
            if not seen_balance_chars or seen_balance_chars.count("C") > 1 or seen_balance_chars.count("D") > 1:
                duplicate_codes[candidate_duplicate_code] |= candidate_duplicate_lines

        # Check that all codes in CoA are correctly reported
        if self.root_report_id == self.env.ref('account_reports.profit_and_loss'):
            accounts_in_coa = self.env["account.account"].search([
                *common_account_domain,
                ('account_type', 'in', ("income", "income_other", "expense", "expense_depreciation", "expense_direct_cost")),
                ('account_type', '!=', "off_balance"),
            ])
        else:  # Balance Sheet
            accounts_in_coa = self.env["account.account"].search([
                *common_account_domain,
                ('account_type', 'not in', ("off_balance", "income", "income_other", "expense", "expense_depreciation", "expense_direct_cost"))
            ])

        # Compute codes that exist in the CoA but are not reported in the report
        non_reported_codes = set((accounts_in_coa - all_reported_accounts).mapped('code'))

        # Create the lines that will be displayed in the xlsx
        all_reported_codes = sorted(set(all_reported_accounts.mapped("code")) | non_reported_codes | non_existing_codes.keys())
        errors_trie = self._get_accounts_coverage_report_errors_trie(all_reported_codes, non_reported_codes, duplicate_codes, duplicate_codes_same_line, non_existing_codes)
        errors_trie['children'].update(**self._get_account_tag_coverage_report_errors_trie(lines_per_non_linked_tag, lines_using_bad_operator_per_tag))  # Add tags that are not linked to an account

        errors_trie = self._regroup_accounts_coverage_report_errors_trie(errors_trie)
        return self._get_accounts_coverage_report_coverage_lines("", errors_trie)

    def _get_accounts_coverage_report_errors_trie(self, all_reported_codes, non_reported_codes, duplicate_codes, duplicate_codes_same_line, non_existing_codes):
        """
        Create the trie that will be used to regroup the same errors on the same subcodes.
        This trie will be in the form of:
        {
            "children": {
                "1": {
                    "children": {
                        "10": { ... },
                        "11": { ... },
                    },
                    "lines": {
                        "Line1",
                        "Line2",
                    },
                    "errors": {
                        "DUPLICATE"
                    }
                },
            "lines": {
                "",
            },
            "errors": {
                None    # Avoid that all codes are merged into the root with the code "" in case all of the errors are the same
            },
        }
        """
        errors_trie = {"children": {}, "lines": {}, "errors": {None}}
        for reported_code in all_reported_codes:
            current_trie = errors_trie
            lines = self.env["account.report.line"]
            errors = set()
            if reported_code in non_reported_codes:
                errors.add("NON_REPORTED")
            elif reported_code in duplicate_codes_same_line:
                lines |= duplicate_codes_same_line[reported_code]
                errors.add("DUPLICATE_SAME_LINE")
            elif reported_code in duplicate_codes:
                lines |= duplicate_codes[reported_code]
                errors.add("DUPLICATE")
            elif reported_code in non_existing_codes:
                lines |= non_existing_codes[reported_code]
                errors.add("NON_EXISTING")
            else:
                errors.add("NONE")

            for j in range(1, len(reported_code) + 1):
                current_trie = current_trie["children"].setdefault(reported_code[:j], {
                    "children": {},
                    "lines": lines,
                    "errors": errors
                })
        return errors_trie

    @api.model
    def _get_account_tag_coverage_report_errors_trie(self, lines_per_non_linked_tag, lines_per_bad_operator_tag):
        """ As we don't want to make a hierarchy for tags, we use a specific
            function to handle tags.
        """
        errors = {
            non_linked_tag: {
                'children': {},
                'lines': line,
                'errors': {'NON_LINKED'},
            }
            for non_linked_tag, line in lines_per_non_linked_tag.items()
        }
        errors.update({
            bad_operator_tag: {
                'children': {},
                'lines': line,
                'errors': {'BAD_OPERATOR'},
            }
            for bad_operator_tag, line in lines_per_bad_operator_tag.items()
        })
        return errors

    def _regroup_accounts_coverage_report_errors_trie(self, trie):
        """
        Regroup the codes that have the same error under the same common subcode/prefix.
        This is done in-place on the given trie.
        """
        if trie.get("children"):
            children_errors = set()
            children_lines = self.env["account.report.line"]
            if trie.get("errors"):  # Add own error
                children_errors |= set(trie.get("errors"))
            for child in trie["children"].values():
                regroup = self._regroup_accounts_coverage_report_errors_trie(child)
                children_lines |= regroup["lines"]
                children_errors |= set(regroup["errors"])
            if len(children_errors) == 1 and children_lines and children_lines == trie["lines"]:
                trie["children"] = {}
                trie["lines"] = children_lines
                trie["errors"] = children_errors
        return trie

    def _get_accounts_coverage_report_coverage_lines(self, subcode, trie, coverage_lines=None):
        """
        Create the coverage lines from the grouped trie. Each line has
        - the account code
        - the error message
        - the lines on which the account code is used
        - the color of the error message for the xlsx
        """
        # Dictionnary of the three possible errors, their message and the corresponding color for the xlsx file
        ERRORS = {
            "NON_REPORTED": {
                "msg": _("This account exists in the Chart of Accounts but is not mentioned in any line of the report"),
                "color": "#FF0000"
            },
            "DUPLICATE": {
                "msg": _("This account is reported in multiple lines of the report"),
                "color": "#FF8916"
            },
            "DUPLICATE_SAME_LINE": {
                "msg": _("This account is reported multiple times on the same line of the report"),
                "color": "#E6A91D"
            },
            "NON_EXISTING": {
                "msg": _("This account is reported in a line of the report but does not exist in the Chart of Accounts"),
                "color": "#FFBF00"
            },
            "NON_LINKED": {
                "msg": _("This tag is reported in a line of the report but is not linked to any account of the Chart of Accounts"),
                "color": "#FFBF00",
            },
            "BAD_OPERATOR": {
                "msg": _("The used operator is not supported for this expression."),
                "color": "#FFBF00",
            }
        }
        if coverage_lines is None:
            coverage_lines = []
        if trie.get("children"):
            for child in trie.get("children"):
                self._get_accounts_coverage_report_coverage_lines(child, trie["children"][child], coverage_lines)
        else:
            error = list(trie["errors"])[0] if trie["errors"] else False
            if error and error != "NONE":
                coverage_lines.append([
                    subcode,
                    ERRORS[error]["msg"],
                    " + ".join(trie["lines"].sorted().mapped("name")),
                    ERRORS[error]["color"]
                ])
        return coverage_lines

    # ============ Accounts Coverage Debugging Tool - END ================


class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    display_custom_groupby_warning = fields.Boolean(compute='_compute_display_custom_groupby_warning')

    @api.depends('groupby', 'user_groupby')
    def _compute_display_custom_groupby_warning(self):
        for line in self:
            line.display_custom_groupby_warning = line.get_external_id() and line.user_groupby != line.groupby

    @api.constrains('groupby', 'user_groupby')
    def _validate_groupby(self):
        super()._validate_groupby()
        for report_line in self:
            self.env['account.report']._check_groupby_fields(report_line.user_groupby)
            self.env['account.report']._check_groupby_fields(report_line.groupby)

    def _expand_groupby(self, line_dict_id, groupby, options, offset=0, limit=None, load_one_more=False, unfold_all_batch_data=None):
        """ Expand function used to get the sublines of a groupby.
        groupby param is a string consisting of one or more coma-separated field names. Only the first one
        will be used for the expansion; if there are subsequent ones, the generated lines will themselves used them as
        their groupby value, and point to this expand_function, hence generating a hierarchy of groupby).
        """
        self.ensure_one()

        group_indent = 0
        line_id_list = self.report_id._parse_line_id(line_dict_id)

        # If this line is a sub-groupby of groupby line (for example, when grouping by partner, id; the id line is a subgroup of partner),
        # we need to add the domain of the parent groupby criteria to the options
        prefix_groups_count = 0
        sub_groupby_domain = []
        full_sub_groupby_key_elements = []
        for markup, model, value in line_id_list:
            if markup.startswith('groupby:'):
                field_name = markup.split(':')[1]
                sub_groupby_domain.append((field_name, '=', value))
                full_sub_groupby_key_elements.append(f"{field_name}:{value}")
            elif markup.startswith('groupby_prefix_group:'):
                prefix_groups_count += 1

            if model == 'account.group':
                group_indent += 1

        if sub_groupby_domain:
            forced_domain = options.get('forced_domain', []) + sub_groupby_domain
            options = {**options, 'forced_domain': forced_domain}

        # Parse groupby
        groupby_data = self._parse_groupby(options, groupby_to_expand=groupby)
        groupby_model = groupby_data['current_groupby_model']
        next_groupby = groupby_data['next_groupby']
        current_groupby = groupby_data['current_groupby']

        # If the report transmitted custom_unfold_all_batch_data dictionary, use it
        full_sub_groupby_key = f"[{self.id}]{','.join(full_sub_groupby_key_elements)}=>{current_groupby}"

        cached_result = (unfold_all_batch_data or {}).get(full_sub_groupby_key)

        if cached_result is not None:
            all_column_groups_expression_totals = cached_result
        else:
            all_column_groups_expression_totals = self.report_id._compute_expression_totals_for_each_column_group(
                self.expression_ids,
                options,
                groupby_to_expand=groupby,
                offset=offset,
                limit=limit + 1 if limit and load_one_more else limit,
            )

        # Put similar grouping keys from different totals/periods together, so that we don't display multiple
        # lines for the same grouping key

        figure_types_defaulting_to_0 = {'monetary', 'percentage', 'integer', 'float'}

        default_value_per_expr_label = {
            col_opt['expression_label']: 0 if col_opt['figure_type'] in figure_types_defaulting_to_0 else None
            for col_opt in options['columns']
        }

        # Gather default value for each expression, in case it has no value for a given grouping key
        default_value_per_expression = {}
        for expression in self.expression_ids:
            if expression.figure_type:
                default_value = 0 if expression.figure_type in figure_types_defaulting_to_0 else None
            else:
                default_value = default_value_per_expr_label.get(expression.label)

            default_value_per_expression[expression] = {'value': default_value}

        # Build each group's result
        aggregated_group_totals = defaultdict(lambda: defaultdict(default_value_per_expression.copy))
        for column_group_key, expression_totals in all_column_groups_expression_totals.items():
            for expression in self.expression_ids:
                for grouping_key, result in expression_totals[expression]['value']:
                    aggregated_group_totals[grouping_key][column_group_key][expression] = {'value': result}

        # Generate groupby lines
        group_lines_by_keys = {}
        for grouping_key, group_totals in aggregated_group_totals.items():
            # For this, we emulate a dict formatted like the result of _compute_expression_totals_for_each_column_group, so that we can call
            # _build_static_line_columns like on non-grouped lines
            line_id = self.report_id._get_generic_line_id(groupby_model, grouping_key, parent_line_id=line_dict_id, markup=f'groupby:{current_groupby}')
            group_line_dict = {
                # 'name' key will be set later, so that we can browse all the records of this expansion at once (in case we're dealing with records)
                'id': line_id,
                'unfoldable': bool(next_groupby),
                'unfolded': (next_groupby and options['unfold_all']) or line_id in options['unfolded_lines'],
                'groupby': next_groupby,
                'columns': self.report_id._build_static_line_columns(self, options, group_totals),
                'level': self.hierarchy_level + 2 * (prefix_groups_count + len(sub_groupby_domain) + 1) + (group_indent - 1),
                'parent_id': line_dict_id,
                'expand_function': '_report_expand_unfoldable_line_with_groupby' if next_groupby else None,
                'caret_options': groupby_model if not next_groupby else None,
            }

            if self.report_id.custom_handler_model_id:
                self.env[self.report_id.custom_handler_model_name]._custom_groupby_line_completer(self.report_id, options, group_line_dict)

            # Growth comparison column.
            if self.report_id._display_growth_comparison(options):
                compared_expression = self.expression_ids.filtered(lambda expr: expr.label == group_line_dict['columns'][0]['expression_label'])
                group_line_dict['growth_comparison_data'] = self.report_id._compute_growth_comparison_column(
                    options, group_line_dict['columns'][0]['no_format'], group_line_dict['columns'][1]['no_format'], green_on_positive=compared_expression.green_on_positive)

            group_lines_by_keys[grouping_key] = group_line_dict

        # Sort grouping keys in the right order and generate line names
        keys_and_names_in_sequence = {}  # Order of this dict will matter

        if groupby_model:
            browsed_groupby_keys = self.env[groupby_model].browse(list(key for key in group_lines_by_keys if key is not None))

            out_of_sorting_record = None
            records_to_sort = browsed_groupby_keys
            if browsed_groupby_keys and load_one_more and len(browsed_groupby_keys) >= limit:
                out_of_sorting_record = browsed_groupby_keys[-1]
                records_to_sort = records_to_sort[:-1]

            for record in records_to_sort.with_context(active_test=False).sorted():
                keys_and_names_in_sequence[record.id] = record.display_name

            if None in group_lines_by_keys:
                keys_and_names_in_sequence[None] = _("Unknown")

            if out_of_sorting_record:
                keys_and_names_in_sequence[out_of_sorting_record.id] = out_of_sorting_record.display_name

        else:
            for non_relational_key in sorted(group_lines_by_keys.keys()):
                keys_and_names_in_sequence[non_relational_key] = str(non_relational_key) if non_relational_key is not None else _("Unknown")

        # Build result: add a name to the groupby lines and handle totals below section for multi-level groupby
        group_lines = []
        for grouping_key, line_name in keys_and_names_in_sequence.items():
            group_line_dict = group_lines_by_keys[grouping_key]
            group_line_dict['name'] = line_name
            group_lines.append(group_line_dict)

        if options.get('hierarchy'):
            group_lines = self.report_id._create_hierarchy(group_lines, options)

        return group_lines

    def _get_groupby_line_name(self, groupby_field_name, groupby_model, grouping_key):
        if groupby_model is None:
            return grouping_key

        if grouping_key is None:
            return _("Unknown")

        return self.env[groupby_model].browse(grouping_key).display_name

    def _parse_groupby(self, options, groupby_to_expand=None):
        """ Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 3 keys:
            'current_groupby':       The name of the field to be used on account.move.line to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated field name.
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

        EXAMPLE:
            When computing a line with groupby=partner_id,account_id,id , without expanding it:
            - groupby_to_expand will be None
            - current_groupby will be None
            - next_groupby will be 'partner_id,account_id,id'
            - current_groupby_model will be None

            When expanding the first group level of the line:
            - groupby_to_expand will be: partner_id,account_id,id
            - current_groupby will be 'partner_id'
            - next_groupby will be 'account_id,id'
            - current_groupby_model will be 'res.partner'

            When expanding further:
            - groupby_to_expand will be: account_id,id ; corresponding to the next_groupby computed when expanding partner_id
            - current_groupby will be 'account_id'
            - next_groupby will be 'id'
            - current_groupby_model will be 'account.account'
        """
        self.ensure_one()

        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(' ', '')
            split_groupby = groupby_to_expand.split(',')
            current_groupby = split_groupby[0]
            next_groupby = ','.join(split_groupby[1:]) if len(split_groupby) > 1 else None
        else:
            current_groupby = None
            groupby = self._get_groupby(options)
            next_groupby = groupby.replace(' ', '') if groupby else None
            split_groupby = next_groupby.split(',') if next_groupby else []

        if current_groupby == 'id':
            groupby_model = 'account.move.line'
        elif current_groupby:
            groupby_model = self.env['account.move.line']._fields[current_groupby].comodel_name
        else:
            groupby_model = None

        return {
            'current_groupby': current_groupby,
            'next_groupby': next_groupby,
            'current_groupby_model': groupby_model,
        }

    def _get_groupby(self, options):
        self.ensure_one()
        if options['export_mode'] == 'file':
            return self.groupby
        return self.user_groupby

    def action_reset_custom_groupby(self):
        self.ensure_one()
        self.user_groupby = self.groupby


class AccountReportExpression(models.Model):
    _inherit = 'account.report.expression'

    def action_view_carryover_lines(self, options, column_group_key=None):
        if column_group_key:
            options = self.report_line_id.report_id._get_column_group_options(options, column_group_key)

        date_from, date_to, _dummy = self.report_line_id.report_id._get_date_bounds_info(options, self.date_scope)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Carryover lines for: %s', self.report_line_name),
            'res_model': 'account.report.external.value',
            'views': [(False, 'list')],
            'domain': [
                ('target_report_expression_id', '=', self.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ],
        }


class AccountReportHorizontalGroup(models.Model):
    _name = "account.report.horizontal.group"
    _description = "Horizontal group for reports"

    name = fields.Char(string="Name", required=True, translate=True)
    rule_ids = fields.One2many(string="Rules", comodel_name='account.report.horizontal.group.rule', inverse_name='horizontal_group_id', required=True)
    report_ids = fields.Many2many(string="Reports", comodel_name='account.report')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "A horizontal group with the same name already exists."),
    ]

    def _get_header_levels_data(self):
        return [
            (rule.field_name, rule._get_matching_records())
            for rule in self.rule_ids
        ]

class AccountReportHorizontalGroupRule(models.Model):
    _name = "account.report.horizontal.group.rule"
    _description = "Horizontal group rule for reports"

    def _field_name_selection_values(self):
        return [
            (aml_field['name'], aml_field['string'])
            for aml_field in self.env['account.move.line'].fields_get().values()
            if aml_field['type'] in ('many2one', 'many2many')
        ]

    horizontal_group_id = fields.Many2one(string="Horizontal Group", comodel_name='account.report.horizontal.group', required=True)
    domain = fields.Char(string="Domain", required=True, default='[]')
    field_name = fields.Selection(string="Field", selection='_field_name_selection_values', required=True)
    res_model_name = fields.Char(string="Model", compute='_compute_res_model_name')

    @api.depends('field_name')
    def _compute_res_model_name(self):
        for record in self:
            if record.field_name:
                record.res_model_name = self.env['account.move.line']._fields[record.field_name].comodel_name
            else:
                record.res_model_name = None

    def _get_matching_records(self):
        self.ensure_one()
        model_name = self.env['account.move.line']._fields[self.field_name].comodel_name
        domain = ast.literal_eval(self.domain)
        return self.env[model_name].search(domain)


class AccountReportCustomHandler(models.AbstractModel):
    _name = 'account.report.custom.handler'
    _description = 'Account Report Custom Handler'

    # This abstract model allows case-by-case localized changes of behaviors of reports.
    # This is used for custom reports, for cases that cannot be supported by the standard engines.

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """ Generates lines dynamically for reports that require a custom processing which cannot be handled
        by regular report engines.
        :return:    A list of tuples [(sequence, line_dict), ...], where:
                    - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                    - line_dict is a dict containing all the line values.
        """
        return []

    def _caret_options_initializer(self):
        """ Returns the caret options dict to be used when rendering this report,
        in the same format as the one used in _caret_options_initializer_default (defined on 'account.report').
        If the result is empty, the engine will use the default caret options.
        """
        return self.env['account.report']._caret_options_initializer_default()

    def _custom_options_initializer(self, report, options, previous_options=None):
        """ To be overridden to add report-specific _init_options... code to the report. """
        if report.root_report_id:
            report.root_report_id._init_options_custom(options, previous_options)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        """ Postprocesses the result of the report's _get_lines() before returning it. """
        return lines

    def _custom_groupby_line_completer(self, report, options, line_dict):
        """ Postprocesses the dict generated by the group_by_line, to customize its content. """

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        """ When using the 'unfold all' option, some reports might end up recomputing the same query for
        each line to unfold, leading to very inefficient computation. This function allows batching this computation,
        and returns a dictionary where all results are cached, for use in expansion functions.
        """
        return None

    def _get_custom_display_config(self):
        """ To be overridden in order to change the templates used by Javascript to render this report (keeping the same
        OWL components), and/or replace some of the default OWL components by custom-made ones.

        This function returns a dict (possibly empty, if there is no custom display config):

        {
            'css_custom_class: 'class',
            'components': {

            },
            'pdf_export': {

            },
            'templates': {

            },
        },
        """
        return {}

    def _enable_export_buttons_for_common_vat_groups_in_branches(self, options):
        """ Helper function to be called in _custom_options_initializer to change the behavior of the report so that the export
        buttons are all forced to 'branch_allowed' in case the currently selected company branches all share the same VAT number, and
        no unselected sub-branch of the active company has the same VAT number. Companies without explicit VAT number (empty vat field)
        will be considered as having the same VAT number as their closest parent with a non-empty VAT.
        """
        report_accepted_company_ids = set(self.env['account.report'].get_report_company_ids(options))
        same_vat_branch_ids = set(self.env.company._get_branches_with_same_vat().ids)
        if report_accepted_company_ids == same_vat_branch_ids:
            for button in options['buttons']:
                button['branch_allowed'] = True


class AccountReportFileDownloadException(Exception):
    def __init__(self, errors, content=None):
        super().__init__()
        self.errors = errors
        self.content = content
