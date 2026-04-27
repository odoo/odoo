# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import io
import json
import logging
import re
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key
from itertools import chain, groupby

import markupsafe
from dateutil.relativedelta import relativedelta
from PIL import ImageFont

from odoo import models, fields, api, _, osv
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.service.model import get_public_method
from odoo.tools import date_utils, get_lang, float_is_zero, float_repr, SQL, parse_version, Query
from odoo.tools.float_utils import float_round, float_compare
from odoo.tools.misc import file_path, format_date, formatLang, split_every, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval

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

NUMBER_FIGURE_TYPES = ('float', 'integer', 'monetary', 'percentage')

LINE_ID_HIERARCHY_DELIMITER = '|'

CURRENCIES_USING_LAKH = {'AFN', 'BDT', 'INR', 'MMK', 'NPR', 'PKR', 'LKR'}


class AccountReportAnnotation(models.Model):
    _name = 'account.report.annotation'
    _description = 'Account Report Annotation'

    report_id = fields.Many2one('account.report', help="The id of the annotated report.")
    line_id = fields.Char(index=True, help="The id of the annotated line.")
    text = fields.Char(string="The annotation's content.")
    date = fields.Date(help="Date considered as annotated by the annotation.")
    fiscal_position_id = fields.Many2one('account.fiscal.position', help="The fiscal position used while annotating.")

    @api.model_create_multi
    def create(self, values):
        fiscal_positions_with_foreign_vat = self.env['account.fiscal.position'].search([('foreign_vat', '!=', False)], limit=1)
        for annotation in values:
            if 'line_id' in annotation:
                annotation['line_id'] = self._remove_tax_grouping_from_line_id(annotation['line_id'])
            if 'fiscal_position_id' in annotation:
                if annotation['fiscal_position_id'] == 'domestic':
                    del annotation['fiscal_position_id']
                elif annotation['fiscal_position_id'] == 'all':
                    annotation['fiscal_position_id'] = fiscal_positions_with_foreign_vat.id
                else:
                    annotation['fiscal_position_id'] = int(annotation['fiscal_position_id'])

        return super().create(values)

    def _remove_tax_grouping_from_line_id(self, line_id):
        """
        Remove the tax grouping from the line_id. This is needed because the tax grouping is not relevant for the annotation.
        Tax grouping are any group using 'account.group' in the line_id.
        """
        return self.env['account.report']._build_line_id([
            (markup, model, res_id)
            for markup, model, res_id in self.env['account.report']._parse_line_id(line_id, markup_as_string=True)
            if model != 'account.group'
        ])

