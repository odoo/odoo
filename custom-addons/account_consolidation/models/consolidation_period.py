# -*- coding: utf-8 -*-

import datetime
import json

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.misc import formatLang


class ConsolidationPeriod(models.Model):
    _name = "consolidation.period"
    _description = "Consolidation Period"
    _order = 'date_analysis_end desc, date_analysis_begin desc, id desc'
    _inherit = ['mail.thread']
    _rec_name = 'chart_name'

    def _get_default_date_analysis_begin(self):
        company = self.env.company
        return company.compute_fiscalyear_dates(datetime.date.today())['date_from'] if company else None

    chart_id = fields.Many2one('consolidation.chart', string="Consolidation", required=True, ondelete='cascade')
    chart_currency_id = fields.Many2one('res.currency', related="chart_id.currency_id")
    chart_name = fields.Char(related='chart_id.name', readonly=True)
    chart_account_ids_count = fields.Integer(related="chart_id.account_ids_count", string='# Accounts')
    display_dates = fields.Char(compute="_compute_display_dates")
    date_analysis_begin = fields.Date(string="Start Date", required=True, default=_get_default_date_analysis_begin)
    date_analysis_end = fields.Date(string="End Date")
    state = fields.Selection([('draft', 'Draft'), ('closed', 'Closed')], default='draft', required=True, tracking=True, copy=False)

    using_composition_ids = fields.One2many('consolidation.period.composition',
                                            'using_period_id')
    used_in_composition_ids = fields.One2many('consolidation.period.composition',
                                              'composed_period_id')

    company_period_ids = fields.One2many('consolidation.company_period', 'period_id', string="Company Periods", copy=False)
    journal_ids = fields.One2many('consolidation.journal', 'period_id', string="Journals")
    journal_ids_count = fields.Integer(compute="_compute_journal_ids_count", string="# Journals")
    color = fields.Integer('Color Index', readonly=False, related="chart_id.color", help='Used in the kanban view')
    dashboard_sections = fields.Text(compute="_compute_dashboard_sections")
    company_unmapped_accounts_counts = fields.Text(compute="_compute_company_unmapped_accounts_counts")

    # COMPUTEDS
    @api.depends('journal_ids')
    def _compute_dashboard_sections(self):
        """
        Compute the dashboard sections
        :return:
        """
        for record in self:
            domain = [('period_id', '=', record.id), ('group_id.show_on_dashboard', '=', True)]
            grouped_res = self.env['consolidation.journal.line']._read_group(domain, ['group_id'], ['amount:sum'])

            results = [
                {"name": group.name, "value": record._format_value(amount_sum)}
                for group, amount_sum in grouped_res
            ]
            record.dashboard_sections = json.dumps(results)

    @api.depends('journal_ids')
    def _compute_journal_ids_count(self):
        """
        Compute the amount of journal ids
        """
        for record in self:
            record.journal_ids_count = len(record.journal_ids)

    @api.depends('date_analysis_begin', 'date_analysis_end')
    def _compute_display_dates(self):
        """
        Compute the display dates
        """
        for record in self:
            begin = record.date_analysis_begin
            end = record.date_analysis_end if record.date_analysis_end else None
            if end is None or (begin.month == end.month and begin.year == end.year):
                record.display_dates = begin.strftime('%b %Y')
            else:
                if begin.year == end.year:
                    vals = (begin.strftime('%b'), end.strftime('%b %Y'))
                else:
                    vals = (begin.strftime('%b %Y'), end.strftime('%b %Y'))
                record.display_dates = '%s-%s' % vals

    @api.depends('company_period_ids')
    def _compute_company_unmapped_accounts_counts(self):
        """ Compute the number of company unmapped accounts
        """
        Account = self.env['account.account'].sudo()
        Company = self.env['res.company']
        for record in self:
            context = {'chart_id': record.chart_id.id}
            record_companies = set(record.company_period_ids.mapped('company_id.id'))
            user_companies = set(self.env.user.company_ids.ids)
            company_ids = tuple(record_companies.intersection(user_companies))

            domain = [
                ('company_id', 'in', company_ids),
                ('consolidation_account_chart_filtered_ids', '=', False),
                ('used', '=', True)
            ]
            values = Account.with_context(context)._read_group(domain, ['company_id'], ['__count'])

            results = [
                {"company_id": company.id, "name": company.name, "value": count}
                for company, count in values
            ]

            record.company_unmapped_accounts_counts = json.dumps(results)

    @api.onchange('date_analysis_end')
    def generate_guessed_company_periods(self):
        """
        Guess and generate company periods that user has a big chance to want to generate.
        """
        self.ensure_one()
        # once generated we don't do anything anymore as the user may have modified something
        if not self.company_period_ids:
            if self.date_analysis_begin and self.date_analysis_end and self.chart_id:
                company_period_values = self._get_company_periods_default_values()
                self.company_period_ids = [(0, 0, value) for value in company_period_values]

    # ORM OVERRIDES

    def copy(self, default=None):
        default = dict(default or {})
        default['date_analysis_begin'] = self.date_analysis_end + datetime.timedelta(days=1)
        default['date_analysis_end'] = None
        return super().copy(default)

    # ACTIONS

    def action_toggle_state(self):
        """
        Toggle the state of this analysis period
        """
        for record in self:
            record.write({'state': 'draft' if record.state == 'closed' else 'closed'})

    def action_close(self):
        """
        Put this analysis period in "closed" state
        """
        self.write({'state': 'closed'})
        return True

    def action_draft(self):
        """
        Put this analysis period in "draft" state
        """
        self.write({'state': 'draft'})
        return True

    def action_generate_journals(self):
        """
        (re)Generate all the journals linked to this analysis period
        :return: the action to execute
        """
        for record in self:
            if record.state == 'closed':
                continue

            record.check_access_rights('write')
            record.journal_ids.check_access_rights('unlink')
            record.journal_ids.check_access_rights('create')
            # Since he has the rights to be here, we can go sudo from here
            record = record.sudo()
            # unlink everything (only the ones auto-generated)
            journals_to_unlink = record.journal_ids.search([
                ('auto_generated', '=', True),
                ('period_id', '=', record.id)
            ])

            journals_to_unlink.line_ids.with_context(allow_unlink=True).unlink()
            journals_to_unlink.unlink()

            # (re)generate
            # 1 journal = 1 company
            record._generate_company_periods_journals()
            # 1 journal = 1 sub-consolidation
            record._generate_consolidations_journals()

    def action_open_mapping(self):
        """
        Open the mapping view for this analysis period and the company designated by the company_id value in context.
        The mapping view is the view allowing the user to map company accounts to consolidated accounts.
        :return: the action to execute
        """
        self.ensure_one()
        company_id = self.env.context.get('company_id')
        company = self.env['res.company'].browse(company_id)
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.account_mapping_action")
        action.update({
            'domain': [('company_id', '=', company_id)],
            # dont know why but it's needed otherwise "cannot read type of undefined" js error
            'views': [[self.env.ref('account_consolidation.account_mapping_tree').id, 'list']],
            'context': {
                'chart_id': self.chart_id.id,
                'company_id': company_id,
                'search_default_not_mapped': True,
                'search_default_used': True,
            },
            'display_name': _('Account Mapping: %s (for %s)', company.name, self.chart_id.name)
        })
        return action

    def action_open_form(self):
        """
        Open the form view this analysis period
        :return: the action to execute
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.consolidation_period_action")
        action.update({
            'views': [[False, 'form']],
            'res_id': self.id
        })
        return action

    def action_open_trial_balance_grid(self):
        """
        Open the trial balance grid for this analysis period
        :return: the action to execute
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'consolidation.journal.line',
            'view_mode': 'grid,graph,form',
            'views': [[False, 'grid'], [False, 'graph'], [False, 'form']],
            'domain': [('period_id', '=', self.id)],
            'context': {
                'default_period_id': self.id
            },
            'name': _('Trial Balance: %s', self.display_name),
            'search_view_id': [self.env.ref('account_consolidation.trial_balance_grid_search').id, 'search']
        }

    def action_open_chart_of_accounts(self):
        """
        Open the consolidated chart of accounts for this analysis period
        :return: the action to execute
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.consolidation_account_action")
        action['context'] = {
            'search_default_chart_id': self.chart_id.id,
            'default_chart_id': self.chart_id.id
        }
        return action

    def action_save_onboarding_create_step(self):
        """Validate the onboarding step of creating the first analysis period."""
        self.env['onboarding.onboarding.step'].action_validate_step(
            'account_consolidation.onboarding_onboarding_step_create_consolidation_period'
        )

    # PROTECTEDS

    def _get_company_periods_default_values(self):
        """
        Get company periods default values based on previous period or chart
        :return: a list of dict containing default values to use for newly creating company periods (one entry for each
        company period)
        :rtype: list
        """
        self.ensure_one()
        previous_analysis_period = self._get_previous_similiar_period()
        # Generate from companies linked to chart
        if not previous_analysis_period:
            company_period_values = self._get_company_periods_default_values_from_chart()
        # Generate from analysis periods linked to chart
        else:
            company_period_values = self._get_company_periods_default_values_from_period(previous_analysis_period)
        return company_period_values

    def _get_previous_similiar_period(self):
        """
        Get previous similar period of this analysis period
        :return: a recordset containing the previous similar period
        """
        self.ensure_one()
        if self.date_analysis_end:
            extra_domain = [('date_analysis_end', '<', self.date_analysis_end)]
        else:
            extra_domain = [('date_analysis_end', '<', self.date_analysis_begin)]

        previous_analysis_periods = self._get_similar_periods(extra_domain, limit=1)
        if not previous_analysis_periods or len(previous_analysis_periods) == 0:
            extra_domain = [('date_analysis_end', '!=', False)]
            previous_analysis_periods = self._get_similar_periods(extra_domain, limit=1)

        return previous_analysis_periods[0] if len(previous_analysis_periods) > 0 else False

    def _get_similar_periods(self, extra_domain= None, limit= None, order= "date_analysis_end desc"):
        """
        Get similar periods of this analysis period
        :param extra_domain: the extra domain to apply to the query made
        :type extra_domain: list
        :param limit: the limit amount of similar periods to retrieve
        :type limit: int
        :param order: the order in which the periods should be retrieved ('date_analysis_end desc' by default)
        :type order: str
        :return: a recordset containing the similar periods
        """
        self.ensure_one()
        domain = [('chart_id', '=', self.chart_id.id)]

        # Avoid to get current period in the results
        if self.id:
            domain.append(('id', '!=', self.id))

        # Allow extra filtering
        if extra_domain is not None:
            domain += extra_domain

        similar_analysis_periods = self.search(domain, order=order, limit=limit)
        return similar_analysis_periods

    def _get_company_periods_default_values_from_period(self, other_period):
        """
        Compute the company periods default values based on another period.
        :param other_period: the period to base on
        :return: a list of dict containing default values to use for newly creating company periods (one entry for each
        company period)
        :rtype: list
        """
        self.ensure_one()
        company_period_values = []
        for previous_company_period in other_period.company_period_ids:
            company_period_value = previous_company_period.copy_data()[0]
            del company_period_value['period_id']
            company_period_value.update({
                'date_company_begin': self.date_analysis_begin,
                'date_company_end': self.date_analysis_end,
            })
            company_period_values.append(company_period_value)
        return company_period_values

    def _get_company_periods_default_values_from_chart(self):
        """
        Compute the company periods default values based on chart
        :return: a list of dict containing default values to use for newly creating company periods (one entry for each
        company period)
        :rtype: list
        """
        self.ensure_one()
        company_period_values = []
        cp_fields = self.env['consolidation.company_period']._fields
        for company_id in self.chart_id.mapped('company_ids.id'):
            values = self.env['consolidation.company_period'].default_get(cp_fields)
            values.update({
                'chart_id': self.chart_id,
                'date_company_begin': self.date_analysis_begin,
                'date_company_end': self.date_analysis_end,
                'company_id': company_id,
            })
            company_period_values.append(values)
        return company_period_values

    def _generate_company_periods_journals(self):
        """
        (re)Generate the journals linked to this analysis period and coming from a linked company periods
        """
        self.ensure_one()
        for company_period in self.company_period_ids:
            company_period._generate_journal()

    def _generate_consolidations_journals(self):
        """
        (re)Generate the journals linked to this analysis period and coming from another analysis period (consolidation
        of consolidation)
        """
        self.ensure_one()
        for consolidation_composition in self.using_composition_ids:
            consolidation_composition._generate_journal()

    def _format_value(self, value, currency=False):
        """
        Format the value of a currency amount based on this analysis period. If no currency is given, this uses the
        chart currency to properly format the given value.
        :param value: the value to format
        :param currency: the currency to use
        :return: the formatted value
        """
        currency_id = currency or self.chart_id.currency_id
        if self.env.context.get('no_format'):
            return currency_id.round(value)
        if currency_id.is_zero(value):
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res


class ConsolidationPeriodComposition(models.Model):
    _name = "consolidation.period.composition"
    _description = "Consolidation Period Composition"

    composed_chart_currency_id = fields.Many2one('res.currency', string='Composed Consolidation Currency',
                                                 related="composed_period_id.chart_id.currency_id")
    composed_period_id = fields.Many2one('consolidation.period', ondelete="cascade",
                                                  string="Composed Analysis Period", required=True)
    using_period_id = fields.Many2one('consolidation.period', string="Analysis Period Using This", ondelete="cascade", required=True)
    using_chart_currency_id = fields.Many2one('res.currency',
                                              related="using_period_id.chart_id.currency_id")
    rate_consolidation = fields.Float(string="Consolidation Rate", help="Should be between 0 and 100 %", default=100,
                                      required=True)
    currency_rate = fields.Float(string="Currency Rate", default=1.0, digits=0,
                                 help="Currency rate from composed chart currency to using chart currency")
    currencies_are_different = fields.Boolean(compute='_compute_currencies_are_different', readonly=True)

    _sql_constraints = [
        ('_unique_composition', 'unique (composed_period_id, using_period_id)',
         "Two compositions of the same analysis period by the same analysis period cannot be created"),
    ]

    @api.constrains('composed_period_id', 'using_period_id')
    def _check_composed_period_id(self):
        for comp in self:
            if comp.composed_period_id == comp.using_period_id:
                raise ValidationError(_("The Composed Analysis Period must be different from the Analysis Period"))

    @api.depends('composed_period_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.composed_period_id.display_name

    def _generate_journal(self):
        """
        (Re)generate the journal representing this analysis period composition. Also (re)generate subsequent non-locked
        period journals.
        """
        self.ensure_one()
        # Delete previous journal
        journals = self.env['consolidation.journal'].search([
            ('composition_id', '=', self.id),
            ('period_id', '=', self.using_period_id.id)
        ])
        journals.line_ids.with_context(allow_unlink=True).unlink()
        journals.unlink()
        # update composed analysis period journals (recursive)
        self.composed_period_id.action_generate_journals()
        journal_lines_values = self._get_journal_lines_values()
        self.env['consolidation.journal'].create({
            'name': self.composed_period_id.chart_name,
            'auto_generated': True,
            'composition_id': self.id,
            'period_id': self.using_period_id.id,
            'chart_id': self.using_period_id.chart_id.id,
            'line_ids': [(0, 0, value) for value in journal_lines_values]
        })

    def _get_journal_lines_values(self):
        """
        Get all the journal line values in order to create them.
        :return: a list of dict containing values for journal lines creation
        """
        self.ensure_one()
        journal_lines_values = []
        for consolidation_account in self.using_period_id.chart_id.account_ids:
            amount = self._get_total_amount(consolidation_account)
            journal_lines_values.append({
                "account_id": consolidation_account.id,
                "amount": amount
            })
        return journal_lines_values

    # PROTECTEDS

    def _get_total_amount(self, consolidation_account):
        """
        Get the total amount for a given consolidation account for this composition. It :
        - sums the lines of composed period written in consolidation accounts related to consolidation account
        - apply the consolidation rate
        - apply the currency rate
        :param consolidation_account: the consolidation account
        :return: the total amount, with all rates applied
        :rtype: float
        """
        self.ensure_one()
        domain = [
            ('account_id.used_in_ids', '=', consolidation_account.id),
            ('period_id', '=', self.composed_period_id.id)
        ]
        amounts = self.env['consolidation.journal.line'].sudo()._read_group(domain, [], ['amount:sum'])
        amount = amounts[0][0]
        return (self.rate_consolidation / 100.0) * (amount * self.currency_rate)

    # COMPUTEDS

    @api.depends('composed_chart_currency_id', 'using_chart_currency_id')
    def _compute_currencies_are_different(self):
        """
        Compute if the currencies (the one from the chart and the one from the company) are different.
        """
        for record in self:
            record.currencies_are_different = record.composed_chart_currency_id != record.using_chart_currency_id

    @api.onchange('composed_chart_currency_id')
    def _onchange_composed_chart_currency_id(self):
        """
        Set the default rate to the current one between the two given currencies (composed chart and using chart one).
        """
        for record in self:
            if not record.currencies_are_different:
                record.currency_rate = 1.0
            elif record.composed_chart_currency_id and record.using_chart_currency_id:
                record.currency_rate = record._get_default_currency_rate()

    def _get_default_currency_rate(self):
        """
        Get the current currency rate between the two given currencies (composed chart and using chart one).
        :return: the current rate in the current company
        :rtype: float
        """
        self.ensure_one()
        from_currency = self.composed_chart_currency_id
        to_currency = self.using_chart_currency_id
        company = self.env.company
        return self.env['res.currency']._get_conversion_rate(from_currency, to_currency, company, datetime.datetime.now())


class ConsolidationCompanyPeriod(models.Model):
    _name = "consolidation.company_period"
    _description = "Consolidation Company Period"

    chart_id = fields.Many2one('consolidation.chart', related="period_id.chart_id", string="Chart")
    period_id = fields.Many2one('consolidation.period', string="Period", required=True,
                                ondelete="cascade")
    company_id = fields.Many2one('res.company', string="Company", required=True)
    company_name = fields.Char(related="company_id.name")
    date_company_begin = fields.Date(string="Start Date", required=True)
    date_company_end = fields.Date(string="End Date", required=True)

    currency_chart_id = fields.Many2one('res.currency', related="period_id.chart_id.currency_id",
                                        string="Consolidation Currency")
    currency_company_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Company Currency")
    currency_rate_avg = fields.Float(string="Average Currency Rate", default=1.0, digits=[12,12],
                                     help="How many units of company currency is needed to get 1 unit of chart currency")
    currency_rate_end = fields.Float(string="End Currency Rate", default=1.0, digits=[12,12],
                                     help="How many units of company currency is needed to get 1 unit of chart currency")
    currencies_are_different = fields.Boolean(compute='_compute_currencies_are_different', readonly=True)

    rate_control = fields.Float(string="Rate Control", help="Should be between 0 and 100 %", default=100, required=True)
    rate_ownership = fields.Float(string="Rate Ownership", help="Should be between 0 and 100 %", default=100,
                                  required=True)
    rate_consolidation = fields.Float(string="Consolidation Rate", help="Should be between 0 and 100 %", default=100,
                                      required=True)
    consolidation_method = fields.Selection([
        ('full', 'Full consolidation'),
        ('proportional', 'Proportional consolidation'),
        ('equity', 'Equity'),
        ('none', 'Not consolidated')], default='full', required=True)
    exclude_journal_ids = fields.Many2many('account.journal', string="Exclude Journals")
    conversion_rate = fields.Float(compute='_compute_conversion_rate')

    # COMPUTEDS
    @api.depends('currency_chart_id', 'currency_company_id')
    def _compute_currencies_are_different(self):
        """
        Compute if the currencies (the one from the chart and the one from the company) are different.
        """
        for record in self:
            record.currencies_are_different = record.currency_chart_id != record.currency_company_id

    @api.depends('chart_id.rate_ids.rate')
    @api.depends_context('date', 'company_id', 'chart_id')
    def _compute_conversion_rate(self):
        date = self.env.context.get('date') or fields.Date.context_today(self)
        company_id = self.env.context.get('company_id')
        chart_id = self.env.context.get('chart_id')
        self.conversion_rate = self.env['consolidation.rate'].get_rate_for(date, company_id, chart_id)

    # ORM OVERRIDES
    @api.depends('company_name', 'date_company_begin', 'date_company_end', 'period_id')
    def _compute_display_name(self):
        """
        Set the display name of the company period. It's based on the dates and the analysis period dates to avoid too
        much information to be uselessly shown.
        """
        for record in self:
            generic_name = record.company_name if record.company_name else '?'
            date_begin = record.date_company_begin if record.date_company_begin else '?'
            date_end = record.date_company_end if record.date_company_end else '?'
            ap = record.period_id
            date_analysis_begin = ap.date_analysis_begin if ap.date_analysis_begin else '?'
            date_analysis_end = ap.date_analysis_end if ap.date_analysis_end else '?'

            if date_analysis_begin == date_begin and date_analysis_end == date_end:
                record.display_name = generic_name
            elif date_begin.month == date_end.month and date_begin.year == date_end.year:
                record.display_name = '%s (%s)' % (generic_name, date_begin.strftime('%b %Y'))
            elif date_begin.year == date_end.year:
                record.display_name = '%s (%s-%s)' % (generic_name, date_begin.strftime('%b'), date_end.strftime('%b %Y'))
            else:
                record.display_name = '%s (%s-%s)' % (generic_name, date_begin.strftime('%b %Y'), date_end.strftime('%b %Y'))

    def _generate_journal(self):
        """
        Generate the journal representing this company_period.
        """
        self.ensure_one()
        journal_lines_values = self._get_journal_lines_values()
        self.env['consolidation.journal'].create({
            'name': _("%s Consolidated Accounting", self.company_name),
            'auto_generated': True,
            'company_period_id': self.id,
            'period_id': self.period_id.id,
            'line_ids': [(0, 0, value) for value in journal_lines_values],
            'chart_id': self.chart_id.id,
        })

    def _get_journal_lines_values(self):
        """
        Get all the journal line values in order to create them.
        :return: a list of dict containing values for journal lines creation
        :rtype: list
        """
        self.ensure_one()
        journal_lines_values = []
        historical_account_ids = self.period_id.chart_id.account_ids.filtered(lambda x: x.currency_mode == 'hist')
        non_hist_account_ids = self.period_id.chart_id.account_ids - historical_account_ids
        for consolidation_account in historical_account_ids:
            journal_lines_values += self._get_historical_journal_lines_values(consolidation_account)

        for consolidation_account in non_hist_account_ids:
            # Maybe there is a better way to group all move line ids and total balance by consolidation account
            currency_amount, move_lines_ids = self._get_total_balance_and_audit_lines(consolidation_account)
            amount = self._apply_rates(currency_amount, consolidation_account)
            journal_lines_values.append({
                "account_id": consolidation_account.id,
                "currency_amount": currency_amount,
                "amount": amount,
                'move_line_ids': [(6, 0, move_lines_ids)]
            })
        return journal_lines_values

    # PROTECTEDS

    def _get_total_balance_and_audit_lines(self, consolidation_account):
        """
        Get the total balance of all the move lines "linked" to this company and a given consolidation account
        :param consolidation_account: the consolidation account
        :return: the total balance as a float and the
        :rtype: tuple
        """
        self.ensure_one()
        domain = self._get_move_lines_domain(consolidation_account)
        res = self.env['account.move.line']._read_group(domain, [], ['balance:sum', 'id:array_agg'])
        return res[0]

    def _apply_rates(self, amount, consolidation_account):
        """
        Apply all the needed rates to an amount. Needed rates are :
        - consolidation rate, which is only based on this company period,
        - currency rate, which is computed based on given consolidation account currency mode and this company periods
        currency rates (only applied if currencies are different).
        :param amount: the amount to convert
        :type amount: float
        :param consolidation_account: the consolidation account
        :return: a float representing the appliance of all needed rate to given amount
        :rtype: float
        """
        self.ensure_one()
        if self.currency_chart_id != self.currency_company_id:
            amount = self._convert(amount, consolidation_account.currency_mode)
        return self._apply_consolidation_rate(amount)

    def _apply_historical_rates(self, move_line):
        """
        Apply all the needed rates to a move line using its historical rate. Needed rates are :
        - consolidation rate, which is only based on this company period,
        - currency rate, which is computed based on move line date
        :param move_line: the move line
        :return: a float representing the appliance of all needed rate to move line balance
        :rtype: float
        """
        self.ensure_one()
        rate = self.with_context(date=move_line.date, company_id=self.company_id.id, chart_id=self.chart_id.id).conversion_rate
        if rate:
            amount = move_line.balance * rate
        else:
            amount = move_line.balance
            currency = move_line.company_currency_id
            if currency != self.currency_chart_id:
                amount = currency._convert(amount, self.currency_chart_id, self.company_id, move_line.date)
        return self._apply_consolidation_rate(amount)

    def _get_historical_journal_lines_values(self, consolidation_account):
        """
        Get all the journal line values for a given consolidation account when using historical currency mode.
        :param consolidation_account: the consolidation account
        :return: a list of dict containing values for journal lines creation
        :rtype: list
        """
        self.ensure_one()
        domain = self._get_move_lines_domain(consolidation_account)
        move_lines = self.env['account.move.line'].search(domain)
        return [{"account_id": consolidation_account.id,
                 "currency_amount": move_line.balance,
                 "amount": self._apply_historical_rates(move_line),
                 'move_line_ids': [(6, 0, [move_line.id])]} for move_line in move_lines]

    def _get_move_lines_domain(self, consolidation_account):
        """
        Get the domain definition to get all the move lines "linked" to this company period and a given consolidation
        account. That means all the move lines that :
        - are in the right company,
        - are not in excluded journals,
        - are linked to a account.account which is mapped in the given consolidation account
        - have a date contained in the company period start and company period end.
        :param consolidation_account: the consolidation account
        :return: a domain definition to be use in search ORM method.
        """
        self.ensure_one()
        return [
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('journal_id', 'not in', self.mapped('exclude_journal_ids.id')),
            ('account_id.consolidation_account_ids', '=', consolidation_account.id),
            ('date', '<=', self.date_company_end),
            '|',
            ('date', '>=', self.date_company_begin),
            ('account_id.include_initial_balance', '=', True)
        ]

    def _convert(self, amount, mode):
        """
        Convert a given amount by using the right currency rate of the company period based on a given mode.
        :param amount: the amount to convert
        :type amount: float
        :param mode: the mode to use (should be "avg" or "end', all other values makes the method return amount
        unchanged.
        :type mode: str
        :return: the converted amount or amount if no currency_rate with the given mode has been found.
        :rtype: float
        """
        self.ensure_one()
        currency_rate = getattr(self, ('currency_rate_%s' % mode), False)
        # The stored $rate value is like this : 1 chart currency = $rate company currency
        # As we do the reversed operation, we need to divide by $rate
        if currency_rate:
            return amount / currency_rate
        return amount

    def _apply_consolidation_rate(self, amount):
        """
        Apply the consolidation rate of the company period to a given amount.
        :param amount: the amount
        :type amount: float
        :return: the computed amount
        """
        self.ensure_one()
        return (self.rate_consolidation / 100.0) * amount