class AccountReport(models.Model):
    _inherit = 'account.report'

    horizontal_group_ids = fields.Many2many(string="Horizontal Groups", comodel_name='account.report.horizontal.group')
    annotations_ids = fields.One2many(string="Annotations", comodel_name='account.report.annotation', inverse_name='report_id')

    # Those fields allow case-by-case fine-tuning of the engine, for custom reports.
    custom_handler_model_id = fields.Many2one(string='Custom Handler Model', comodel_name='ir.model')
    custom_handler_model_name = fields.Char(string='Custom Handler Model Name', related='custom_handler_model_id.model')

    # Account Coverage Report
    is_account_coverage_report_available = fields.Boolean(compute='_compute_is_account_coverage_report_available')

    tax_closing_start_date = fields.Date(  # the default value is set in _auto_init
        string="Start Date",
        company_dependent=True
    )

    # Fields used for send reports by cron
    send_and_print_values = fields.Json(copy=False)

    def _auto_init(self):
        super()._auto_init()

        def precommit():
            self.env['ir.default'].set(
                'account.report',
                'tax_closing_start_date',
                fields.Date.context_today(self).replace(month=1, day=1),
            )
        self.env.cr.precommit.add(precommit)

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
            reports = {r.id: r.name for r in self}
            actions = self.env['ir.actions.client'] \
                .search([('name', 'in', list(reports.values())), ('tag', '=', 'account_report')]) \
                .filtered(lambda act: (ast.literal_eval(act.context).get('report_id'), act.name) in reports.items())
            self.env['ir.ui.menu'] \
                .search([
                    ('active', '=', not vals['active']),
                    ('action', 'in', [f'ir.actions.client,{action.id}' for action in actions]),
                ])\
                .active = vals['active']
        return super().write(vals)

    ####################################################
    # CRON
    ####################################################

    @api.model
    def _cron_account_report_send(self, job_count=10):
        """ Handle Send & Print async processing.
        :param job_count: maximum number of jobs to process if specified.
        """
        to_process = self.env['account.report'].search(
            [('send_and_print_values', '!=', False)],
        )
        if not to_process:
            return

        processed_count = 0
        need_retrigger = False

        for report in to_process:
            if need_retrigger:
                break
            send_and_print_vals = report.send_and_print_values
            report_partner_ids = send_and_print_vals.get('report_options', {}).get('partner_ids', [])
            need_retrigger = processed_count + len(report_partner_ids) > job_count
            partner_ids = report_partner_ids[:job_count - processed_count]
            company = self.env['res.company'].browse(send_and_print_vals['report_options']['companies'][0]['id'])
            existing_partner_ids = set(self.env['res.partner'].browse(partner_ids).exists().ids)
            for partner_id in partner_ids:
                if partner_id in existing_partner_ids:
                    options = {
                        **send_and_print_vals['report_options'],
                        'partner_ids': [partner_id],
                    }
                    self.env['account.report.send']._process_send_and_print(report=report.with_company(company), options=options)
                    processed_count += 1
                report_partner_ids.remove(partner_id)
            if report_partner_ids:
                send_and_print_vals['report_options']['partner_ids'] = report_partner_ids
                report.send_and_print_values = send_and_print_vals
            else:
                report.send_and_print_values = False

        if need_retrigger:
            self.env.ref('account_reports.ir_cron_account_report_send')._trigger()

    ####################################################
    # MENU MANAGEMENT
    ####################################################

    def _get_existing_menuitem(self):
        self.ensure_one()
        action = self.env['ir.actions.client']\
            .search([('name', '=', self.name), ('tag', '=', 'account_report')])\
            .filtered(lambda act: ast.literal_eval(act.context).get('report_id') == self.id)
        menuitem = self.env['ir.ui.menu']\
            .with_context({'active_test': False, 'ir.ui.menu.full_list': True})\
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

    def _get_filter_journal_groups(self, options):
        return self.env['account.journal.group'].search([
            *self.env['account.journal.group']._check_company_domain(self.get_report_company_ids(options)),
        ], order='sequence')

    def _init_options_journals(self, options, previous_options, additional_journals_domain=None):
        # The additional additional_journals_domain optional parameter allows calling this with an additional restriction on journals,
        # to regenerate the journal options accordingly.
        def option_value(value, selected=False, group_journals=None):
            result = {
                'id': value.id,
                'model': value._name,
                'name': value.display_name,
                'selected': selected,
            }

            if value._name == 'account.journal.group':
                result.update({
                    'title': value.display_name,
                    'journals': group_journals.ids,
                    'journal_types': list(set(group_journals.mapped('type'))),
                })
            elif value._name == 'account.journal':
                result.update({
                    'title': f"{value.name} - {value.code}",
                    'type': value.type,
                    'visible': True,
                })

            return result

        if not self.filter_journals:
            return

        previous_journals = previous_options.get('journals', [])
        previous_journal_group_action = previous_options.get('__journal_group_action', {})

        all_journals = self._get_filter_journals(options, additional_domain=additional_journals_domain)
        all_journal_groups = self._get_filter_journal_groups(options)

        options['journals'] = []
        options['selected_journal_groups'] = {}

        groups_journals_selected = set()
        options_journal_groups = []

        # First time opening the report, and make sure it's not specifically stated that we should not reset the filter
        is_opening_report = previous_options.get('is_opening_report')  # key from JS controller when report is being opened
        # a key to prevent the reset of the journals filter even when is_opening_report is True
        can_reset_journals_filter = not previous_options.get('not_reset_journals_filter')

        # 1. Handle journal group selection
        for group in all_journal_groups:
            group_journals = all_journals - group.excluded_journal_ids
            selected = False
            first_group_already_selected = bool(options['selected_journal_groups'])  # only one group should be selected at most

            # select the first group by default when opening the report
            if is_opening_report and not first_group_already_selected and can_reset_journals_filter:
                selected = True
            # Otherwise, select the previous selected group (if any)
            elif group.id == previous_journal_group_action.get('id'):
                selected = previous_journal_group_action.get('action') == 'add'

            group_option = option_value(group, selected=selected, group_journals=group_journals)
            options_journal_groups.append(group_option)

            # Select all the group journals
            if selected:
                options['selected_journal_groups'] = group_option
                groups_journals_selected |= set(group_journals.ids)

        # 2. Handle journals selection
        previous_selected_journals_ids = {
            journal['id']
            for journal in previous_journals
            if journal.get('model') == 'account.journal' and journal.get('selected')
        }

        company_journals_map = defaultdict(list)
        journals_selected = set()

        for journal in all_journals:
            selected = False

            if journal.id in groups_journals_selected:
                selected = True

            elif not options['selected_journal_groups'] and previous_journal_group_action.get('action') != 'remove':
                if journal.id in previous_selected_journals_ids:
                    selected = True

            if selected:
                journals_selected.add(journal.id)

            company_journals_map[journal.company_id].append(option_value(journal, selected=journal.id in journals_selected))

        # 3. Recompute selected groups in case the set of selected journals is equal to a group's accepted journals
        for group in options_journal_groups:
            if journals_selected == set(group['journals']):
                group['selected'] = True
                options['selected_journal_groups'] = group

        # 4. Unselect all journals if all are selected and no group is specifically selected
        if journals_selected == set(all_journals.ids) and not options['selected_journal_groups']:
            for company, journals in company_journals_map.items():
                for journal in journals:
                    journal['selected'] = False

        # 5. Build group options
        if all_journal_groups:
            options['journals'] = [{
                'id': 'divider',
                'name': _("Multi-ledger"),
                'model': 'account.journal.group',
            }] + options_journal_groups

        if not company_journals_map:
            options['name_journal_group'] = _("No Journal")
            return

        # 6. Build journals options
        if len(company_journals_map) > 1 or all_journal_groups:
            for company, journals in company_journals_map.items():
                # users may not have full access to the parent company in case they are in a branch, yet they have to see the company name
                company_name = company.sudo().display_name

                # if not is_opening_report, then gets the unfolded attribute of the company from the previous options
                unfolded = False if is_opening_report else next(
                    (entry.get('unfolded') for entry in previous_journals
                     if entry['model'] == 'res.company' and entry['name'] == company_name), False)

                for journal in journals:
                    journal['visible'] = unfolded

                options['journals'].append({
                    'id': 'divider',
                    'model': 'res.company',
                    'name': company_name,
                    'unfolded': unfolded,
                })

                options['journals'] += journals

        else:
            options['journals'].extend(next(iter(company_journals_map.values()), []))


    def _init_options_journals_names(self, options, previous_options, additional_journals_domain=None):
        all_journals = [
            journal for journal in options.get('journals', [])
            if journal['model'] == 'account.journal'
        ]
        journals_selected = [j for j in all_journals if j.get('selected')]
        # 1. Compute the name to display on the widget
        if options.get('selected_journal_groups'):
            names_to_display = [options['selected_journal_groups']['name']]
        elif len(all_journals) == len(journals_selected) or not journals_selected:
            names_to_display = [_("All Journals")]
        else:
            names_to_display = []
            for journal in options['journals']:
                if journal.get('model') == 'account.journal' and journal['selected']:
                    names_to_display += [journal['name']]

        # 2. Abbreviate the name
        max_nb_journals_displayed = 5
        nb_remaining = len(names_to_display) - max_nb_journals_displayed
        displayed_names = ', '.join(names_to_display[:max_nb_journals_displayed])
        if nb_remaining == 1:
            options['name_journal_group'] = _("%(names)s and one other", names=displayed_names)
        elif nb_remaining > 1:
            options['name_journal_group'] = _("%(names)s and %(remaining)s others", names=displayed_names, remaining=nb_remaining)
        else:
            options['name_journal_group'] = displayed_names

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
    def _init_options_aml_ir_filters(self, options, previous_options):
        options['aml_ir_filters'] = []
        if not self.filter_aml_ir_filters:
            return

        ir_filters = self.env['ir.filters'].search([('model_id', '=', 'account.move.line')])
        if not ir_filters:
            return

        aml_ir_filters = [{'id': x.id, 'name': x.name, 'selected': False} for x in ir_filters]
        previous_options_aml_ir_filters = previous_options.get('aml_ir_filters', [])
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

        def get_quarter_name(date_to, date_from):
            date_to_quarter_string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            date_from_quarter_string = format_date(self.env, fields.Date.to_string(date_from), date_format='MMM')
            return f"{date_from_quarter_string} - {date_to_quarter_string}"

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
        elif period_type == 'tax_period':
            day, month = self.env.company._get_tax_closing_start_date_attributes(self)
            months_per_period = self.env.company._get_tax_periodicity_months_delay(self)
            # We need to format ourselves the date and not switch the period type to the actual period because we do not want to write the actual period in the options but keep tax_period
            if day == 1 and month == 1 and months_per_period in (1, 3, 12):
                match months_per_period:
                    case 1:
                        string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
                    case 3:
                        string = get_quarter_name(date_to, date_from)
                    case 12:
                        string = date_to.strftime('%Y')
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = '%s - %s' % (dt_from_str, dt_to_str)

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
                string = get_quarter_name(date_to, date_from)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %(date_from)s\nto  %(date_to)s', date_from=dt_from_str, date_to=dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'currency_table_period_key': f"{date_from if mode == 'range' else 'None'}_{date_to}",
            'mode': mode,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_shifted_dates_period(self, options, period_vals, periods, tax_period=False):
        '''Shift the period.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :param periods:     The number of periods we want to move either in the future or the past
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = fields.Date.from_string(period_vals['date_to'])
        if period_type == 'month':
            date_to = date_from + relativedelta(months=periods)
        elif period_type == 'quarter':
            date_to = date_from + relativedelta(months=3 * periods)
        elif period_type == 'year':
            date_to = date_from + relativedelta(years=periods)
        elif period_type in {'custom', 'today'}:
            date_to = date_from + relativedelta(days=periods)

        if tax_period or 'tax_period' in period_type:
            month_per_period = self.env.company._get_tax_periodicity_months_delay(self)
            date_from, date_to = self.env.company._get_tax_closing_period_boundaries(date_from + relativedelta(months=month_per_period * periods), self)
            return self._get_dates_period(date_from, date_to, mode, period_type='tax_period')
        if period_type in ('fiscalyear', 'today'):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = {}
            # This loop is needed because a fiscal year can be a month, quarter, etc
            for _ in range(abs(periods)):
                date_to = (date_from if periods < 0 else date_to) + relativedelta(days=periods / abs(periods))
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
                if periods < 0:
                    date_from = company_fiscalyear_dates['date_from']
                else:
                    date_to = company_fiscalyear_dates['date_to']

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

    def _init_options_date(self, options, previous_options):
        """ Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        date = previous_options.get('date', {})
        period_date_to = date.get('date_to')
        period_date_from = date.get('date_from')
        mode = date.get('mode')
        date_filter = date.get('filter', 'custom')

        default_filter = self.default_opening_date_filter
        options_mode = 'range' if self.filter_date_range else 'single'
        date_from = date_to = period_type = False

        if mode == 'single' and options_mode == 'range':
            # 'single' date mode to 'range'.
            if date_filter:
                date_to = fields.Date.from_string(period_date_to or period_date_from)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                options_filter = 'custom'
            else:
                options_filter = default_filter
        elif mode == 'range' and options_mode == 'single':
            # 'range' date mode to 'single'.
            if date_filter == 'custom':
                date_to = fields.Date.from_string(period_date_to or period_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif date_filter:
                options_filter = date_filter
            else:
                options_filter = default_filter
        elif (mode is None or mode == options_mode) and date:
            # Same date mode.
            if date_filter == 'custom':
                if options_mode == 'range':
                    date_from = fields.Date.from_string(period_date_from)
                    date_to = fields.Date.from_string(period_date_to)
                else:
                    date_to = fields.Date.from_string(period_date_to or period_date_from)
                    date_from = date_utils.get_month(date_to)[0]

                options_filter = 'custom'
            else:
                options_filter = date_filter
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
                curr_year = fields.Date.context_today(self).year
                if company_fiscalyear_dates['date_from'].year < curr_year:
                    company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(company_fiscalyear_dates['date_to'] + relativedelta(days=1))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
            elif 'tax_period' in options_filter:
                if 'custom' in options_filter:
                    base_date = fields.Date.from_string(period_date_to)
                else:
                    base_date = fields.Date.context_today(self)

                date_from, date_to = self.env.company._get_tax_closing_period_boundaries(base_date, self)
                period_type = 'tax_period'
                start_day, start_month = self.env.company._get_tax_closing_start_date_attributes(self)
                if start_day == 1 and start_month == 1:
                    periods = self.env.company._get_tax_periodicity_months_delay(self)
                    period_type_map = {
                        1: 'month',
                        3: 'quarter',
                        12: 'year',
                    }
                    period_type = period_type_map.get(periods, 'tax_period')

        options['date'] = self._get_dates_period(
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
        )

        if any(option in options_filter for option in ['previous', 'next']):
            new_period = date.get('period', -1 if 'previous' in options_filter else 1)
            options['date'] = self._get_shifted_dates_period(options, options['date'], new_period, tax_period='tax_period' in options_filter)
            # This line is useful for the export and tax closing so that the period is set in the options.
            options['date']['period'] = new_period

        options['date']['filter'] = options_filter if options_filter != 'custom_tax_period' else 'custom'

    def _init_options_comparison(self, options, previous_options):
        """ Initialize the 'comparison' options key.

        This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if not self.filter_period_comparison:
            return

        previous_comparison = previous_options.get('comparison', {})
        previous_filter = previous_comparison.get('filter')

        period_order = previous_comparison.get('period_order') or 'descending'
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
            number_period = max(previous_comparison.get('number_period', 1) or 0, 0)
            options_filter = number_period and previous_filter or 'no_comparison'

        options['comparison'] = {
            'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
            'period_order': period_order,
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
                    period_vals = self._get_shifted_dates_period(options, previous_period, -1)
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

    def _init_options_column_percent_comparison(self, options, previous_options):
        if options['selected_horizontal_group_id'] is None:
            if self.filter_growth_comparison and len(options['columns']) == 2 and len(options.get('comparison', {}).get('periods', [])) == 1:
                options['column_percent_comparison'] = 'growth'

            if (
                    options.get('display_analytic_groupby')
                    and len(options.get('analytic_plans_groupby', [])) == 1
                    and not options.get('analytic_accounts')
                    and not options.get('comparison', {}).get('periods', [])
                    and len(options['columns']) == 2
            ):
                options['column_percent_comparison'] = 'analytic_coverage'

            if self.filter_budgets and any(budget['selected'] for budget in options.get('budgets', [])):
                options['column_percent_comparison'] = 'budget'

    def _get_options_date_domain(self, options, date_scope):
        date_from, date_to = self._get_date_bounds_info(options, date_scope)

        scope_domain = [('date', '<=', date_to)]
        if date_from:
            scope_domain += [('date', '>=', date_from)]

        return scope_domain

    def _get_date_bounds_info(self, options, date_scope):
        # Default values (the ones from 'strict_range')
        date_to = options['date']['date_to']
        date_from = options['date']['date_from'] if options['date']['mode'] == 'range' else None

        if date_scope == 'from_beginning':
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
            current_period_start, _current_period_end = self.env.company._get_tax_closing_period_boundaries(fields.Date.from_string(options['date']['date_from']), self)
            eve_of_period_start = current_period_start - relativedelta(days=1)
            date_from, date_to = self.env.company._get_tax_closing_period_boundaries(eve_of_period_start, self)

        return date_from, date_to


    ####################################################
    # OPTIONS: analytic filter
    ####################################################

    def _init_options_analytic(self, options, previous_options):
        if not self.filter_analytic:
            return


        if self.env.user.has_group('analytic.group_analytic_accounting'):
            previous_analytic_accounts = previous_options.get('analytic_accounts', [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False).search([('id', 'in', analytic_account_ids)])

            options['display_analytic'] = True
            options['analytic_accounts'] = selected_analytic_accounts.ids
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

    ####################################################
    # OPTIONS: partners
    ####################################################

    def _init_options_partner(self, options, previous_options):
        if not self.filter_partner:
            return

        options['partner'] = True
        previous_partner_ids = previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options.get('partner_categories') or []

        selected_partner_ids = [int(partner) for partner in previous_partner_ids]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_partners = selected_partner_ids and self.env['res.partner'].with_context(active_test=False).search([('id', 'in', selected_partner_ids)]) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('display_name')
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
    def _init_options_reconciled(self, options, previous_options):
        if self.filter_unreconciled:
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

    def _init_options_account_type(self, options, previous_options):
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

        if previous_options.get('account_type'):
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
    def _init_options_order_column(self, options, previous_options):
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

    def _init_options_hierarchy(self, options, previous_options):
        company_ids = self.get_report_company_ids(options)
        if self.filter_hierarchy != 'never' and self.env['account.group'].search_count(self.env['account.group']._check_company_domain(company_ids), limit=1):
            options['display_hierarchy_filter'] = True
            if 'hierarchy' in previous_options:
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
            line_id = self._get_generic_line_id('account.group', account_group.id if account_group else None, parent_line_id=parent_id)
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
            result = []
            for total, column in zip(hierarchy[group]['totals'], line['columns']):
                value = column.get('no_format')
                if isinstance(total, float) and isinstance(value, (int, float)):
                    result.append(total + value)
                else:
                    result.append('')
            return result

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

        # Precompute the account groups of the accounts in the report
        account_ids = []
        for line in lines:
            markup, res_model, model_id = self._parse_line_id(line['id'])[-1]
            if res_model == 'account.account':
                account_ids.append(model_id)
        self.env['account.account'].browse(account_ids).group_id

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

    def _init_options_prefix_groups_threshold(self, options, previous_options):
        previous_threshold = previous_options.get('prefix_groups_threshold')
        options['prefix_groups_threshold'] = self.prefix_groups_threshold

    ####################################################
    # OPTIONS: fiscal position (multi vat)
    ####################################################

    def _init_options_fiscal_position(self, options, previous_options):
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

            if previous_options.get('fiscal_position') in accepted_prev_vals:
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
            previous_fpos = previous_options.get('fiscal_position')
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
                ('country_id', '=', self.country_id.id),
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

    def _init_options_companies(self, options, previous_options):
        if previous_options.get('forced_companies'):
            options['forced_companies'] = previous_options['forced_companies']
            companies = self.env.company.browse(previous_options['forced_companies'])
        elif self.filter_multi_company == 'selector':
            companies = self.env.companies
        elif self.filter_multi_company == 'tax_units':
            companies = self._multi_company_tax_units_init_options(options, previous_options=previous_options)
        else:
            # Multi-company is disabled for this report ; only accept the sub-branches of the current company from the selector
            companies = self.env.company._accessible_branches()

        options['companies'] = [{'name': c.name, 'id': c.id, 'currency_id': c.currency_id.id} for c in companies]

    def _multi_company_tax_units_init_options(self, options, previous_options):
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

        if previous_options.get('tax_unit') in companies_authorized_tax_unit_opt:
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
    def _init_options_multi_currency(self, options, previous_options):
        options['multi_currency'] = (
            any([company.get('currency_id') != options['companies'][0].get('currency_id') for company in options['companies']])
            or any([column.figure_type != 'monetary' for column in self.column_ids])
            or any(expression.figure_type and expression.figure_type != 'monetary' for expression in self.line_ids.expression_ids)
        )

    ####################################################
    # OPTIONS: CURRENCY TABLE
    ####################################################
    def _init_options_currency_table(self, options, previous_options):
        companies = self.env['res.company'].browse(self.get_report_company_ids(options))
        table_type = 'monocurrency' if self.env['res.currency']._check_currency_table_monocurrency(companies) else self.currency_translation

        periods = {}
        for col_group in options['column_groups'].values():
            if col_group['forced_options'].get('no_impact_on_currency_table'):
                # This key is used to ignore the colum group in the creation of the periods list for
                # the currency table. This way, its dates won't influence. It's useful for groups corresponding
                # to an initial balance of some sorts, like on the Trial Balance.
                continue

            col_group_date = col_group['forced_options'].get('date', options['date'])

            col_group_date_from = col_group_date['date_from'] if col_group_date['mode'] == 'range' else None
            col_group_date_to = col_group_date['date_to']
            period_key = col_group_date['currency_table_period_key']

            already_present_period = periods.get(period_key)
            if already_present_period:
                # This can happen for custom reports, needing to enforce the same rates on multiple column groups with
                # different dates (e.g. Trial Balance). In that case, the date_from and date_to of the currency table period must respectively
                # be the lowest and highest among those groups.
                if col_group_date_from and already_present_period['from'] > col_group_date_from:
                    already_present_period['from'] = col_group_date_from

                if already_present_period['to'] < col_group_date_to:
                    already_present_period['to'] = col_group_date_to
            else:
                periods[period_key] = {
                    'from': col_group_date_from,
                    'to': col_group_date_to,
                }

        options['currency_table'] = {'type': table_type, 'periods': periods}

    @api.model
    def _currency_table_apply_rate(self, value: SQL) -> SQL:
        """ Returns an SQL term to use in a SELECT statement converting the value passed as parameter into the current company's currency, using the
        currency table (which must be joined in the query as well ; using _currency_table_aml_join for account.move.line, or _get_currency_table for
        other more specific uses).
        """
        return SQL("(%(value)s) * COALESCE(account_currency_table.rate, 1)", value=value)

    @api.model
    def _currency_table_aml_join(self, options, aml_alias=SQL('account_move_line')) -> SQL:
        """ Returns the JOIN condition to the currency table in a query needing to use it to convert aml balances from one currency to another.
        """
        if options['currency_table']['type'] == 'cta':
            return SQL(
                """
                    JOIN account_account aml_ct_account
                        ON aml_ct_account.id = %(aml_table)s.account_id
                    LEFT JOIN %(currency_table)s
                        ON %(aml_table)s.company_id = account_currency_table.company_id
                        AND (
                            account_currency_table.rate_type = CASE
                                WHEN aml_ct_account.account_type LIKE ANY (ARRAY[%(income_prefix)s, %(expense_prefix)s, 'equity_unaffected']) THEN 'average'
                                WHEN aml_ct_account.account_type LIKE %(equity_prefix)s THEN 'historical'
                                ELSE 'current'
                            END
                        )
                        AND (account_currency_table.date_from IS NULL OR account_currency_table.date_from <= %(aml_table)s.date)
                        AND (account_currency_table.date_next IS NULL OR account_currency_table.date_next > %(aml_table)s.date)
                        AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
                """,
                aml_table=aml_alias,
                equity_prefix='equity%',
                income_prefix='income%',
                expense_prefix='expense%',
                currency_table=self._get_currency_table(options),
                period_key=options['date']['currency_table_period_key'],
            )

        return SQL(
            """
                JOIN %(currency_table)s
                    ON %(aml_table)s.company_id = account_currency_table.company_id
                    AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
            """,
            aml_table=aml_alias,
            currency_table=self._get_currency_table(options),
            period_key=options['date']['currency_table_period_key'],
        )

    @api.model
    def _get_currency_table(self, options) -> SQL:
        """ Returns the currency table table definition to be injected in the JOIN condition of an SQL query needing to use it.
        """
        if options['currency_table']['type'] == 'monocurrency':
            companies = self.env['res.company'].browse(self.get_report_company_ids(options))
            return self.env['res.currency']._get_monocurrency_currency_table_sql(companies, use_cta_rates=options['currency_table']['type'] == 'cta')

        return SQL('account_currency_table')

    def _init_currency_table(self, options):
        """ Creates the currency table temporary table if necessary, using the provided options to compute its periods.
        This function should always be called before any query invovlving the currency table is run.
        """
        if options['currency_table']['type'] != 'monocurrency':
            companies = self.env['res.company'].browse(self.get_report_company_ids(options))

            self.env['res.currency']._create_currency_table(
                companies,
                [(period_key, period['from'], period['to']) for period_key, period in options['currency_table']['periods'].items()],
                use_cta_rates=options['currency_table']['type'] == 'cta',
            )

    ####################################################
    # OPTIONS: ROUNDING UNIT
    ####################################################
    def _init_options_rounding_unit(self, options, previous_options):
        default = 'decimals'
        options['rounding_unit'] = previous_options.get('rounding_unit', default)
        options['rounding_unit_names'] = self._get_rounding_unit_names()

    def _get_rounding_unit_names(self):
        currency_symbol = self.env.company.currency_id.symbol
        currency_name = self.env.company.currency_id.name

        rounding_unit_names = [
            ('decimals', (f'.{currency_symbol}', '')),
            ('units', (f'{currency_symbol}', '')),
            ('thousands', (f'K{currency_symbol}', _('Amounts in Thousands'))),
            ('millions', (f'M{currency_symbol}', _('Amounts in Millions'))),
        ]

        if currency_name in CURRENCIES_USING_LAKH:
            rounding_unit_names.insert(3, ('lakhs', (f'L{currency_symbol}', _('Amounts in Lakhs'))))

        return dict(rounding_unit_names)

    # ####################################################
    # OPTIONS: ALL ENTRIES
    ####################################################
    def _init_options_all_entries(self, options, previous_options):
        if self.filter_show_draft:
            options['all_entries'] = previous_options.get('all_entries', False)
        else:
            options['all_entries'] = False

    ####################################################
    # OPTIONS: UNFOLDED LINES
    ####################################################
    def _init_options_unfolded(self, options, previous_options):
        options['unfold_all'] = self.filter_unfold_all and previous_options.get('unfold_all', False)

        previous_section_source_id = previous_options.get('sections_source_id')
        if not previous_section_source_id or previous_section_source_id == options['sections_source_id']:
            # Only keep the unfolded lines if they belong to the same report or a section of the same report
            options['unfolded_lines'] = previous_options.get('unfolded_lines', [])
        else:
            options['unfolded_lines'] = []

    ####################################################
    # OPTIONS: HIDE LINE AT 0
    ####################################################
    def _init_options_hide_0_lines(self, options, previous_options):
        if self.filter_hide_0_lines != 'never':
            previous_val = previous_options.get('hide_0_lines')
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
            is_zero_line = all(col.get('figure_type') not in NUMBER_FIGURE_TYPES or col.get('is_zero', True) for col in line['columns'])
            if is_zero_line and line['id'] not in has_visible_children:
                lines_to_hide.add(line['id'])
            if line.get('parent_id') and line['id'] not in lines_to_hide:
                has_visible_children.add(line['parent_id'])
        return list(filter(lambda x: x['id'] not in lines_to_hide, lines))

    ####################################################
    # OPTIONS: HORIZONTAL GROUP
    ####################################################
    def _init_options_horizontal_groups(self, options, previous_options):
        options['available_horizontal_groups'] = [
            {
                'id': horizontal_group.id,
                'name': horizontal_group.name,
            }
            for horizontal_group in self.horizontal_group_ids
        ]
        previous_selected = previous_options.get('selected_horizontal_group_id')
        options['selected_horizontal_group_id'] = previous_selected if previous_selected in self.horizontal_group_ids.ids else None

    ####################################################
    # OPTIONS: SEARCH BAR
    ####################################################
    def _init_options_search_bar(self, options, previous_options):
        if self.search_bar:
            options['search_bar'] = True
            if 'default_filter_accounts' not in self._context and 'filter_search_bar' in previous_options:
                options['filter_search_bar'] = previous_options['filter_search_bar']

    ####################################################
    # OPTIONS: COLUMN HEADERS
    ####################################################

    def _init_options_column_headers(self, options, previous_options):
        # Prepare column headers, in case the order of the comparison is ascending we reverse the order of the columns
        all_comparison_date_vals = ([options['date']] + options.get('comparison', {}).get('periods', []))
        if options.get('comparison') and options['comparison']['period_order'] == 'ascending':
            all_comparison_date_vals = all_comparison_date_vals[::-1]

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
        else:
            # Insert budget column headers if needed
            selected_budgets = [budget for budget in options.get('budgets', []) if budget['selected']]
            if selected_budgets:
                budget_headers = [{
                    'name': '',
                    'forced_options': {
                        'budget_base': True,
                    }
                }]

                for budget in selected_budgets:
                    # Add budget amount column
                    budget_headers.append({
                        'name': budget['name'],
                        'forced_options': {
                            'compute_budget': budget['id'],
                        },
                        'colspan': 1,
                    })
                    if len(self.column_ids.filtered(lambda column: column.figure_type == 'monetary')) == 1:
                        # Add budget percentage column (only if one column in the report)
                        budget_headers.append({
                            'name': "%",
                            'forced_options': {
                                'budget_percentage': budget['id'],
                            },
                            'colspan': 1,
                        })

                column_headers.append(budget_headers)

        options['column_headers'] = column_headers

    ####################################################
    # OPTIONS: COLUMNS
    ####################################################
    def _init_options_columns(self, options, previous_options):
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}
        all_column_group_vals_in_order = self._generate_columns_group_vals_recursively(options['column_headers'], default_group_vals)

        columns, column_groups = self._build_columns_from_column_group_vals(options, all_column_group_vals_in_order)

        options['columns'] = columns
        options['column_groups'] = column_groups

        # Debug column is only shown when there is a single column group, so that we can display all the subtotals of the line in a clear way
        options['show_debug_column'] = options['export_mode'] != 'print' \
                                       and self.env.user.has_group('base.group_no_one') \
                                       and len(options['column_groups']) == 1 \
                                       and len(self.line_ids) > 0 # No debug column on fully dynamic reports by default (they can customize this)

        # Show an additional column summing all the horizontal groups if there is no comparison and only one level of horizontal group
        options['show_horizontal_group_total'] = options.get('selected_horizontal_group_id') \
                                                 and options.get('comparison', {}).get('filter') == 'no_comparison' \
                                                 and len(self.column_ids) == 1 \
                                                 and len(options['column_headers']) == 2

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

            # for budget, only one column in needed, regardless of the number of columns in the report
            if any(budget_key in column_group_val['forced_options'] for budget_key in ('compute_budget', 'budget_percentage')):
                columns.append({
                    'name': "",
                    'column_group_key': column_group_key,
                    'expression_label': 'balance',
                    'sortable': False,
                    'figure_type': 'monetary',
                    'blank_if_zero': False,
                    'style': "text-align: center; white-space: nowrap;",
                })

            else:
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

    def _init_options_buttons(self, options, previous_options):
        options['buttons'] = [
            {'name': _('PDF'), 'sequence': 10, 'action': 'export_file', 'action_param': 'export_to_pdf', 'file_export_type': _('PDF'), 'branch_allowed': True, 'always_show': True},
            {'name': _('XLSX'), 'sequence': 20, 'action': 'export_file', 'action_param': 'export_to_xlsx', 'file_export_type': _('XLSX'), 'branch_allowed': True, 'always_show': True},
        ]

    def open_account_report_file_download_error_wizard(self, errors, content):
        self.ensure_one()

        model = 'account.report.file.download.error.wizard'
        vals = {'actionable_errors': errors}

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

    def _init_options_section_buttons(self, options, previous_options):
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
    def _init_options_variants(self, options, previous_options):
        allowed_variant_ids = set()

        previous_section_source_id = previous_options.get('sections_source_id')
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

        previous_opt_report_id = previous_options.get('selected_variant_id')
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
    def _init_options_sections(self, options, previous_options):
        if options.get('selected_variant_id'):
            options['sections_source_id'] = options['selected_variant_id']
        else:
            options['sections_source_id'] = self.id

        source_report = self.env['account.report'].browse(options['sections_source_id'])

        available_sections = source_report.section_report_ids if source_report.use_sections else self.env['account.report']
        options['sections'] = [{'name': section.name, 'id': section.id} for section in available_sections]

        if available_sections:
            section_id = previous_options.get('selected_section_id')
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
    def _init_options_report_id(self, options, previous_options):
        if previous_options.get('no_report_reroute'):
            # Used for exports
            options['report_id'] = self.id
        else:
            options['report_id'] = options.get('selected_section_id') or options.get('selected_variant_id') or self.id

    ####################################################
    # OPTIONS: EXPORT MODE
    ####################################################
    def _init_options_export_mode(self, options, previous_options):
        options['export_mode'] = previous_options.get('export_mode')

    ####################################################
    # OPTIONS: HORIZONTAL SPLIT
    ####################################################
    def _init_options_horizontal_split(self, options, previous_options):
        if any(line.horizontal_split_side for line in self.line_ids):
            options['horizontal_split'] = previous_options.get('horizontal_split', False)

    ####################################################
    # OPTIONS: CUSTOM
    ####################################################
    def _init_options_custom(self, options, previous_options):
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model:
            self.env[custom_handler_model]._custom_options_initializer(self, options, previous_options)

    ####################################################
    # OPTIONS: INTEGER ROUNDING
    ####################################################
    def _init_options_integer_rounding(self, options, previous_options):
        if self.integer_rounding:
            options['integer_rounding'] = self.integer_rounding
            if options.get('export_mode') == 'file':
                options['integer_rounding_enabled'] = True
            else:
                options['integer_rounding_enabled'] = previous_options.get('integer_rounding_enabled', True)
            return options

    ####################################################
    # OPTIONS: BUDGETS
    ####################################################
    def _init_options_budgets(self, options, previous_options):
        if self.filter_budgets:
            previous_selection = {budget_option['id'] for budget_option in previous_options.get('budgets', []) if budget_option.get('selected')}

            options['budgets'] = [
                {
                    'id': budget.id,
                    'name': budget.name,
                    'selected': budget.id in previous_selection,
                    'company_id': budget.company_id.id,
                }
                for budget in self.env['account.report.budget'].search([('company_id', '=', self.env.company.id)])
            ]
            options['show_all_accounts'] = previous_options.get('show_all_accounts') or False

    ####################################################
    # OPTIONS: READONLY QUERY
    ####################################################
    def _init_options_readonly_query(self, options, previous_options):
        options['readonly_query'] = (
            options['currency_table']['type'] == 'monocurrency'
            and not any(budget_opt['selected'] for budget_opt in options.get('budgets', []))
        )

    ####################################################
    # OPTIONS: CORE
    ####################################################

    @api.readonly
    def get_options(self, previous_options):
        self.ensure_one()

        initializers_in_sequence = self._get_options_initializers_in_sequence()

        options = {}

        if previous_options.get('_running_export_test'):
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
            variant_options = {**previous_options}
            for reroute_opt_key in ('selected_variant_id', 'selected_section_id', 'variants_source_id', 'sections_source_id'):
                opt_val = options.get(reroute_opt_key)
                if opt_val:
                    variant_options[reroute_opt_key] = opt_val

            return self.env['account.report'].browse(options['report_id']).get_options(variant_options)

        # No reroute; keep on and compute the other options
        for initializer_index in range(reroute_initializer_index + 1, len(initializers_in_sequence)):
            initializer = initializers_in_sequence[initializer_index]
            initializer(options, previous_options=previous_options)

        options_companies = self.env['res.company'].browse(self.get_report_company_ids(options))
        # Set export buttons to 'branch_allowed' if the currently selected company branches all share the same VAT
        # number and no unselected sub-branch of the active company has the same VAT number. Companies with an empty VAT
        # field will be considered as having the same VAT number as their closest parent with a non-empty VAT.
        if options.get('enable_export_buttons_for_common_vat_in_branches'):
            report_accepted_company_ids = set(options_companies.ids)
            same_vat_branch_ids = set(self.env.company._get_branches_with_same_vat().ids)
            if report_accepted_company_ids == same_vat_branch_ids:
                options['buttons'] = [{**button, 'branch_allowed': button.get('branch_allowed', True)} for button in options['buttons']]

        # Disable buttons without branch_allowed = True if not all branches are selected
        if not options_companies._all_branches_selected():
            for button in filter(lambda x: not x.get('branch_allowed'), options['buttons']):
                button['error_action'] = 'show_error_branch_allowed'

        # Sort the buttons list by sequence, for rendering
        options['buttons'] = sorted(options['buttons'], key=lambda x: x.get('sequence', 90))

        # Sanitizing date_from and date_to since they need to be JSON-serializable when exporting the report
        # on the server side, since the ORM converts them to strings automatically when sending them to the client.
        for date_dict in (
            [options.get('date', {})] +
            [group_data['forced_options']['date'] for group_data in options['column_groups'].values() if group_data.get('forced_options', {}).get('date')]
        ):
            if (date_from := date_dict.get('date_from')) and not isinstance(date_from, str):
                date_dict['date_from'] = fields.Date.to_string(date_from)

            if (date_to := date_dict.get('date_to')) and not isinstance(date_to, str):
                date_dict['date_to'] = fields.Date.to_string(date_to)

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
            self._init_options_export_mode: 60,
            self._init_options_integer_rounding: 70,
            self._init_options_journals: 80,
            self._init_options_journals_names: 90,

            'default': 200,

            self._init_options_column_headers: 990,
            self._init_options_columns: 1000,
            self._init_options_column_percent_comparison: 1010,
            self._init_options_order_column: 1020,
            self._init_options_hierarchy: 1030,
            self._init_options_prefix_groups_threshold: 1040,
            self._init_options_custom: 1050,
            self._init_options_currency_table: 1055,
            self._init_options_section_buttons: 1060,
            self._init_options_readonly_query: 1070,
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
        if not options.get('compute_budget'):
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

        if options.get('forced_domain'):
            # That option key is set when splitting options between column groups
            domain += options['forced_domain']

        return domain

    ####################################################
    # QUERIES
    ####################################################

    def _get_report_query(self, options, date_scope, domain=None) -> Query:
        """ Get a Query object that references the records needed for this report. """
        domain = self._get_options_domain(options, date_scope) + (domain or [])

        self.env['account.move.line'].check_access('read')

        query = self.env['account.move.line']._where_calc(domain)

        if options.get('compute_budget'):
            self._create_report_budget_temp_table(options)
            query._tables['account_move_line'] = SQL.identifier('account_report_budget_temp_aml')
            query.add_where(SQL(
                "%s AND budget_id = %s",
                query.where_clause,
                options['compute_budget'],
            ))

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query

    def _create_report_budget_temp_table(self, options):
        self._cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='account_report_budget_temp_aml'")
        if self._cr.fetchone():
            return

        stored_aml_fields, fields_to_insert = self.env['account.move.line']._prepare_aml_shadowing_for_report({
            'id': SQL.identifier("id"),
            'balance': SQL.identifier('amount'),
            'company_id': self.env.company.id,
            'parent_state': 'posted',
            'date': SQL.identifier('date'),
            'account_id': SQL.identifier("account_id"),
            'debit': SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
            'credit': SQL("CASE WHEN (amount < 0) THEN -amount else 0 END"),
        })

        self._cr.execute(SQL(
            """
                -- Create a temporary table, dropping not null constraints because we're not filling those columns
                CREATE TEMPORARY TABLE IF NOT EXISTS account_report_budget_temp_aml () inherits (account_move_line) ON COMMIT DROP;
                ALTER TABLE account_report_budget_temp_aml NO INHERIT account_move_line;
                ALTER TABLE account_report_budget_temp_aml ALTER COLUMN move_id DROP NOT NULL;
                ALTER TABLE account_report_budget_temp_aml ALTER COLUMN currency_id DROP NOT NULL;
                ALTER TABLE account_report_budget_temp_aml ALTER COLUMN journal_id DROP NOT NULL;
                ALTER TABLE account_report_budget_temp_aml ALTER COLUMN display_type DROP NOT NULL;
                ALTER TABLE account_report_budget_temp_aml ADD budget_id INTEGER NOT NULL;

                INSERT INTO account_report_budget_temp_aml (%(stored_aml_fields)s, budget_id)
                SELECT %(fields_to_insert)s, budget_id
                FROM account_report_budget_item
                WHERE budget_id IN %(available_budget_ids)s;

                -- Create a supporting index to avoid seq.scans
                CREATE INDEX IF NOT EXISTS account_report_budget_temp_aml__composite_idx ON account_report_budget_temp_aml (account_id, journal_id, date, company_id);
                -- Update statistics for correct planning
                ANALYZE account_report_budget_temp_aml
            """,
            stored_aml_fields=stored_aml_fields,
            fields_to_insert=fields_to_insert,
            available_budget_ids=tuple(budget_option['id'] for budget_option in options['budgets']),
        ))

        if options.get('show_all_accounts'):
            stored_aml_fields, fields_to_insert = self.env['account.move.line']._prepare_aml_shadowing_for_report({
                # Using nextval will consume a sequence number, we decide to do it to avoid comparing apples and oranges
                'id': SQL("(SELECT nextval('account_report_budget_item_id_seq'))"),
                'balance': SQL("0"),
                'company_id': self.env.company.id,
                'parent_state': 'posted',
                'date': SQL("%s", options['date']['date_from']),
                'account_id': SQL.identifier("accounts", "id"),
                'debit': SQL("0"),
                'credit': SQL("0"),
            })
            accounts_subquery = self.env['account.account']._where_calc([
                ('company_ids', 'in', self.get_report_company_ids(options)),
                ('internal_group', 'in', ['income', 'expense']),
            ])
            self._cr.execute(SQL(
                """
                -- Insert dynamic combinations of account_id and budget_id into the temporary table
                INSERT INTO account_report_budget_temp_aml (%(stored_aml_fields)s, budget_id)
                     SELECT %(fields_to_insert)s, budgets.id AS budget_id
                       FROM (%(accounts_subquery)s) AS accounts
                 CROSS JOIN (
                                SELECT id
                                  FROM account_report_budget
                                 WHERE id IN %(available_budget_ids)s
                            ) AS budgets
                """,
                stored_aml_fields=stored_aml_fields,
                fields_to_insert=fields_to_insert,
                accounts_subquery=accounts_subquery.select(),
                available_budget_ids=tuple(budget_option['id'] for budget_option in options['budgets']),
                income='income%',
                expense='expense%',
                company_ids=tuple(),
            ))

    ####################################################
    # LINE IDS MANAGEMENT HELPERS
    ####################################################
    def _get_generic_line_id(self, model_name, value, markup=None, parent_line_id=None):
        """ Generates a generic line id from the provided parameters.

        Such a generic id consists of a string repeating 1 to n times the following pattern:
        markup-model-value, each occurence separated by a LINE_ID_HIERARCHY_DELIMITER character from the previous one.

        Each pattern corresponds to a level of hierarchy in the report, so that
        the n-1 patterns starting the id of a line actually form the id of its generator line.
        EX: a~b~c|d~e~f|g~h~i => This line is a subline generated by a~b~c|d~e~f where | is the LINE_ID_HIERARCHY_DELIMITER.

        Each pattern consists of the three following elements:
        - markup:  a (possibly empty) free string or json-formatted dict allowing finer identification of the line
                   (like the name of the field for account.accounting.reports)

        - model:   the model this line has been generated for, or an empty string if there is none

        - value:   the groupby value for this line (typically the id of a record
                   or the value of a field), or an empty string if there isn't any.
        """
        self.ensure_one()

        if parent_line_id:
            parent_id_list = self._parse_line_id(parent_line_id, markup_as_string=True)
        else:
            parent_id_list = [(None, 'account.report', self.id)]

        # In case the markup is a dict, it must be converted to a string, but in a way such that the keys are ordered alphabetically.
        # This is useful, notably for annotations where the ids of the lines are stored, therefore requiring a consistent ordering
        if isinstance(markup, dict):
            markup = json.dumps(markup, sort_keys=True)

        new_line = self._build_line_id(parent_id_list + [(markup, model_name, value)])
        return new_line

    @api.model
    def _get_line_from_xml_id(self, lines, xml_id):
        """ Helper function to get a specific account report line from the xmlid """
        report_line = self.env.ref(xml_id, raise_if_not_found=False)
        return next(
            line for line in lines
            if self._get_model_info_from_id(line['id']) == ('account.report.line', report_line.id)
        )

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
            return x if x is not None and x is not False else ''
        return LINE_ID_HIERARCHY_DELIMITER.join(f'{convert_none(markup)}~{convert_none(model)}~{convert_none(value)}' for markup, model, value in current)

    @api.model
    def _build_parent_line_id(self, current):
        """Build the parent_line id based on the current position in the report.

        For instance, if current is [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)], it will return
        markup1~account.account~5
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        to_process = [(json.dumps(markup) if isinstance(markup, dict) else markup, model, value) for markup, model, value in current[:-1]]
        return self._build_line_id(to_process)

    @api.model
    def _parse_markup(self, markup):
        if not markup:
            return markup
        try:
            result = json.loads(markup)
        except json.JSONDecodeError:  # the markup is not a JSON object
            return markup
        if isinstance(result, dict):
            return result

        return markup

    @api.model
    def _parse_line_id(self, line_id, markup_as_string=False):
        """Parse the provided string line id and convert it to its list representation.
        Empty strings for model and value will be converted to None.

        For instance if line_id is markup1~account.account~5|markup2~res.partner~8 (where | is the LINE_ID_HIERARCHY_DELIMITER),
        it will return [('markup1', 'account.account', 5), ('markup2', 'res.partner', 8)]
        :param line_id (str): the generic line id to parse
        """
        return line_id and [
            # When there is a model, value is an id, so we cast it to and int. Else, we keep the original value (for groupby lines on
            # non-relational fields, for example).
            (self._parse_markup(markup) if not markup_as_string else markup, model or None, int(value) if model and value else (value or None))
            for markup, model, value in (key.rsplit('~', 2) for key in line_id.split(LINE_ID_HIERARCHY_DELIMITER))
        ] or []

    @api.model
    def _get_unfolded_lines(self, lines, parent_line_id):
        """ Return a list of all children lines for specified parent_line_id.
        NB: It will return the parent_line itself!

        For instance if parent_line_ids is '~account.report.line~84|{"groupby": "currency_id"}~res.currency~174'
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
        return {
            **self._caret_options_initializer_default(),
            **(self.env[self.custom_handler_model_name]._caret_options_initializer() if self.custom_handler_model_id else {}),
        }

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
        # When coming from a specific account, the unfold must only be retained
        # on the specified account. Better performance and more ergonomic
        # as it opens what client asked. And "Unfold All" is 1 clic away.
        options["unfold_all"] = False

        records_to_unfold = []
        for _dummy, model, record_id in self._parse_line_id(params['line_id']):
            if model in ('account.group', 'account.account'):
                records_to_unfold.append((model, record_id))

        if not records_to_unfold or records_to_unfold[-1][0] != 'account.account':
            raise UserError(_("'Open General Ledger' caret option is only available form report lines targetting accounts."))

        general_ledger = self.env.ref('account_reports.general_ledger_report')
        lines_to_unfold = []
        for model, record_id in records_to_unfold:
            parent_line_id = lines_to_unfold[-1] if lines_to_unfold else None
            # Re-create the hierarchy of account groups that should be unfolded in GL
            generic_line_id = general_ledger._get_generic_line_id(model, record_id, parent_line_id=parent_line_id)
            lines_to_unfold.append(generic_line_id)

        options['not_reset_journals_filter'] = True  # prevents resetting the default journal group
        gl_options = general_ledger.get_options(options)
        gl_options['not_reset_journals_filter'] = True  # prevents resetting the default journal group
        gl_options['unfolded_lines'] = lines_to_unfold

        account_id = self.env['account.account'].browse(records_to_unfold[-1][1])
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
            options["report_id"] = report_to_call.id
            return report_to_call.dispatch_report_action(options, action, action_param=action_param, on_sections_source=False)

        if self.id not in (options['report_id'], options.get('sections_source_id')):
            raise UserError(_("Trying to dispatch an action on a report not compatible with the provided options."))

        args = [options, action_param] if action_param is not None else [options]
        model = self
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model and hasattr(self.env[custom_handler_model], action):
            model = self.env[custom_handler_model]
        report_method = get_public_method(model, action)
        return report_method(model, *args)

    def _get_custom_report_function(self, function_name, prefix):
        """ Returns a report function from its name, first checking it to ensure it's private (and raising if it isn't).
            This helper is used by custom report fields containing function names.
            The function will be called on the report's custom handler if it exists, or on the report itself otherwise.
        """
        self.ensure_one()
        function_name_prefix = f'_report_{prefix}_'
        if not function_name.startswith(function_name_prefix):
            raise UserError(_("Method '%(method_name)s' must start with the '%(prefix)s' prefix.", method_name=function_name, prefix=function_name_prefix))

        if self.custom_handler_model_id:
            handler = self.env[self.custom_handler_model_name]
            if hasattr(handler, function_name):
                return getattr(handler, function_name)

        if not hasattr(self, function_name):
            raise UserError(_("Invalid method “%s”", function_name))
        # Call the check method without the private prefix to check for others security risks.
        return getattr(self, function_name)

    def _get_lines(self, options, all_column_groups_expression_totals=None, warnings=None):
        self.ensure_one()

        if options['report_id'] != self.id:
            # Should never happen; just there to prevent BIG issues and directly spot them
            raise UserError(_("Inconsistent report_id in options dictionary. Options says %(options_report)s; report is %(report)s.", options_report=options['report_id'], report=self.id))

        # Necessary to ensure consistency of the data if some of them haven't been written in database yet
        self.env.flush_all()

        if warnings is not None:
            self._generate_common_warnings(options, warnings)

        # Merge static and dynamic lines in a common list
        if all_column_groups_expression_totals is None:
            self._init_currency_table(options)
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

            parent_generic_id = None

            if line.parent_id:
                # Normally, the parent line has necessarily been treated in a previous iteration
                try:
                    parent_generic_id = line_cache[line.parent_id]['id']
                except KeyError as e:
                    raise UserError(_(
                        "Line '%(child)s' is configured to appear before its parent '%(parent)s'. This is not allowed.",
                        child=line.name, parent=e.args[0].name
                    ))

            line_dict = self._get_static_line_dict(options, line, all_column_groups_expression_totals, parent_id=parent_generic_id)
            line_cache[line] = line_dict

            if line.hide_if_zero:
                hide_if_zero_lines += line

            lines.append(line_dict)

        for dummy, left_dynamic_line in dynamic_lines:
            lines.append(left_dynamic_line)

        # Manage growth comparison
        if options.get('column_percent_comparison') == 'growth':
            for line in lines:
                first_value, second_value = line['columns'][0]['no_format'], line['columns'][1]['no_format']

                green_on_positive = True
                model, line_id = self._get_model_info_from_id(line['id'])

                if model == 'account.report.line' and line_id:
                    report_line = self.env['account.report.line'].browse(line_id)
                    compared_expression = report_line.expression_ids.filtered(
                        lambda expr: expr.label == line['columns'][0]['expression_label']
                    )
                    green_on_positive = compared_expression.green_on_positive

                line['column_percent_comparison_data'] = self._compute_column_percent_comparison_data(
                    options, first_value, second_value, green_on_positive=green_on_positive
                )
        # Manage budget comparison
        elif options.get('column_percent_comparison') == 'budget':
            for line in lines:
                self._set_budget_column_comparisons(options, line)

        elif options.get('column_percent_comparison') == 'analytic_coverage':
            for line in lines:
                first_value, second_value = line['columns'][0]['no_format'], line['columns'][1]['no_format']
                line['column_percent_comparison_data'] = self._compute_column_percent_comparison_data(options, first_value, second_value, green_on_positive=False)

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

        # Clean up before generating totals, so _add_totals_below_sections doesn't create
        # a total line for a parent whose children were all hidden.
        if hidden_lines_dict_ids:
            lines = self._cleanup_empty_sections(lines)

        # Handle totals below sections for static lines
        lines = self._add_totals_below_sections(lines, options)

        # Unfold lines (static or dynamic) if necessary and add totals below section to dynamic lines
        lines = self._fully_unfold_lines_if_needed(lines, options)

        self._inject_account_names_for_consolidation(lines)

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(self, options, lines)

        if warnings is not None:
            custom_handler_name = self.custom_handler_model_name or self.root_report_id.custom_handler_model_name
            if custom_handler_name:
                self.env[custom_handler_name]._customize_warnings(self, options, all_column_groups_expression_totals, warnings)

        # Format values in columns of lines that will be displayed
        self._format_column_values(options, lines)

        if options.get('export_mode') == 'print' and options.get('hide_0_lines'):
            lines = self._filter_out_0_lines(lines)
            lines = self._cleanup_empty_sections(lines)

        return lines

    # Deprecated, removed in master.
    @api.model
    def format_column_values(self, options, lines):
        self._format_column_values(options, lines, force_format=True)

        return lines

    def format_column_values_from_client(self, options, lines):
        """ Format column values for display. Called via dispatch_report_action when rounding unit changes on client side."""
        self._format_column_values(options, lines, force_format=True)

        return lines

    def _format_column_values(self, options, line_dict_list, force_format=False):
        for line_dict in line_dict_list:
            for column_dict in line_dict['columns']:
                if 'name' in column_dict and not force_format:
                    # Columns which have already received a name are assumed to be already formatted; nothing needs to be done for them.
                    # This gives additional flexibility to custom reports, if needed.
                    continue

                if not column_dict:
                    continue
                elif column_dict.get('is_zero') and column_dict.get('blank_if_zero'):
                    rslt = ''
                elif options.get('export_mode') == 'file':
                    rslt = column_dict.get('no_format', '')
                else:
                    rslt = self.format_value(
                        options,
                        column_dict.get('no_format'),
                        column_dict.get('figure_type'),
                        format_params=column_dict.get('format_params'),
                    )

                column_dict['name'] = rslt

            # Handle the total in case of an horizontal group when there is no comparison and only one level of horizontal group
            if options.get('show_horizontal_group_total'):
                # In case the line has no formula
                if all(column['no_format'] is None for column in line_dict['columns']):
                    continue
                # In case total below section, some line don't have the value displayed
                if self.env.company.totals_below_sections and not options.get('ignore_totals_below_sections') and line_dict['unfolded']:
                    continue

                figure_type_is_valid = all(column['figure_type'] in {'float', 'integer', 'monetary'} for column in line_dict['columns'])
                total_value = sum(column["no_format"] for column in line_dict['columns']) if figure_type_is_valid else None
                line_dict['horizontal_group_total_data'] = {
                    'name': self.format_value(
                        options,
                        total_value,
                        line_dict['columns'][0]['figure_type'],
                        format_params=line_dict['columns'][0]['format_params'],
                    ),
                    'no_format': total_value,
                }

    def _generate_common_warnings(self, options, warnings):
        # Display a warning if we're displaying only the data of the current company, but it's also part of a tax unit
        if options.get('available_tax_units') and options['tax_unit'] == 'company_only':
            warnings['account_reports.common_warning_tax_unit'] = {}

        report_company_ids = self.get_report_company_ids(options)
        # The _accessible_branches function will return the accessible branches from the ones that are already selected,
        # and the report_company_ids function will return the current company and its branches (that are selected) with the same VAT
        # or tax unit. Therefore, we will display the warning only when the selected companies do not have the same VAT
        # and in the context of branches.
        if self.filter_multi_company == 'tax_units' and any(accessible_branch.id not in report_company_ids for accessible_branch in self.env.company._accessible_branches()):
            warnings['account_reports.tax_report_warning_tax_id_selected_companies'] = {'alert_type': 'warning'}

        # Check whether there are unposted entries for the selected period and partner or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            domain = osv.expression.AND([
                self.env['account.move']._check_company_domain(report_company_ids),
                [('state', '=', 'draft')],
                [('date', '<=', options['date']['date_to'])],
            ])
            if options.get('partner_ids'):
                domain = osv.expression.AND([
                    domain,
                    osv.expression.OR([
                        [('partner_id', 'in', options['partner_ids'])],
                        [('partner_shipping_id', 'in', options['partner_ids'])],
                        [('commercial_partner_id', 'in', options['partner_ids'])],
                    ])
                ])
            if self.env['account.move'].search_count(domain, limit=1):
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
                to_insert = self._expand_unfoldable_line(
                    line_dict['expand_function'], line_dict['id'], groupby, options, progress, 0, line_dict.get('horizontal_split_side'),
                    unfold_all_batch_data=custom_unfold_all_batch_data,
                )
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
        groupby = line._get_groupby(options)
        has_children = (groupby and any(col['has_sublines'] for col in columns)) or bool(line.children_ids)

        rslt = {
            'id': line_id,
            'name': line.name,
            'groupby': groupby,
            'unfoldable': line.foldable and has_children,
            'unfolded': (not line.foldable and (groupby or has_children)) or line_id in options['unfolded_lines'] or has_children and options['unfold_all'],
            'columns': columns,
            'level': line.hierarchy_level,
            'page_break': line.print_on_new_page,
            'action_id': line.action_id.id,
            'expand_function': groupby and '_report_expand_unfoldable_line_with_groupby' or None,
        }

        if line.horizontal_split_side:
            rslt['horizontal_split_side'] = line.horizontal_split_side

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
                    {'formula': expression.formula, 'subformula': expression.subformula, 'value': self.format_value(options, column_group_totals[expression]['value'], figure_type)}
                ))

            # Sort results so that they can be rendered nicely in the UI
            for details in expressions_detail.values():
                details.sort(key=lambda x: x[0])
            sorted_expressions_detail = sorted(expressions_detail.items(), key=lambda x: x[0])

            if sorted_expressions_detail:
                try:
                    rslt['debug_popup_data'] = json.dumps({'expressions_detail': sorted_expressions_detail})
                except TypeError:
                    raise UserError(_(
                        'Invalid subformula in expression "%(expression)s" of line "%(line)s": %(subformula)s',
                        expression=expression.label,
                        line=expression.report_line_id.name,
                        subformula=expression.subformula,
                    ))
        return rslt

    @api.model
    def _build_static_line_columns(self, line, options, all_column_groups_expression_totals, groupby_model=None):
        line_expressions_map = {expr.label: expr for expr in line.expression_ids}
        columns = []
        for column_data in options['columns']:
            col_group_key = column_data['column_group_key']
            current_group_expression_totals = all_column_groups_expression_totals[col_group_key]
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
                info_popup_data['carryover'] = self._format_value(options, carryover_value, 'monetary')

                carryover_expression = line_expressions_map[carryover_expr_label]
                if carryover_expression.carryover_target:
                    info_popup_data['carryover_target'] = carryover_expression._get_carryover_target_expression(options).report_line_name
                # If it's not set, it means the carryover needs to target the same expression

            applied_carryover_value = target_line_res_dict.get('_applied_carryover_%s' % column_expr_label, {}).get('value', 0)
            if self.env.company.currency_id.compare_amounts(0, applied_carryover_value) != 0:
                info_popup_data['applied_carryover'] = self._format_value(options, applied_carryover_value, 'monetary')
                info_popup_data['allow_carryover_audit'] = self.env.user.has_group('base.group_no_one')
                info_popup_data['expression_id'] = line_expressions_map['_applied_carryover_%s' % column_expr_label]['id']
                info_popup_data['column_group_key'] = col_group_key

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
                        'column_group_key': col_group_key,
                        'target_expression_id': column_expression.id,
                        'rounding': rounding,
                        'figure_type': figure_type,
                        'column_value': column_value,
                    }

                formatter_params['digits'] = rounding

            # Handle editable financial budgets
            editable_budget = groupby_model == 'account.account' and options['column_groups'][col_group_key]['forced_options'].get('compute_budget')
            if editable_budget and self.env.user.has_group('account.group_account_manager'):
                edit_popup_data = {
                    'column_group_key': col_group_key,
                    'target_expression_id': column_expression.id,
                    'rounding': self.env.company.currency_id.decimal_places,
                    'figure_type': 'monetary',
                    'column_value': column_value,
                }

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

        format_params = {}
        if figure_type == 'monetary' and currency:
            format_params['currency_id'] = currency.id
        elif figure_type in ('float', 'percentage'):
            format_params['digits'] = digits

        col_group_key = col_data.get('column_group_key')

        return {
            'auditable': col_value is not None
                         and column_expression.auditable
                         and not options['column_groups'][col_group_key]['forced_options'].get('compute_budget'),
            'blank_if_zero': blank_if_zero,
            'column_group_key': col_group_key,
            'currency': currency,
            'currency_symbol': (currency or self.env.company.currency_id).symbol if options.get('multi_currency') else None,
            'digits': digits,
            'expression_label': col_data.get('expression_label'),
            'figure_type': figure_type,
            'green_on_positive': column_expression.green_on_positive,
            'has_sublines': has_sublines,
            'is_zero': col_value is None or (
                isinstance(col_value, (int, float))
                and figure_type in NUMBER_FIGURE_TYPES
                and self._is_value_zero(col_value, figure_type, format_params)
            ),
            'no_format': col_value,
            'format_params': format_params,
            'report_line_id': report_line_id,
            'sortable': col_data.get('sortable', False),
            'comparison_mode': col_data.get('comparison_mode'),
        }

    def _inject_account_names_for_consolidation(self, lines):
        """ When grouping by account_code, in order to make the consolidation clearer, we add the account name in the context
            of the current company next to the account_code.
        """
        account_codes = []
        for line in lines:
            markup = self._get_markup(line['id'])
            if isinstance(markup, dict) and markup.get('groupby') == 'account_code':
                account_codes.append(line['name'])
        if not account_codes:
            return

        account_code_to_account_name_dict = {account.code: account.name for account in self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self.env.company),
            ('code', 'in', account_codes),
        ])}
        for line in lines:
            markup = self._get_markup(line['id'])
            if isinstance(markup, dict) and markup.get('groupby') == 'account_code':
                account_code = line['name']
                account_name = account_code_to_account_name_dict.get(account_code)
                if account_code and account_name:
                    line['name'] = f'{account_code} {account_name}'

    def _get_dynamic_lines(self, options, all_column_groups_expression_totals, warnings=None):
        if self.custom_handler_model_id:
            rslt = self.env[self.custom_handler_model_name]._dynamic_lines_generator(self, options, all_column_groups_expression_totals, warnings=warnings)
            self._apply_integer_rounding_to_dynamic_lines(options, (line for _sequence, line in rslt))
            return rslt
        return []

    def _apply_integer_rounding_to_dynamic_lines(self, options, dynamic_lines):
        if options.get('integer_rounding_enabled'):
            for line in dynamic_lines:
                for column_dict in line.get('columns', []):
                    if 'name' not in column_dict and column_dict.get('figure_type') == 'monetary' and column_dict.get('no_format'):
                        # If 'name' is already in it, no need to round the amount ; it is forced by the custom report already
                        column_dict['no_format'] = float_round(
                            column_dict['no_format'],
                            precision_digits=0,
                            rounding_method=options['integer_rounding'],
                        )

    def _compute_expression_totals_for_each_column_group(self, expressions, options,
        groupby_to_expand=None, forced_all_column_groups_expression_totals=None, col_groups_restrict=None, offset=0, limit=None, include_default_vals=False, warnings=None):
        """
            Main computation function for static lines.

            :param expressions: The account.report.expression objects to evaluate.

            :param options: The options dict for this report, obtained from.get_options({}).

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

            :param col_groups_restrict: List of column group keys of the groups to compute. Other column groups will be ignored, and will
                                        not be added to the result of this function (they can still be provided beforehand through
                                        forced_all_column_groups_expression_totals). If not provided, all colum groups will be computed.

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

            if not col_groups_restrict or group_key in col_groups_restrict:
                current_group_expression_totals = self._compute_expression_totals_for_single_column_group(
                    group_options,
                    grouped_formulas,
                    forced_column_group_expression_totals=forced_column_group_totals,
                    offset=offset,
                    limit=limit,
                    warnings=warnings,
                )
            else:
                current_group_expression_totals = forced_column_group_totals

            all_column_groups_expression_totals[group_key] = current_group_expression_totals

        return all_column_groups_expression_totals

    def _standardize_date_scope_for_date_range(self, date_scope):
        """ Depending on the fact the report accepts date ranges or not, different date scopes might mean the same thing.
        This function is used so that, in those cases, only one of these date_scopes' values is used, to avoid useless creation
        of multiple computation batches and improve the overall performance as much as possible.
        """
        if not self.filter_date_range and date_scope == 'strict_range':
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
                    subformula_error_format = _(
                        'Invalid subformula in expression "%(expression)s" of line "%(line)s": %(subformula)s',
                        expression=expression.label,
                        line=expression.report_line_id.name,
                        subformula=expression.subformula,
                    )
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
                            if col['figure_type'] == 'monetary'
                        )

                        if (in_monetary_column and not expression.figure_type) or expression.figure_type == 'monetary':
                            method = column_group_options['integer_rounding']
                            if isinstance(expression_value, list):
                                expression_value = [(key, float_round(value, precision_digits=0, rounding_method=method) if value is not None else value) for key, value in expression_value]
                            else:
                                expression_value = float_round(expression_value, precision_digits=0, rounding_method=method)

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
                                "Expression labelled '%(label)s' of line '%(line)s' is being overwritten when computing the current report. "
                                "Make sure the cross-report aggregations of this report only reference terms belonging to other reports.",
                                label=expression.label, line=expression.report_line_id.name
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
                            raise UserError(_("Could not expand term %(term)s while evaluating formula %(unexpanded_formula)s", term=term, unexpanded_formula=unexpanded_formula))

                    formula = re.sub(term_replacement_regex % re.escape(term), f'({expanded_term})', formula)

                to_treat.append((formula, unexpanded_formula, forced_date_scope))

            else:
                # The formula contains only digits and operators; it can be evaluated
                try:
                    formula_result = expr_eval(formula)
                except ZeroDivisionError:
                    for expr in formulas_dict[unexpanded_formula, forced_date_scope]:
                        if expr.subformula != "ignore_zero_division":
                            raise UserError(_(
                                "Division by zero occurred while evaluating Expression: %(line_name)s > %(label)s.",
                                line_name=expr.report_line_name,
                                label=expr.label,
                            ))
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

        if subformula not in {'cross_report', 'ignore_zero_division'}:
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

        query = self._get_report_query(options, date_scope)
        groupby_sql = self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, query) if current_groupby else None
        tail_query = self._get_engine_query_tail(offset, limit)
        lang = get_lang(self.env, self.env.user.lang).code
        acc_tag_name = self.with_context(lang='en_US').env['account.account.tag']._field_to_sql('acc_tag', 'name')
        sql = SQL(
            """
            SELECT
                SUBSTRING(%(acc_tag_name)s, 2, LENGTH(%(acc_tag_name)s) - 1) AS formula,
                SUM(%(balance_select)s
                    * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                    * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                ) AS balance,
                COUNT(account_move_line.id) AS aml_count
                %(select_groupby_sql)s

            FROM %(table_references)s

            JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
            JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
                AND acc_tag.id IN %(tag_ids)s
            %(currency_table_join)s

            WHERE %(search_condition)s

            GROUP BY %(groupby_clause)s

            ORDER BY %(groupby_clause)s

            %(tail_query)s
            """,
            acc_tag_name=acc_tag_name,
            select_groupby_sql=SQL(', %s AS grouping_key', groupby_sql) if groupby_sql else SQL(),
            table_references=query.from_clause,
            tag_ids=tuple(tags.ids),
            balance_select=self._currency_table_apply_rate(SQL("account_move_line.balance")),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            groupby_clause=SQL(
                "SUBSTRING(%(acc_tag_name)s, 2, LENGTH(%(acc_tag_name)s) - 1)%(groupby_sql)s",
                acc_tag_name=acc_tag_name,
                groupby_sql=SQL(', %s', groupby_sql) if groupby_sql else SQL(),
            ),
            tail_query=tail_query,
        )

        self._cr.execute(sql)

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

        batchable_domains_data = {}  # In the form {(model name, aml_field):  [(domain, expressions)]}
        non_batchable_domains_data = []  # In the form [(domain, expressions)]
        for formula, expressions in formulas_dict.items():
            try:
                domain = literal_eval(formula)
            except (ValueError, SyntaxError):
                raise UserError(_(
                    'Invalid domain formula in expression "%(expression)s" of line "%(line)s": %(formula)s',
                    expression=expressions[0].label,
                    line=expressions[0].report_line_id.name,
                    formula=formula,
                ))

            if offset or limit or any(expr.subformula == 'count_rows' for expr in expressions):
                # count_rows cannot be computed generically with batching (because of the additional groupby we inject in the batch computation)
                non_batchable_domains_data.append((domain, formula, expressions))
                continue

            aml_root_fields = set()
            traversing_model_domain = []
            for term in domain:
                match term:
                    case (aml_field_expr, operator, value):
                        aml_field, _dot, model_field_expr = aml_field_expr.partition('.')
                        aml_root_fields.add(aml_field)
                        traversing_model_domain.append((model_field_expr or 'id', operator, value))
                    case str():
                        traversing_model_domain.append(term)

            if len(aml_root_fields) == 1:
                aml_field = self.env['account.move.line']._fields[next(iter(aml_root_fields))]
                if aml_field.type == 'many2one':
                    batchable_domains_data.setdefault((aml_field.comodel_name, aml_field.name), []).append((traversing_model_domain, formula, expressions))
                else:
                    non_batchable_domains_data.append((domain, formula, expressions))
            else:
                non_batchable_domains_data.append((domain, formula, expressions))

        rslt = {}
        for (batch_model, batch_aml_field), batch_domains in chain(batchable_domains_data.items(), (((None, None), [data]) for data in non_batchable_domains_data)):
            aml_domain = batch_domains[0][0] if not batch_model else None  # batch_domains contains only one element if there is not batch_model/batch_aml_field
            query = self._get_report_query(options, date_scope, domain=aml_domain)

            groupby_sql = self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, query) if current_groupby else None
            batch_groupby_sql = self.env['account.move.line']._field_to_sql('account_move_line', batch_aml_field, query) if batch_aml_field else None

            select_count_field = self.env['account.move.line']._field_to_sql('account_move_line', next_groupby.split(',')[0] if next_groupby else 'id', query)

            tail_query = self._get_engine_query_tail(offset, limit)
            query = SQL(
                """
                SELECT
                    COALESCE(SUM(%(balance_select)s), 0.0) AS sum,
                    COUNT(DISTINCT %(select_count_field)s) AS count_rows
                    %(select_groupby_sql)s
                    %(select_batch_groupby_sql)s
                FROM %(table_references)s
                %(currency_table_join)s
                WHERE %(search_condition)s
                %(groupby_sql)s
                %(order_by_sql)s
                %(tail_query)s
                """,
                select_count_field=select_count_field,
                select_groupby_sql=SQL(', %s AS grouping_key', groupby_sql) if groupby_sql else SQL(),
                select_batch_groupby_sql=SQL(', %s AS batch_grouping_key', batch_groupby_sql) if batch_groupby_sql else SQL(),
                table_references=query.from_clause,
                balance_select=self._currency_table_apply_rate(SQL("account_move_line.balance")),
                currency_table_join=self._currency_table_aml_join(options),
                search_condition=query.where_clause,
                groupby_sql=SQL('GROUP BY %s', SQL(',').join(groupby_term for groupby_term in (groupby_sql, batch_groupby_sql) if groupby_term)) if groupby_sql or batch_groupby_sql else SQL(),
                order_by_sql=SQL(' ORDER BY %s', groupby_sql) if groupby_sql else SQL(),
                tail_query=tail_query,
            )

            self._cr.execute(query)
            all_query_res = self._cr.dictfetchall()

            results_by_batch_grouping_key = {}
            if batch_model:
                for query_res in all_query_res:
                    results_by_batch_grouping_key.setdefault(query_res['batch_grouping_key'], []).append(query_res)

            for domain, formula, expressions in batch_domains:
                formula_rslt = []
                total_sum = 0
                totals_by_grouping_key = {}

                batch_included_ids = self.env[batch_model].search(domain).ids if batch_model else [None]
                for batch_included_id in batch_included_ids:
                    batch_res = results_by_batch_grouping_key.get(batch_included_id, []) if batch_included_id is not None else all_query_res

                    for query_res in batch_res:
                        totals = totals_by_grouping_key.setdefault(query_res.get('grouping_key'), {
                            'sum': 0,
                            'sum_if_pos': 0,
                            'sum_if_neg': 0,
                            'count_rows': 0,
                            'has_sublines': False,
                        })

                        res_sum = query_res['sum']
                        totals['sum'] += res_sum
                        totals['count_rows'] += query_res['count_rows']
                        totals['has_sublines'] = totals['has_sublines'] or bool(query_res['count_rows'])

                        total_sum += res_sum

                for grouping_key, totals in totals_by_grouping_key.items():
                    formula_rslt.append((grouping_key, totals))

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
                                rslt[formula, policy_expressions] = _format_result_depending_on_groupby(formula_rslt_with_sign)
                            else:
                                rslt[formula, policy_expressions] = _format_result_depending_on_groupby([])

                if expressions_by_sign_policy['no_sign_check']:
                    rslt[formula, expressions_by_sign_policy['no_sign_check']] = _format_result_depending_on_groupby(formula_rslt)

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
                        raise UserError(_("Invalid token '%(token)s' in account_codes formula '%(formula)s'", token=token, formula=formula))

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
        all_prefixes_queries: list[SQL] = []
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

            prefix_query = self.env['account.account']._where_calc(account_domain)
            all_prefixes_queries.append(prefix_query.select(
                SQL("%s AS prefix", [prefix, *excluded_prefixes]),
                SQL("account_account.id AS account_id"),
            ))

        # Build a map to associate each account with the prefixes it matches
        accounts_prefix_map = defaultdict(list)
        for prefix, account_id in self.env.execute_query(SQL(' UNION ALL ').join(all_prefixes_queries)):
            accounts_prefix_map[account_id].append(tuple(prefix))

        # Run main query
        query = self._get_report_query(options, date_scope)

        current_groupby_aml_sql = self.env['account.move.line']._field_to_sql('account_move_line', current_groupby, query) if current_groupby else None
        tail_query = self._get_engine_query_tail(offset, limit)
        if current_groupby_aml_sql and tail_query:
            tail_query_additional_groupby_where_sql = SQL(
                """
                AND %(current_groupby_aml_sql)s IN (
                    SELECT DISTINCT %(current_groupby_aml_sql)s
                    FROM account_move_line
                    WHERE %(search_condition)s
                    ORDER BY %(current_groupby_aml_sql)s
                    %(tail_query)s
                )
                """,
                current_groupby_aml_sql=current_groupby_aml_sql,
                search_condition=query.where_clause,
                tail_query=tail_query,
            )
        else:
            tail_query_additional_groupby_where_sql = SQL()

        extra_groupby_sql =  SQL(", %s", current_groupby_aml_sql) if current_groupby_aml_sql else SQL()
        extra_select_sql = SQL(", %s AS grouping_key", current_groupby_aml_sql) if current_groupby_aml_sql else SQL()

        query = SQL(
            """
            SELECT
                account_move_line.account_id AS account_id,
                SUM(%(balance_select)s) AS sum,
                COUNT(account_move_line.id) AS aml_count
                %(extra_select_sql)s
            FROM %(table_references)s
            %(currency_table_join)s
            WHERE %(search_condition)s
            %(tail_query_additional_groupby_where_sql)s
            GROUP BY account_move_line.account_id%(extra_groupby_sql)s
            %(order_by_sql)s
            %(tail_query)s
            """,
            extra_select_sql=extra_select_sql,
            table_references=query.from_clause,
            balance_select=self._currency_table_apply_rate(SQL("account_move_line.balance")),
            currency_table_join=self._currency_table_aml_join(options),
            search_condition=query.where_clause,
            extra_groupby_sql=extra_groupby_sql,
            tail_query_additional_groupby_where_sql=tail_query_additional_groupby_where_sql,
            order_by_sql=SQL('ORDER BY %s', current_groupby_aml_sql) if current_groupby_aml_sql else SQL(),
            tail_query=tail_query if not tail_query_additional_groupby_where_sql else SQL(),
        )
        self._cr.execute(query)

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
            rslt_groups_by_grouping_keys = {}
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
                            if not current_groupby:
                                rslt_destination['result'] += rslt_group['result']
                                rslt_destination['has_sublines'] = rslt_destination['has_sublines'] or rslt_group['has_sublines']
                            elif group_key in rslt_groups_by_grouping_keys:
                                # Will happen if the same grouping key is used on move lines with different accounts.
                                # This comes from the GROUPBY in the SQL query, which uses both grouping key and account.
                                # When this happens, we want to aggregate the results of each grouping key, to avoid duplicates in the end result.
                                already_treated_rslt_group = rslt_groups_by_grouping_keys[group_key]
                                already_treated_rslt_group['has_sublines'] = already_treated_rslt_group['has_sublines'] or rslt_group['has_sublines']
                                already_treated_rslt_group['result'] += rslt_group['result']
                            else:
                                rslt_groups_by_grouping_keys[group_key] = rslt_group
                                rslt_destination.append((group_key, rslt_group))

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
        date_from, date_to = self._get_date_bounds_info(options, date_scope)
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
        where_clause = self.env['account.report.external.value']._where_calc(external_value_domain).where_clause

        # We have to execute two separate queries, one for text values and one for numeric values
        num_queries = []
        string_queries = []
        monetary_queries = []
        for formula, expressions in formulas_dict.items():
            query_end = SQL()
            if formula == 'most_recent':
                query_end = SQL(
                    """
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                    """,
                )
            string_query = """
                    SELECT %(expression_id)s, text_value
                    FROM account_report_external_value
                    WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
                """
            monetary_query = """
                SELECT
                    %(expression_id)s,
                    COALESCE(SUM(COALESCE(%(balance_select)s, 0)), 0)
                FROM account_report_external_value
                    %(currency_table_join)s
                WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
                %(query_end)s
            """
            num_query = """
                    SELECT %(expression_id)s, SUM(COALESCE(value, 0))
                      FROM account_report_external_value
                     WHERE %(where_clause)s AND target_report_expression_id = %(expression_id)s
               %(query_end)s
            """

            for expression in expressions:
                if expression.figure_type == "string":
                    string_queries.append(SQL(
                        string_query,
                        expression_id=expression.id,
                        where_clause=where_clause,
                    ))
                elif expression.figure_type == "monetary":
                    monetary_queries.append(SQL(
                        monetary_query,
                        expression_id=expression.id,
                        balance_select=self._currency_table_apply_rate(SQL("CAST(value AS numeric)")),
                        currency_table_join=SQL(
                            """
                                JOIN %(currency_table)s
                                ON account_currency_table.company_id = account_report_external_value.company_id
                                AND account_currency_table.rate_type = 'current'
                            """,
                            currency_table=self._get_currency_table(options),
                        ),
                        where_clause=where_clause,
                        query_end=query_end,
                    ))
                else:
                    num_queries.append(SQL(
                        num_query,
                        expression_id=expression.id,
                        where_clause=where_clause,
                        query_end=query_end,
                    ))

        # Convert to dict to have expression ids as keys
        query_results_dict = {}
        for query_list in (num_queries, string_queries, monetary_queries):
            if query_list:
                query_results = self.env.execute_query(SQL(' UNION ALL ').join(SQL("(%s)", query) for query in query_list))
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

    def _get_engine_query_tail(self, offset, limit) -> SQL:
        """ Helper to generate the OFFSET, LIMIT and ORDER conditions of formula engines' queries.
        """
        query_tail = SQL()

        if offset:
            query_tail = SQL("%s OFFSET %s", query_tail, offset)

        if limit:
            query_tail = SQL("%s LIMIT %s", query_tail, limit)

        return query_tail

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
        if date_from >= date_to:
            # This can happen when setting the lock date back in the past
            return

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
                    'name': label or _("Carryover from %(date_from)s to %(date_to)s", date_from=format_date(self.env, date_from), date_to=format_date(self.env, date_to)),
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
            date_from, date_to = self._get_date_bounds_info(column_group_options, expression.date_scope)
            external_values_domain = [('target_report_expression_id', '=', expression.id), ('date', '<=', date_to)]
            if date_from:
                external_values_domain.append(('date', '>=', date_from))

            if expression.formula == 'most_recent':
                query = self.env['account.report.external.value']._where_calc(external_values_domain)
                rows = self.env.execute_query(SQL("""
                    SELECT ARRAY_AGG(id)
                    FROM %s
                    WHERE %s
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """, query.from_clause, query.where_clause or SQL("TRUE")))
                if rows:
                    external_values_domain = [('id', 'in', rows[0][0])]

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
        column = next((col for col in report_line.report_id.column_ids if col.expression_label == expression_label), self.env['account.report.column'])
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
        for markup, dummy, grouping_key in parsed_line_dict_id:
            if isinstance(markup, dict) and 'groupby' in markup:
                groupby_field_name = markup['groupby']
                custom_handler_model = self._get_custom_handler_model()
                if custom_handler_model and (custom_groupby_data := self.env[custom_handler_model]._get_custom_groupby_map().get(groupby_field_name)):
                    groupby_domain += custom_groupby_data['domain_builder'](grouping_key)
                else:
                    groupby_domain.append((groupby_field_name, '=', grouping_key))

        return groupby_domain

    def _get_expression_audit_aml_domain(self, expression_to_audit, options):
        """ Returns the domain used to audit a single provided expression.

        'account_codes' engine's D and C formulas can't be handled by a domain: we make the choice to display
        everything for them (so, audit shows all the lines that are considered by the formula). To avoid confusion from the user
        when auditing such lines, a default group by account can be used in the list view.
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

        if options.get('selected_journal_groups'):
            ctx.update({
                'search_default_journal_group_id': [options['selected_journal_groups']['id']],
            })

        journal_type = params.get('journal_type')
        if journal_type or options.get('selected_journal_groups') and options['selected_journal_groups']['journal_types']:
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
                'credit': {
                    'filter': 'search_default_credit',
                    'view_id': self.env.ref('account.view_move_line_tree').id
                },
            }
            if options.get('selected_journal_groups'):
                ctx_to_update = {}
                for journal_type in options['selected_journal_groups']['journal_types']:
                    ctx_to_update[type_to_view_param[journal_type]['filter']] = 1
                ctx.update(ctx_to_update)
            else:
                ctx.update({
                    type_to_view_param[journal_type]['filter']: 1,
                })
            view_id = type_to_view_param[journal_type]['view_id']

        action_domain = [('display_type', 'not in', ('line_section', 'line_note'))]

        if record_model == 'account.group':
            if record_id:
                query = SQL("""
                    SELECT a.id
                      FROM account_account a
                      JOIN account_group ag
                           ON ag.code_prefix_start <= LEFT(a.code_store->>'%(root_company_id)s', char_length(ag.code_prefix_start))
                              AND ag.code_prefix_end >= LEFT(a.code_store->>'%(root_company_id)s', char_length(ag.code_prefix_end))
                              AND ag.company_id = %(root_company_id)s
                     WHERE ag.id = %(record_id)s
                           AND a.code_store ? '%(root_company_id)s'
                """,
                    root_company_id=self.env.company.root_id.id,
                    record_id=record_id
                )
            else:
                query = SQL("""
                    WITH relevant_accounts AS (
                        SELECT id, code_store->>%(root_company_id)s AS code
                          FROM account_account
                         WHERE code_store ? %(root_company_id)s
                    )
                  SELECT a.id
                    FROM relevant_accounts a
                   WHERE NOT EXISTS (
                        SELECT 1
                          FROM account_group ag
                         WHERE ag.company_id = %(root_company_id)s
                               AND LEFT(a.code, char_length(ag.code_prefix_start)) >= ag.code_prefix_start
                               AND LEFT(a.code, char_length(ag.code_prefix_end))   <= ag.code_prefix_end
                    )
                """, root_company_id=str(self.env.company.root_id.id))

            self.env.cr.execute(query)
            account_ids = [account[0] for account in self.env.cr.fetchall()]
            action_domain += [('account_id', 'in', account_ids)]
        elif record_id is None:
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
                'product.product': 'search_default_product_id',
                'product.category': 'search_default_product_category_id',
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

            if options.get('journals') and not ctx['search_default_journal_id']:
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if len(selected_journals) == 1:
                    ctx['search_default_journal_id'] = selected_journals
                elif len(selected_journals) > 1:
                    ctx['search_default_journal_ids'] = True
                    ctx['journal_ids'] = selected_journals

            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                ctx.update({
                    'search_default_analytic_accounts': 1,
                    'analytic_ids': analytic_ids,
                })

        return {
            'name': self._get_action_name(params, record_model, record_id),
            'view_mode': 'list,pivot,graph,kanban',
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
            'views': [(False, 'list'), (False, 'form')],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            }
        }

    def action_modify_manual_value(self, line_id, options, column_group_key, new_value_str, target_expression_id, rounding, json_friendly_column_group_totals):
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

        target_column_group_options = self._get_column_group_options(options, column_group_key)
        self._init_currency_table(target_column_group_options)

        if target_column_group_options.get('compute_budget'):
            expressions_to_recompute = self.env['account.report.expression'].browse(target_expression_id) \
                                       + self.line_ids.expression_ids.filtered(lambda x: x.engine == 'aggregation')
            self._action_modify_manual_budget_value(line_id, target_column_group_options, new_value_str, target_expression_id, rounding)
        else:
            expressions_to_recompute = self.line_ids.expression_ids.filtered(lambda x: x.engine in ('external', 'aggregation'))
            self._action_modify_manual_external_value(target_column_group_options, new_value_str, target_expression_id, rounding)

        # We recompute values for each column group, not only the one we modified a value in; this is important in case some date_scope is used to
        # retrieve the manual value from a previous period.

        all_column_groups_expression_totals = self._convert_json_friendly_column_group_totals(
            json_friendly_column_group_totals,
            expressions_to_exclude=expressions_to_recompute,
        )

        recomputed_expression_totals = self._compute_expression_totals_for_each_column_group(
            expressions_to_recompute, options, forced_all_column_groups_expression_totals=all_column_groups_expression_totals)

        return {
            'lines': self._get_lines(options, all_column_groups_expression_totals=recomputed_expression_totals),
            'column_groups_totals': self._get_json_friendly_column_group_totals(recomputed_expression_totals),
        }

    def _convert_json_friendly_column_group_totals(self, json_friendly_column_group_totals, expressions_to_exclude=None, col_groups_to_exclude=None):
        """ json_friendly_column_group_totals contains ids instead of expressions (because it comes from js) ; this function is used
        to convert them back to records.
        """
        all_column_groups_expression_totals = {}
        for column_group_key, expression_totals in json_friendly_column_group_totals.items():
            if col_groups_to_exclude and column_group_key in col_groups_to_exclude:
                continue

            all_column_groups_expression_totals[column_group_key] = {}
            for expr_id, expr_totals in expression_totals.items():
                expression = self.env['account.report.expression'].browse(int(expr_id))  # Should already be in cache, so acceptable
                if not expressions_to_exclude or expression not in expressions_to_exclude:
                    all_column_groups_expression_totals[column_group_key][expression] = expr_totals

        return all_column_groups_expression_totals

    def _action_modify_manual_external_value(self, target_column_group_options, new_value_str, target_expression_id, rounding):
        """ Edit a manual value from the report, updating or creating the corresponding account.report.external.value object.

        :param target_column_group_options: The options dict of the column group where the modification happened.

        :param column_group_key: The string identifying the column group into which the change as manual value needs to be done.

        :param new_value_str: The new value to be set, as a string.

        :param rounding: The number of decimal digits to round with.

        """
        if len(target_column_group_options['companies']) > 1:
            raise UserError(_("Editing a manual report line is not allowed when multiple companies are selected."))

        if target_column_group_options['fiscal_position'] == 'all' and target_column_group_options['available_vat_fiscal_positions']:
            raise UserError(_("Editing a manual report line is not allowed in multivat setup when displaying data from all fiscal positions."))

        # Create the manual value
        target_expression = self.env['account.report.expression'].browse(target_expression_id)
        date_from, date_to = self._get_date_bounds_info(target_column_group_options, target_expression.date_scope)
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

    def _action_modify_manual_budget_value(self, line_id, target_column_group_options, new_value_str, target_expression_id, rounding):
        target_expression = self.env['account.report.expression'].browse(target_expression_id)

        if not new_value_str and target_expression.figure_type != 'string':
            new_value_str = '0'

        try:
            value_to_set = float_round(float(new_value_str), precision_digits=rounding)
        except ValueError:
            raise UserError(_("%s is not a numeric value", new_value_str))

        model, account_id = self._get_model_info_from_id(line_id)
        if model != 'account.account':
            raise UserError(_("Budget items can only be edited from account lines."))

        # Depending on the expression's formula, the balance of the account could be multiplied by -1
        # within the report. We need to apply the same multiplier on the budget item we create.
        if target_expression.engine == 'domain' and target_expression.subformula.startswith('-'):
            value_to_set *= -1
        elif target_expression.engine == 'account_codes':
            account = self.env['account.account'].browse(account_id)

            # Search for the sign to apply to this account
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(target_expression.formula.replace(' ', '')):
                if not token:
                    continue

                token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                multiplicator = -1 if token_match['sign'] == '-' else 1
                prefix = token_match['prefix']

                tag_match = ACCOUNT_CODES_ENGINE_TAG_ID_PREFIX_REGEX.match(prefix)
                if tag_match:
                    if tag_match['ref']:
                        tag = self.env.ref(tag_match['ref'])
                    else:
                        tag = self.env['account.account.tag'].browse(tag_match['id'])

                    account_matches = tag in account.tag_ids
                else:
                    account_matches = account.code.startswith(prefix)

                if account_matches:
                    value_to_set *= multiplicator
                    break

        self.env['account.report.budget'].browse(target_column_group_options['compute_budget'])._create_or_update_budget_items(
            value_to_set,
            account_id,
            rounding,
            target_column_group_options['date']['date_from'],
            target_column_group_options['date']['date_to'],
        )

    def action_display_inactive_sections(self, options):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Enable Sections"),
            'view_mode': 'list,form',
            'res_model': 'account.report',
            'domain': [('section_main_report_ids', 'in', options['sections_source_id']), ('active', '=', False)],
            'views': [(False, 'list'), (False, 'form')],
            'context': {
                'list_view_ref': 'account_reports.account_report_add_sections_tree',
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
        - All lines are sorted except:
            - lines having the 'total' class
            - static lines (lines with model 'account.report.line')
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
            if column_index is False:
                return 0
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
            a_model = self._get_model_info_from_id(a_line_dict['id'])[0]
            b_model = self._get_model_info_from_id(b_line_dict['id'])[0]

            # static lines are not sorted
            if a_model == b_model == 'account.report.line':
                return 0

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

        column_index = False
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

    def _get_annotations_domain_date_from(self, options):
        if options['date']['filter'] in {'today', 'custom'} and options['date']['mode'] == 'single':
            options_company_ids = [company['id'] for company in options['companies']]
            root_companies_ids = self.env['res.company'].browse(options_company_ids).root_id.ids
            fiscal_year = self.env['account.fiscal.year'].search_fetch([
                ('company_id', 'in', root_companies_ids),
                ('date_from', '<=', options['date']['date_to']),
                ('date_to', '>=', options['date']['date_to']),
            ], limit=1, field_names=['date_from'])
            if fiscal_year:
                return datetime.datetime.combine(fiscal_year.date_from, datetime.time.min)

            period_date_from, _ = date_utils.get_fiscal_year(
                datetime.datetime.strptime(options['date']['date_to'], '%Y-%m-%d'),
                day=self.env.company.fiscalyear_last_day,
                month=int(self.env.company.fiscalyear_last_month)
            )
            return period_date_from

        date_from = datetime.datetime.strptime(options['date']['date_from'], '%Y-%m-%d')
        if options['date']['period_type'] == "fiscalyear":
            period_date_from, _ = date_utils.get_fiscal_year(date_from)
        elif options['date']['period_type'] in ["year", "quarter", "month", "week", "day", "hour"]:
            period_date_from = date_utils.start_of(date_from, options['date']['period_type'])
        else:
            period_date_from = date_from
        return period_date_from

    def _adjust_date_for_joined_comparison(self, options, period_date_from):
        comparison_filter = options.get('comparison', {}).get('filter')
        if comparison_filter == 'previous_period':
            comparison_date_from = datetime.datetime.strptime(options['comparison'].get('periods', [{}])[-1].get('date_from'), '%Y-%m-%d')
            return min(period_date_from, comparison_date_from)
        return period_date_from

    def _adjust_domain_for_unjoined_comparison(self, options, dates_domain):
        comparison_filter = options.get('comparison', {}).get('filter')
        if comparison_filter and comparison_filter not in {'no_comparison', 'previous_period'}:
            unlinked_comparison_periods_domains_list = [
                ['&', ('date', '>=', period['date_from']), ('date', '<=', period['date_to'])]
                for period in options['comparison']['periods']
            ]
            dates_domain = osv.expression.OR([dates_domain, *unlinked_comparison_periods_domains_list])

        return dates_domain

    def _build_annotations_domain(self, options):
        domain = [('report_id', '=', options['report_id'])]
        if options.get('date'):
            period_date_from = self._get_annotations_domain_date_from(options)
            period_date_from = self._adjust_date_for_joined_comparison(options, period_date_from)
            dates_domain = osv.expression.AND([
                [('date', '>=', period_date_from)],
                [('date', '<=', options['date']['date_to'])],
            ])
            dates_domain = self._adjust_domain_for_unjoined_comparison(options, dates_domain)

            domain = osv.expression.AND([
                domain,
                osv.expression.OR([
                    [('date', '=', False)],
                    dates_domain,
                ]),
            ])

        fiscal_position_option = options.get('fiscal_position')
        if isinstance(fiscal_position_option, int):
            domain = osv.expression.AND([domain, [('fiscal_position_id', '=', fiscal_position_option)]])
        elif fiscal_position_option == 'domestic':
            domain = osv.expression.AND([domain, [('fiscal_position_id', '=', False)]])
        return domain

    def get_annotations(self, options):
        """
        This method handles which annotations have to be displayed on the report.
        This decision is based on the different dates and mode of display of those dates in the report.

        param options: dict of options used to generate the report
        return: dict of lists containing for each annotated line_id of the report the list of annotations linked to it
        """
        self.ensure_one()
        annotations_by_line = defaultdict(list)
        annotations = self.env['account.report.annotation'].search_read(self._build_annotations_domain(options))
        for annotation in annotations:
            line_id_without_tax_grouping = self.env['account.report.annotation']._remove_tax_grouping_from_line_id(annotation['line_id'])
            annotation['create_date'] = annotation['create_date'].date()
            annotations_by_line[line_id_without_tax_grouping].append(annotation)
        return annotations_by_line

    def get_report_information(self, options):
        """
        return a dictionary of information that will be consumed by the AccountReport component.
        """
        self.ensure_one()
        self.env.flush_all()

        warnings = {}
        self._init_currency_table(options)
        all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(self.line_ids.expression_ids, options, warnings=warnings)

        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = self._get_json_friendly_column_group_totals(all_column_groups_expression_totals)

        if self.custom_handler_model_name:
            custom_display_config = self.env[self.custom_handler_model_name]._get_custom_display_config()
        elif self.root_report_id and self.root_report_id.custom_handler_model_name:
            custom_display_config = self.env[self.root_report_id.custom_handler_model_name]._get_custom_display_config()
        else:
            custom_display_config = {}

        return {
            'caret_options': self._get_caret_options(),
            'column_headers_render_data': self._get_column_headers_render_data(options),
            'column_groups_totals': json_friendly_column_group_totals,
            'context': self.env.context,
            'custom_display': custom_display_config,
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
            'annotations': self.get_annotations(options),
            'groups': {
                'analytic_accounting': self.env.user.has_group('analytic.group_analytic_accounting'),
                'account_readonly': self.env.user.has_group('account.group_account_readonly'),
                'account_user': self.env.user.has_group('account.group_account_user'),
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

    @api.readonly
    def get_report_information_readonly(self, options):
        """ Readonly version of get_report_information, to be called from RPC when options['readonly_query'] is True,
        to better spread the load on servers when possible.
        """
        return self.get_report_information(options)

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
            return self.chart_template in set(companies.mapped('chart_template'))

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
                # Separate non-budget and budget headers
                budget_count = sum(
                    any(key in header.get('forced_options', {}) for key in ('compute_budget', 'budget_percentage'))
                    for header in column_header
                )
                non_budget_count = len(column_header) - budget_count

                # budget headers (amount and percentage) can only contain a single column each, regardless of the amount of columns in the report.
                # This implies that we first need to multiply for the 'regular' columns and then add the budget columns.
                colspan *= non_budget_count
                colspan += budget_count

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

    def get_expanded_lines(self, options, line_dict_id, groupby, expand_function_name, progress, offset, horizontal_split_side):
        self.env.flush_all()
        self._init_currency_table(options)

        lines = self._expand_unfoldable_line(expand_function_name, line_dict_id, groupby, options, progress, offset, horizontal_split_side)
        lines = self._fully_unfold_lines_if_needed(lines, options)

        self._inject_account_names_for_consolidation(lines)

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(self, options, lines)

        self._format_column_values(options, lines)
        return lines

    @api.readonly
    def get_expanded_lines_readonly(self, options, line_dict_id, groupby, expand_function_name, progress, offset, horizontal_split_side):
        """ Readonly version of get_expanded_lines_readonly, to be called from RPC when options['readonly_query'] is True,
        to better spread the load on servers when possible.
        """
        return self.get_expanded_lines(options, line_dict_id, groupby, expand_function_name, progress, offset, horizontal_split_side)

    def _expand_unfoldable_line(self, expand_function_name, line_dict_id, groupby, options, progress, offset, horizontal_split_side, unfold_all_batch_data=None):
        if not expand_function_name:
            raise UserError(_("Trying to expand a line without an expansion function."))

        if not progress:
            progress = {column_group_key: 0 for column_group_key in options['column_groups']}

        expand_function = self._get_custom_report_function(expand_function_name, 'expand_unfoldable_line')
        expansion_result = expand_function(line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=unfold_all_batch_data)

        rslt = expansion_result['lines']

        if horizontal_split_side:
            for line in rslt:
                line['horizontal_split_side'] = horizontal_split_side

        # Apply integer rounding to the result if needed.
        # The groupby expansion function is the only one guaranteed to call the expressions computation,
        # so the values computed for it will already have been rounded if integer rounding is enabled. No need to round them again.
        if expand_function_name != '_report_expand_unfoldable_line_with_groupby':
            self._apply_integer_rounding_to_dynamic_lines(options, rslt)

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

    def _cleanup_empty_sections(self, lines):
        """ Resets the fold state for parents left without visible children, and removes their orphaned total lines.
        The total line removal only applies when called after _add_totals_below_sections.
        """
        # Collect parent IDs that still have at least one non-total child visible.
        # Total lines are generated from the parent itself and don't count as expandable children.
        parents_with_non_total_child = set()
        markups = {}
        for line in lines:
            markup = self._get_markup(line['id'])
            markups[line['id']] = markup
            parent_id = line.get('parent_id')
            if parent_id is not None and markup != 'total':
                parents_with_non_total_child.add(parent_id)

        result = []
        for line in lines:
            # Lines with an expand_function load their children on demand, so hide_if_zero doesn't affect them.
            if line.get('expand_function'):
                result.append(line)
            elif markups[line['id']] == 'total':
                # Keep the total only if its parent still has real children.
                if line.get('parent_id') in parents_with_non_total_child:
                    result.append(line)
            elif line['id'] in parents_with_non_total_child:
                result.append(line)
            else:
                line['unfoldable'] = False
                line['unfolded'] = False
                result.append(line)

        return result

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

            line_id = self._get_generic_line_id(None, None, parent_line_id=parent_line_dict_id, markup={'groupby_prefix_group': prefix_key})

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
                'hide_line_buttons': True,
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
            elif isinstance(markup, dict) and 'groupby' in markup or 'groupby_prefix_group' in markup:
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
            if markup and isinstance(markup, dict) and 'groupby_prefix_group' in markup:
                prefix_piece = markup['groupby_prefix_group']
                matched_prefix += prefix_piece.upper()
            else:
                # Might happen if a groupby is grouped by prefix, then a subgroupby is grouped by another subprefix.
                # In this case, we want to reset the prefix group to only consider the one used in the subgroupby.
                matched_prefix = ''

        return matched_prefix

    @api.model
    def format_value(self, options, value, figure_type, format_params=None):
        if format_params is None:
            format_params = {}

        if 'currency' in format_params:
            format_params['currency'] = self.env['res.currency'].browse(format_params['currency'].id)

        return self._format_value(options=options, value=value, figure_type=figure_type, format_params=format_params)

    def _format_value(self, options, value, figure_type, format_params=None):
        """ Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want.
        """
        if value is None:
            return ''

        if figure_type == 'none':
            return value

        if isinstance(value, str) or figure_type == 'string':
            return str(value)

        if format_params is None:
            format_params = {}

        formatLang_params = {
            'rounding_method': 'HALF-UP',
            'rounding_unit': options.get('rounding_unit'),
        }

        if figure_type == 'monetary':
            currency = self.env['res.currency'].browse(format_params['currency_id']) if 'currency_id' in format_params else self.env.company.currency_id
            if options.get('multi_currency'):
                formatLang_params['currency_obj'] = currency
            else:
                formatLang_params['digits'] = currency.decimal_places

        elif figure_type == 'integer':
            formatLang_params['digits'] = 0

        elif figure_type == 'boolean':
            return _("Yes") if bool(value) else _("No")

        elif figure_type in ('date', 'datetime'):
            return format_date(self.env, value)

        else:
            formatLang_params['digits'] = format_params.get('digits', 1)

        if self._is_value_zero(value, figure_type, format_params):
            # Make sure -0.0 becomes 0.0
            value = abs(value)

        if self._context.get('no_format'):
            return value

        formatted_amount = formatLang(self.env, value, **formatLang_params)

        if figure_type == 'percentage':
            return f"{formatted_amount}%"

        return formatted_amount

    @api.model
    def _is_value_zero(self, amount, figure_type, format_params):
        if amount is None:
            return True

        if figure_type == 'monetary':
            currency = self.env['res.currency'].browse(format_params['currency_id']) if 'currency_id' in format_params else self.env.company.currency_id
            return currency.is_zero(amount)
        elif figure_type in NUMBER_FIGURE_TYPES:
            return float_is_zero(amount, precision_digits=format_params.get('digits', 0))
        else:
            return False

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

    def _get_report_send_recipients(self, options):
        custom_handler_model = self._get_custom_handler_model()
        if custom_handler_model and hasattr(self.env[custom_handler_model], '_get_report_send_recipients'):
            return self.env[custom_handler_model]._get_report_send_recipients(options)
        return self.env['res.partner']

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
            key=lambda report: len(report[1]['columns']) > 5 or report[1].get('horizontal_split')
        )

        footer = self.env['ir.actions.report']._render_template("account_reports.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())))

        action_report = self.env['ir.actions.report']
        files_stream = []
        for is_landscape, reports_with_options in grouped_reports_by_format:
            bodies = []

            for report, report_options in reports_with_options:
                # Use custom handler's PDF export method if available
                custom_handler_model = report._get_custom_handler_model()
                handler = self.env[custom_handler_model] if (
                    custom_handler_model and hasattr(self.env[custom_handler_model], '_get_pdf_export_html')
                ) else report
                bodies.append(handler._get_pdf_export_html(
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
                </tbody></table></div>
                <div style="page-break-after: always"></div>
                <div class="d-flex align-items-start">
                <table class="o_table">
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

        # Manage annotations.
        render_values['annotations'] = self._build_annotations_list_for_pdf_export(options['date'], lines, report_info['annotations'])

        options['css_custom_class'] = report_info['custom_display'].get('css_custom_class', '')

        # Render.
        return self.env['ir.qweb']._render(template, render_values)

    def _build_annotations_list_for_pdf_export(self, date_options, lines, annotations_per_line_id):
        annotations_to_render = []
        number = 0
        for line in lines:
            if line_annotations := annotations_per_line_id.get(line['id']):
                line['annotations'] = []
                for annotation in line_annotations:
                    report_period_date_from = datetime.datetime.strptime(date_options['date_from'], '%Y-%m-%d').date()
                    report_period_date_to = datetime.datetime.strptime(date_options['date_to'], '%Y-%m-%d').date()
                    if not annotation['date'] or report_period_date_from <= annotation['date'] <= report_period_date_to:
                        number += 1
                        line['annotations'].append(str(number))
                        annotations_to_render.append({
                            'number': str(number),
                            'text': annotation['text'],
                            'date': format_date(self.env, annotation['date']) if annotation['date'] else None,
                        })
        return annotations_to_render

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
        def add_worksheet_unique_name(workbook, sheet_name):
            existing_names = set(workbook.sheetnames.keys())
            count = 1
            max_length = 31
            new_sheet_name = sheet_name[:max_length]

            while new_sheet_name in existing_names:
                suffix = f" ({count})"
                truncated_name = sheet_name[:max_length - len(suffix)]
                new_sheet_name = f"{truncated_name}{suffix}"
                count += 1
            return workbook.add_worksheet(new_sheet_name)

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
            # Use custom handler's XLSX export method if available
            custom_handler_model = report._get_custom_handler_model()
            if custom_handler_model and hasattr(self.env[custom_handler_model], '_inject_report_into_xlsx_sheet'):
                self.env[custom_handler_model]._inject_report_into_xlsx_sheet(report_options, workbook)
            else:
                report._inject_report_into_xlsx_sheet(report_options, workbook, add_worksheet_unique_name(workbook, report.name))

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

    @api.model
    def _set_xlsx_cell_sizes(self, sheet, fonts, col, row, value, style, has_colspan):
        """ This small helper will resize the cells if needed, to allow to get a better output. """
        def get_string_width(font, string):
            return font.getlength(string) / 5

        # Get the correct font for the row style
        font_type = ('Bol' if style.bold else 'Reg') + ('Ita' if style.italic else '')
        report_font = fonts[font_type]

        # 8.43 is the default width of a column in Excel.
        if parse_version(xlsxwriter.__version__) >= parse_version('3.0.6'):
            # cols_sizes was removed in 3.0.6 and colinfo was replaced by col_info
            # see https://github.com/jmcnamara/XlsxWriter/commit/860f4a2404549aca1eccf9bf8361df95dc574f44
            try:
                col_width = sheet.col_info[col][0]
            except KeyError:
                col_width = 8.43
        else:
            col_width = sheet.col_sizes.get(col, [8.43])[0]

        row_height = sheet.row_sizes.get(row, [8.43])[0]

        if value is None:
            value = ''
        else:
            try:  # noqa: SIM105
                # This is needed, otherwise we could compute width on very long number such as 12.0999999998
                # which wouldn't show well in the end result as the numbers are rounded.
                value = float_repr(float(value), self.env.company.currency_id.decimal_places)
            except (ValueError, OverflowError):
                pass

        # Start by computing the width of the cell if we are not using colspans.
        if not has_colspan:
            # Ensure to take indents into account when computing the width.
            formatted_value = f"{'  ' * style.indent}{value}"
            width = get_string_width(
                report_font,
                max(formatted_value.split('\n'), key=lambda line: get_string_width(report_font, line))
            )
            # We set the width if it is bigger than the current one, with a limit at 75 (max to avoid taking excessive space).
            if width > col_width:
                sheet.set_column(col, col, min(width + 4, 75))  # We need to add a little extra padding to ensure our columns are not clipping the text

    def _get_xlsx_export_fonts(self):
        """ Get the bold, italic and regular LATO font information so that we can use them for format purposes. """
        fonts = {}
        for font_type in ('Reg', 'Bol', 'RegIta', 'BolIta'):
            try:
                lato_path = f'web/static/fonts/lato/Lato-{font_type}-webfont.ttf'
                fonts[font_type] = ImageFont.truetype(file_path(lato_path), 12)
            except (OSError, FileNotFoundError):
                # This won't give great result, but it will work.
                fonts[font_type] = ImageFont.load_default()
        return fonts

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        fonts = self._get_xlsx_export_fonts()

        def write_cell(sheet, x, y, value, style, colspan=1, datetime=False):
            self._set_xlsx_cell_sizes(sheet, fonts, x, y, value, style, colspan > 1)
            if colspan == 1:
                if datetime:
                    sheet.write_datetime(y, x, value, style)
                else:
                    sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        default_format_props = {'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666', 'num_format': '#,##0.00'}
        text_format_props = {'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666'}
        date_format_props = {'font_name': 'Lato', 'font_size': 12, 'font_color': '#666666', 'align': 'left', 'num_format': 'yyyy-mm-dd'}
        title_format = workbook.add_format({'font_name': 'Lato', 'font_size': 12, 'bold': True, 'bottom': 2})
        annotation_format = workbook.add_format({**text_format_props, 'text_wrap': True})
        workbook_formats = {
            0: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
            },
            1: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
            },
            2: {
                'default': workbook.add_format({**default_format_props, 'bold': True}),
                'text': workbook.add_format({**text_format_props, 'bold': True}),
                'date': workbook.add_format({**date_format_props, 'bold': True}),
                'initial': workbook.add_format(default_format_props),
                'total': workbook.add_format({**default_format_props, 'bold': True}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'indent': 2}),
                'initial_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 1}),
            },
            'default': {
                'default': workbook.add_format(default_format_props),
                'text': workbook.add_format(text_format_props),
                'date': workbook.add_format(date_format_props),
                'total': workbook.add_format(default_format_props),
                'default_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'indent': 2}),
            },
        }

        def get_format(content_type='default', level='default'):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats['default'],
                    'default_indent': workbook.add_format({**default_format_props, 'indent': level}),
                    'date_indent': workbook.add_format({**date_format_props, 'indent': level}),
                    'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': level - 1}),
                }

            level_formats = workbook_formats[level]
            if '_indent' in content_type and not level_formats.get(content_type):
                return level_formats.get('default_indent', level_formats.get(content_type.removesuffix('_indent'), level_formats['default']))
            return level_formats.get(content_type, level_formats['default'])

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))
        annotations = self.get_annotations(options)

        # For reports with lines generated for accounts, the account name and codes are shown in a single column.
        # To help user post-process the report if they need, we should in such a case split the account name and code in two columns.
        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            if line_model == 'account.account':
                # Reuse the _split_code_name to split the name and code in two values.
                account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])

        # Set the (Account) Name column width to 50.
        # If we have account lines and split the name and code in two columns, we will also set the code column.
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 13)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

        if not options.get('no_xlsx_currency_code_columns'):
            self._add_xlsx_currency_codes_columns(options, lines)

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
                write_cell(sheet, x_offset, y_offset, header_to_render.get('name', ''), title_format, colspan + (1 if options['show_horizontal_group_total'] and header_level_index == 0 else 0))
                x_offset += colspan
            if options.get('column_percent_comparison') in ('growth', 'analytic_coverage'):
                write_cell(sheet, x_offset, y_offset, '%', title_format)
                x_offset += 1

            if options['show_horizontal_group_total'] and header_level_index != 0:
                horizontal_group_name = next((group['name'] for group in options['available_horizontal_groups'] if group['id'] == options['selected_horizontal_group_id']), None)
                write_cell(sheet, x_offset, y_offset, horizontal_group_name, title_format)
                x_offset += 1
            if annotations:
                annotations_x_offset = x_offset
                write_cell(sheet, annotations_x_offset, y_offset, 'Annotations', title_format)
                x_offset += 1
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_cell(sheet, x_offset, y_offset, subheader.get('name', ''), title_format, colspan)
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        if account_lines_split_names:
            # If we have a separate account code column, add a title for it
            write_cell(sheet, x_offset - 2, y_offset, _("Code"), title_format)
            write_cell(sheet, x_offset - 1, y_offset, _("Account Name"), title_format)
        sheet.set_column(x_offset, x_offset + len(options['columns']), 10)

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_cell(sheet, x_offset, y_offset, column.get('name', ''), title_format, colspan)
            x_offset += colspan

        if options['show_horizontal_group_total']:
            write_cell(sheet, x_offset, y_offset, options['columns'][0].get('name', ''), title_format, colspan)

        if options.get('column_percent_comparison') in ('growth', 'analytic_coverage'):
            write_cell(sheet, x_offset, y_offset, '', title_format, colspan)
        y_offset += 1

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        # Disable bold styling for the max level.
        max_level = max(line.get('level', -1) for line in lines) if lines else -1
        if max_level in {0, 1, 2}:
            # Total lines are supposed to be a level above, so we don't touch them.
            for wb_format in (s for s in workbook_formats[max_level] if 'total' not in s):
                workbook_formats[max_level][wb_format].set_bold(False)

        # Add lines.
        counter = 1
        for y, line in enumerate(lines):
            level = line.get('level')
            if level == 0:
                y_offset += 1
            elif not level:
                level = 'default'

            line_id = self._parse_line_id(line.get('id'))
            is_initial_line = line_id[-1][0] == 'initial' if line_id else False
            is_total_line = line_id[-1][0] == 'total' if line_id else False

            # Write the first column(s), with a specific style to manage the indentation.
            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format('text', level)

            if cell_type == 'date':
                cell_format = get_format('date_indent', level)
            elif is_initial_line:
                cell_format = get_format('initial_indent', level)
            elif is_total_line:
                cell_format = get_format('total_indent', level)
            else:
                cell_format = get_format('default_indent', level)

            x_offset = original_x_offset + 1
            if lines[y]['id'] in account_lines_split_names:
                # Write the Account Code and Name columns.
                code, name = account_lines_split_names[lines[y]['id']]
                # Don't indent the account code and don't format is as a monetary value either.
                write_cell(sheet, 0, y + y_offset, code, account_code_cell_format)
                write_cell(sheet, 1, y + y_offset, name, cell_format)
            else:
                write_cell(sheet, original_x_offset, y + y_offset, cell_value, cell_format, datetime=cell_type == 'date')

                if 'parent_id' in line and line['parent_id'] in account_lines_split_names:
                    write_cell(sheet, 1 + original_x_offset, y + y_offset, account_lines_split_names[line['parent_id']][0], account_code_cell_format)
                elif account_lines_split_names:
                    write_cell(sheet, 1 + original_x_offset, y + y_offset, "", account_code_cell_format)

            # Write all the remaining cells.
            columns = line['columns']
            if options.get('column_percent_comparison') and 'column_percent_comparison_data' in line:
                columns += [line['column_percent_comparison_data']]

            if options['show_horizontal_group_total']:
                columns += [line.get('horizontal_group_total_data', {'name': 0})]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)
                if cell_type == 'date':
                    cell_format = get_format('date', level)
                elif is_initial_line:
                    cell_format = get_format('initial', level)
                elif is_total_line:
                    cell_format = get_format('total', level)
                else:
                    cell_format = get_format('default', level)
                write_cell(sheet, x + line.get('colspan', 1) - 1, y + y_offset, cell_value, cell_format, datetime=cell_type == 'date')

            # Write annotations.
            if annotations and (line_annotations := annotations.get(line['id'])):
                line_annotation_text = []
                for line_annotation in line_annotations:
                    line_annotation_text.append(f"{counter} - {line_annotation['text']}")
                    counter += 1
                write_cell(sheet, annotations_x_offset, y + y_offset, "\n".join(line_annotation_text), annotation_format)

    def _add_xlsx_currency_codes_columns(self, options, lines):
        """ Adds a 'Currency Code' column for each column displaying amounts in foreign currencies. This is done because
        the raw number is displayed on the xlsx file, making it impossible to know the currency used.
        To have it displayed, the line must have an expression label starting with '_currency_' """
        required_currency_code_columns = {
            label.removeprefix('_currency_')
            for label in self.line_ids.expression_ids.mapped('label')
            if label.startswith('_currency_')
        }

        new_columns = []
        for col in options['columns']:
            new_columns.append(col)

            if col['expression_label'] in required_currency_code_columns:
                new_columns.append({
                    **col,
                    'name': _("Currency Code"),
                    'figure_type': 'string',
                    'expression_label': f"_xlsx_currency_code_{col['expression_label']}"
                })

        options['columns'] = new_columns

        # Add 'Currency Code' values to each line
        for line in lines:
            new_column_values = []

            for index, col_data in enumerate(line['columns']):
                new_column_values.append(col_data)

                if col_data.get('expression_label') in required_currency_code_columns:
                    currency = col_data.get('currency')
                    currency_code = currency.name if currency else ''
                    new_column = self._build_column_dict(currency_code, options['columns'][index+1], options)
                    new_column['name'] = new_column['no_format']
                    new_column_values.append(new_column)

            line['columns'] = new_column_values

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

            filters_sheet.write(y_offset, 0, report.name, name_style)
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
            (_("Unreconciled Entries"), 'unreconciled', self.filter_unreconciled),
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
            lg = get_lang(self.env, self.env.user.lang)
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

        # Display unfold & initial balance even when debit/credit column is hidden and the balance == 0
        if not any(isinstance(column.get('no_format'), (int, float)) and column.get('expression_label') != 'balance' for column in line_columns):
            return None

        return {
            'id': self._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='initial'),
            'name': _("Initial Balance"),
            'level': 3 + level_shift,
            'parent_id': parent_line_id,
            'columns': line_columns,
        }

    def _compute_column_percent_comparison_data(self, options, value1, value2, green_on_positive=True):
        ''' Helper to get the additional columns due to the growth comparison feature. When only one comparison is
        requested, an additional column is there to show the percentage of growth based on the compared period.
        :param options:             The report options.
        :param value1:              The value in the current period.
        :param value2:              The value in the compared period.
        :param green_on_positive:   A flag customizing the value with a green color depending if the growth is positive.
        :return:                    The new columns to add to line['columns'].
        '''
        if not isinstance(value1, (int, float)) or not isinstance(value2, (int, float)) or float_is_zero(value2, precision_rounding=0.1):
            return {'name': _('n/a'), 'mode': 'muted'}

        comparison_type = options['column_percent_comparison']
        if comparison_type == 'growth':

            values_diff = value1 - value2
            growth = round(values_diff / value2 * 100, 1)

            # In case the comparison is made on a negative figure, the color should be the other
            # way around. For example:
            #                       2018         2017           %
            # Product Sales      1000.00     -1000.00     -200.0%
            #
            # The percentage is negative, which is mathematically correct, but my sales increased
            # => it should be green, not red!
            if float_is_zero(growth, 1):
                return {'name': '0.0%', 'mode': 'muted'}
            else:
                return {
                    'name': f"{float_repr(growth, 1)}%",
                    'mode': 'red' if ((values_diff > 0) ^ green_on_positive) else 'green',
                }

        elif comparison_type == 'budget':
            percentage_value = value1 / value2 * 100
            if float_is_zero(percentage_value, 1):
                # To avoid negative 0
                return {'name': '0.0%', 'mode': 'green'}

            comparison_value = float_compare(value1, value2, 1)
            return {
                'name': f"{float_repr(percentage_value, 1)}%",
                'mode': 'green' if (comparison_value >= 0 and green_on_positive) or (comparison_value == -1 and not green_on_positive) else 'red',
            }

        elif comparison_type == 'analytic_coverage':
            coverage = round(value1 / value2 * 100, 1)
            if float_is_zero(coverage, precision_rounding=0.1):
                return {'name': '0.0%'}
            else:
                return {
                    'name': str(coverage) + '%',
                    'mode': 'green' if float_compare(coverage, 100, 1) == 0 else 'red',
                }

    def _set_budget_column_comparisons(self, options, line):
        """
            Set the percentage values in the budget columns
        """
        for col_index, col in enumerate(line['columns']):
            col_group_data = options['column_groups'][col['column_group_key']]
            if 'budget_percentage' in col_group_data.get('forced_options'):
                budget_id = col_group_data['forced_options']['budget_percentage']
                date_key = col_group_data.get('forced_options', {}).get('date')
                if not date_key:
                    continue

                budget_base_col = None
                budget_amount_col = None
                for line_col in line['columns']:
                    other_col_group_key = line_col['column_group_key']
                    other_col_options = options['column_groups'][other_col_group_key]
                    if other_col_options.get('forced_options', {}).get('date') == date_key:
                        if other_col_options.get('forced_options', {}).get('budget_base') and line_col['figure_type'] == 'monetary':
                            budget_base_col = line_col
                        elif other_col_options.get('forced_options', {}).get('compute_budget') == budget_id:
                            budget_amount_col = line_col
                if budget_base_col is None or budget_amount_col is None:
                    continue
                value = self._compute_column_percent_comparison_data(
                    options,
                    budget_base_col['no_format'],
                    budget_amount_col['no_format'],
                    green_on_positive=budget_base_col['green_on_positive'],
                )
                comparison_column = self._build_column_dict(
                    value['name'],
                    {
                        **budget_amount_col,
                        'figure_type': 'string',
                        'comparison_mode': value['mode'],
                    }
                )
                line['columns'][col_index] = comparison_column

    def _check_groupby_fields(self, groupby_fields_name: list[str] | str):
        """ Checks that each string in the groupby_fields_name list is a valid groupby value for an accounting report.
            So it must be:
            - a field from account.move.line which is (1) searchable and (2) for which _field_to_sql is implemented,
              this includes stored and related non-stored fields, or
            - a custom value allowed by the _get_custom_groupby_map function of the custom handler
        """
        self.ensure_one()
        if isinstance(groupby_fields_name, str | bool):
            groupby_fields_name = groupby_fields_name.split(',') if groupby_fields_name else []

        for field_name in (fname.strip() for fname in groupby_fields_name):
            groupby_field = self.env['account.move.line']._fields.get(field_name)
            if groupby_field:
                if not groupby_field._description_searchable:
                    raise UserError(self.env._("Field %s of account.move.line is not searchable and can therefore not be used in a groupby expression.", field_name))
                try:
                    self.env['account.move.line']._field_to_sql('account_move_line', field_name, Query(self.env, 'account_move_line'))
                except ValueError:
                    raise UserError(self.env._("Field %s of account.move.line cannot be used in a groupby expression.", field_name)) from None
            elif (custom_handler_name := self._get_custom_handler_model()):
                if field_name not in self.env[custom_handler_name]._get_custom_groupby_map():
                    raise UserError(_("Field %s does not exist on account.move.line, and is not supported by this report's custom handler.", field_name))
            else:
                raise UserError(_("Field %s does not exist on account.move.line.", field_name))

    # ============ Accounts Coverage Debugging Tool - START ================
    @api.depends('country_id', 'chart_template', 'root_report_id')
    def _compute_is_account_coverage_report_available(self):
        for report in self:
            report.is_account_coverage_report_available = (
                (
                    report.availability_condition == 'country' and self.env.company.account_fiscal_country_id == report.country_id
                    or
                    report.availability_condition == 'coa' and self.env.company.chart_template == report.chart_template
                    or
                    report.availability_condition == 'always'
                )
                and
                report.root_report_id in (
                    self.env.ref('account_reports.profit_and_loss', raise_if_not_found=False),
                    self.env.ref('account_reports.balance_sheet', raise_if_not_found=False)
                )
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
            if len(set(candidate_duplicate_lines.mapped('name'))) <= 1:
                continue
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

    def _generate_file_data_with_error_check(self, options, content_generator, generator_params, errors):
        """ Checks for critical errors (i.e. errors that would cause the rendering to fail) in the generator values.
            If at least one error is critical, the 'account.report.file.download.error.wizard' wizard is opened
            before rendering the file, so they can be fixed.
            If there are only non-critical errors, the wizard is opened after the file has been generated,
            allowing the user to download it anyway.

            :param dict options: The report options.
            :param def content_generator: The function used to generate the exported content.
            :param dict generator_params: The parameters passed to the 'content_generator' method (List).
            :param list errors: A list of errors in the following format:
                [
                    {
                        'message': The error message to be displayed in the wizard (String),
                        'action_text': The text of the action button (String),
                        'action': Contains the action values (Dictionary),
                        'level': One of 'info', 'warning', 'danger'. (String).
                                 Only the 'danger' level represents a blocking error.
                    },
                    {...},
                ]
            :returns: The data that will be used by the file generator.
            :rtype: dict
        """
        if errors is None:
            errors = []
        self.ensure_one()
        if any(error_value.get('level') == 'danger' for error_value in errors.values()):
            raise AccountReportFileDownloadException(errors)

        content = content_generator(**generator_params)

        file_data = {
            'file_name': self.get_default_report_filename(options, generator_params['file_type']),
            'file_content': re.sub(r'\n\s*\n', '\n', content).encode(),
            'file_type': generator_params['file_type'],
        }

        if errors:
            raise AccountReportFileDownloadException(errors, file_data)

        return file_data

    def action_create_composite_report(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.report',
            'views': [[False, 'form']],
            'context': {
                'default_section_report_ids': self.ids,
            }
        }

    def show_error_branch_allowed(self, *args, **kwargs):
        raise UserError(_("Please select the main company and its branches in the company selector to proceed."))


class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    display_custom_groupby_warning = fields.Boolean(compute='_compute_display_custom_groupby_warning')

    @api.depends('groupby', 'user_groupby')
    def _compute_display_custom_groupby_warning(self):
        for line in self:
            line.display_custom_groupby_warning = line.get_external_id()[line.id] and line.user_groupby != line.groupby

    @api.constrains('groupby', 'user_groupby')
    def _validate_groupby(self):
        super()._validate_groupby()
        for report_line in self:
            report_line.report_id._check_groupby_fields(report_line.user_groupby)
            report_line.report_id._check_groupby_fields(report_line.groupby)

    def _expand_groupby(self, line_dict_id, groupby, options, offset=0, limit=None, load_one_more=False, unfold_all_batch_data=None):
        """ Expand function used to get the sublines of a groupby.
        groupby param is a string consisting of one or more coma-separated field names. Only the first one
        will be used for the expansion; if there are subsequent ones, the generated lines will themselves used them as
        their groupby value, and point to this expand_function, hence generating a hierarchy of groupby).
        """
        self.ensure_one()

        group_indent = 0
        line_id_list = self.report_id._parse_line_id(line_dict_id)

        # Parse groupby
        groupby_data = self._parse_groupby(options, groupby_to_expand=groupby)
        groupby_model = groupby_data['current_groupby_model']
        next_groupby = groupby_data['next_groupby']
        current_groupby = groupby_data['current_groupby']
        custom_groupby_map = groupby_data['custom_groupby_map']

        # If this line is a sub-groupby of groupby line (for example, when grouping by partner, id; the id line is a subgroup of partner),
        # we need to add the domain of the parent groupby criteria to the options
        prefix_groups_count = 0
        sub_groupby_domain = []
        full_sub_groupby_key_elements = []
        for markup, model, value in line_id_list:
            if isinstance(markup, dict) and 'groupby' in markup:
                field_name = markup['groupby']
                if field_name in custom_groupby_map:
                    sub_groupby_domain += custom_groupby_map[field_name]['domain_builder'](value)
                else:
                    sub_groupby_domain.append((field_name, '=', value))
                full_sub_groupby_key_elements.append(f"{field_name}:{value}")
            elif isinstance(markup, dict) and 'groupby_prefix_group' in markup:
                prefix_groups_count += 1

            if model == 'account.group':
                group_indent += 1

        if sub_groupby_domain:
            forced_domain = options.get('forced_domain', []) + sub_groupby_domain
            options = {**options, 'forced_domain': forced_domain}

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
            line_id = self.report_id._get_generic_line_id(groupby_model, grouping_key, parent_line_id=line_dict_id, markup={'groupby': current_groupby})
            group_line_dict = {
                # 'name' key will be set later, so that we can browse all the records of this expansion at once (in case we're dealing with records)
                'id': line_id,
                'unfoldable': bool(next_groupby),
                'unfolded': (next_groupby and options['unfold_all']) or line_id in options['unfolded_lines'],
                'groupby': next_groupby,
                'columns': self.report_id._build_static_line_columns(self, options, group_totals, groupby_model=groupby_model),
                'level': self.hierarchy_level + 2 * (prefix_groups_count + len(sub_groupby_domain) + 1) + (group_indent - 1),
                'parent_id': line_dict_id,
                'expand_function': '_report_expand_unfoldable_line_with_groupby' if next_groupby else None,
                'caret_options': groupby_model if not next_groupby else None,
            }

            if self.report_id.custom_handler_model_id:
                self.env[self.report_id.custom_handler_model_name]._custom_groupby_line_completer(self.report_id, options, group_line_dict)

            # Growth comparison column.
            if options.get('column_percent_comparison') == 'growth':
                compared_expression = self.expression_ids.filtered(lambda expr: expr.label == group_line_dict['columns'][0]['expression_label'])
                group_line_dict['column_percent_comparison_data'] = self.report_id._compute_column_percent_comparison_data(
                    options, group_line_dict['columns'][0]['no_format'], group_line_dict['columns'][1]['no_format'], green_on_positive=compared_expression.green_on_positive)
            # Manage budget comparison
            elif options.get('column_percent_comparison') == 'budget':
                self.report_id._set_budget_column_comparisons(options, group_line_dict)
            elif options.get('column_percent_comparison') == 'analytic_coverage':
                group_line_dict[
                    'column_percent_comparison_data'] = self.report_id._compute_column_percent_comparison_data(
                    options, group_line_dict['columns'][0]['no_format'], group_line_dict['columns'][1]['no_format'], green_on_positive=False)
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
            for non_relational_key in sorted(group_lines_by_keys.keys(), key=lambda k: (k is None, k)):
                if custom_groupby_name_builder := custom_groupby_map.get(current_groupby, {}).get('label_builder'):
                    keys_and_names_in_sequence[non_relational_key] = custom_groupby_name_builder(non_relational_key)
                else:
                    if non_relational_key is None:
                        keys_and_names_in_sequence[non_relational_key] = _("Undefined")
                    else:
                        groupby_field = self.env['account.move.line']._fields[groupby_data['current_groupby']]
                        if groupby_field.type == 'selection':
                            selection_options = dict(groupby_field._description_selection(self.env))
                            keys_and_names_in_sequence[non_relational_key] = selection_options.get(non_relational_key) or _("Undefined")
                        else:
                            keys_and_names_in_sequence[non_relational_key] = str(non_relational_key)

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
        # TODO master: remove this method as it is dead code
        if groupby_model is None:
            return grouping_key

        if grouping_key is None:
            return _("Unknown")

        return self.env[groupby_model].browse(grouping_key).display_name

    def _parse_groupby(self, options, groupby_to_expand=None):
        """ Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 4 keys:
            'current_groupby':       The name of the value to be used to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded. That value can be either a field of account.move.line, or
                                     a custom groupby value defined in this report's custom handler's _get_custom_groupby_map function.

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated values (again,
                                     either field names from account.move.line or a custom groupby defined on the handler).
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

            'custom_groupby_map';    The groupby map, used to handle custom groupby values, as returned by the _get_custom_groupby_map function
                                     of the custom handler (by default, it will be an empty dict)

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

        custom_handler_name = self.report_id._get_custom_handler_model()
        custom_groupby_map = self.env[custom_handler_name]._get_custom_groupby_map() if custom_handler_name else {}
        if current_groupby in custom_groupby_map:
            groupby_model = custom_groupby_map[current_groupby]['model']
        elif current_groupby == 'id':
            groupby_model = 'account.move.line'
        elif current_groupby:
            groupby_model = self.env['account.move.line']._fields[current_groupby].comodel_name
        else:
            groupby_model = None

        return {
            'current_groupby': current_groupby,
            'next_groupby': next_groupby,
            'current_groupby_model': groupby_model,
            'custom_groupby_map': custom_groupby_map,
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

        date_from, date_to = self.report_line_id.report_id._get_date_bounds_info(options, self.date_scope)

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


class AccountReportExternalValue(models.Model):
    _inherit = 'account.report.external.value'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._check_lock_date_violation(set(self._build_vals_to_check_for_lock_date(records)))
        return records

    def write(self, vals):
        # We need to build vals_to_check before the super() call because of the 'target_report_expression_id' field :
        # if the user tries to modify this specific field, it'll potentially change the linked report id, and so he can
        # bypass the lock dates from the original report (if it was a tax report for example)
        vals_to_check = set(self._build_vals_to_check_for_lock_date(self))
        res = super().write(vals)
        # Then we add the modified records
        for lock_date_to_check in self._build_vals_to_check_for_lock_date(self):
            vals_to_check.add(lock_date_to_check)
        self._check_lock_date_violation(vals_to_check)
        return res

    @api.model
    def _build_vals_to_check_for_lock_date(self, records):
        """
        Generator method to build tuples out of records. The tuples will contain 3 values:
        - is tax, bool: is the external value linked to a tax report
        - date to check, date: the date we want to check the lock dates for
        - company, res.company: the company we want to check the lock dates for
        """
        generic_tax_report = self.env.ref('account.generic_tax_report')
        for external_value in records:
            report = external_value.target_report_expression_id.report_line_id.report_id
            yield (
                not self.env.context.get('ignore_tax_lock_date') and generic_tax_report in (report + report.root_report_id + report.section_main_report_ids.root_report_id),  # is tax
                external_value.date,  # date to check
                external_value.company_id,  # company
            )

    def _check_lock_date_violation(self, vals_to_check):
        """
        This method raises an error if the companies have lock dates after the date we want to create/write the values
        :param vals_to_check: a set of tuples like: `{(is_tax, date, company_id)}`
        """
        for is_tax, date, company_id in vals_to_check:
            violated_lock_dates = company_id._get_lock_date_violations(
                date,
                sale=False,
                purchase=False,
                tax=is_tax,
            )
            if violated_lock_dates:
                lock_date_names = [company_id._fields[lock_date[1]].get_description(self.env)['string'] for lock_date in violated_lock_dates]
                lock_dates = "\n- " + "\n- ".join(lock_date_names)
                raise ValidationError(_("You cannot update this value as it's locked by: %s", lock_dates))


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

    def _custom_options_initializer(self, report, options, previous_options):
        """ To be overridden to add report-specific _init_options... code to the report. """
        if report.root_report_id and report.root_report_id.custom_handler_model_id != report.custom_handler_model_id:
            report.root_report_id._init_options_custom(options, previous_options)

    def _custom_line_postprocessor(self, report, options, lines):
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

    def _get_custom_groupby_map(self):
        """ Allows the use of custom values in the groupby field of account.report.line, to use them in custom engines. Those custom
        values can be anything, and need to be properly handled by the custom engine using them. This allows adding support for grouping on
        something else than just the fields of account.move.line, which is the default.

        :return:    A dict, in the form {groupby_name: {'model': model, 'domain_builder': domain_builder}}, where:
                        - groupby_name is the custom value to use in groupby instead of one of aml's field names
                        - model: is a model name (a string), representing the model the value returned for this custom groupby targets.
                                 The model will be used to compute the display_name to show for each generated groupby line, in the UI.
                                 This value can be passed to None ; in such case, the raw value returned by the engine will be shown.
                        - domain_builder is a function to be called when expanding a groupby line generated by this custom groupby, to compute the
                                 domain to apply in order to restrict the computation to the content of this groupby line.
                                 This function must accept a single parameter, corresponding to the groupby value to compute the domain for.
                        - label_builder is a function to be called to compute a label for the groupby value, that will be shown as the line name
                                 in the UI. This ways, translatable labels and multi-values keys serialized to json can be fully supported.
        """
        return {}

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        """ To be overridden to add report-specific warnings in the warnings dictionary.
        When a root report defines something in this function, its variants without any custom handler will also call the root report's
        _customize_warnings function. This can hence be used to share warnings between all variants.

        Should only be used when necessary, _dynamic_lines_generator is preferred.
        """

    def _enable_export_buttons_for_common_vat_groups_in_branches(self, options):
        """ DEPRECATED: to be removed in master. Buttons are now set to 'branch_allowed' when needed in get_options() """
        pass


class AccountReportFileDownloadException(Exception):
    def __init__(self, errors, content=None):
        super().__init__()
        self.errors = errors
        self.content = content
