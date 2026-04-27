# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
import itertools

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import format_date


class ResCompany(models.Model):
    _inherit = "res.company"

    totals_below_sections = fields.Boolean(
        string='Add totals below sections',
        help='When ticked, totals and subtotals appear below the sections of the report.')
    account_tax_periodicity = fields.Selection([
        ('year', 'annually'),
        ('semester', 'semi-annually'),
        ('4_months', 'every 4 months'),
        ('trimester', 'quarterly'),
        ('2_months', 'every 2 months'),
        ('monthly', 'monthly')], string="Delay units", help="Periodicity", default='monthly', required=True)
    account_tax_periodicity_reminder_day = fields.Integer(string='Start from', default=7, required=True)
    account_tax_periodicity_journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type', '=', 'general')], check_company=True)
    account_revaluation_journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'general')], check_company=True)
    account_revaluation_expense_provision_account_id = fields.Many2one('account.account', string='Expense Provision Account', check_company=True)
    account_revaluation_income_provision_account_id = fields.Many2one('account.account', string='Income Provision Account', check_company=True)
    account_tax_unit_ids = fields.Many2many(string="Tax Units", comodel_name='account.tax.unit', help="The tax units this company belongs to.")
    account_representative_id = fields.Many2one('res.partner', string='Accounting Firm',
                                                help="Specify an Accounting Firm that will act as a representative when exporting reports.")
    account_display_representative_field = fields.Boolean(compute='_compute_account_display_representative_field')

    @api.depends('account_fiscal_country_id.code')
    def _compute_account_display_representative_field(self):
        country_set = self._get_countries_allowing_tax_representative()
        for record in self:
            record.account_display_representative_field = record.account_fiscal_country_id.code in country_set

    def _get_countries_allowing_tax_representative(self):
        """ Returns a set containing the country codes of the countries for which
        it is possible to use a representative to submit the tax report.
        This function is a hook that needs to be overridden in localisation modules.
        """
        return set()

    def _get_default_misc_journal(self):
        """ Returns a default 'miscellanous' journal to use for
        account_tax_periodicity_journal_id field. This is useful in case a
        CoA was already installed on the company at the time the module
        is installed, so that the field is set automatically when added."""
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self),
            ('type', '=', 'general'),
        ], limit=1)

    def _get_tax_closing_journal(self):
        journals = self.env['account.journal']
        for company in self:
            journals |= company.account_tax_periodicity_journal_id or company._get_default_misc_journal()

        return journals

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._initiate_account_onboardings()
        return companies

    def write(self, values):
        tax_closing_update_dependencies = ('account_tax_periodicity', 'account_tax_periodicity_journal_id.id')
        to_update = self.env['res.company']
        for company in self:
            if company._get_tax_closing_journal():
                need_tax_closing_update = any(
                    update_dep in values and company.mapped(update_dep)[0] != values[update_dep]
                    for update_dep in tax_closing_update_dependencies
                )

                if need_tax_closing_update:
                    to_update += company

        res = super().write(values)

        # Early return
        if not to_update:
            return res

        to_reset_closing_moves = self.env['account.move'].sudo().search([
            ('company_id', 'in', to_update.ids),
            ('tax_closing_report_id', '!=', False),
            ('state', '=', 'draft'),
        ])
        to_reset_closing_moves.button_cancel()
        misc_journals = self.env['account.journal'].sudo().search([
            *self.env['account.journal']._check_company_domain(to_update),
            ('type', '=', 'general'),
        ])
        to_reset_closing_reminder_activities = self.env['mail.activity'].sudo().search([
            ('res_id', 'in', misc_journals.ids),
            ('res_model_id', '=', self.env['ir.model']._get_id('account.journal')),
            ('activity_type_id', '=', self.env.ref('account_reports.tax_closing_activity_type').id),
            ('active', '=', True),
        ])
        to_reset_closing_reminder_activities.action_cancel()
        generic_tax_report = self.env.ref('account.generic_tax_report')

        # Create a new reminder
        # The user is unlikely to change the periodicity often and for multiple companies at once
        # So it is fair enough to make this that way as we are obliged to get the tax report for each company
        # And then loop over all the reports to get their period boudaries and look for activity
        for company in to_update:
            tax_reports = self.env['account.report'].search([
                ('availability_condition', '=', 'country'),
                ('country_id', 'in', company.account_enabled_tax_country_ids.ids),
                ('root_report_id', '=', generic_tax_report.id),
            ])
            if not tax_reports.filtered(lambda x: x.country_id == company.account_fiscal_country_id):
                tax_reports += generic_tax_report

            for tax_report in tax_reports:
                period_start, period_end = company._get_tax_closing_period_boundaries(fields.Date.today(), tax_report)
                activity = company._get_tax_closing_reminder_activity(tax_report.id, period_end)
                if not activity and self.env['account.move'].search_count([
                    ('date', '<=', period_end),
                    ('date', '>=', period_start),
                    ('tax_closing_report_id', '=', tax_report.id),
                    ('company_id', '=', company.id),
                    ('state', '=', 'posted')
                ]) == 0:
                    company._generate_tax_closing_reminder_activity(tax_report, period_end)

        hidden_tax_journals = self._get_tax_closing_journal().sudo().filtered(lambda j: not j.show_on_dashboard)
        if hidden_tax_journals:
            hidden_tax_journals.show_on_dashboard = True

        return res

    def _get_closing_report_for_tax_closing_move(self, report, fpos):
        closing_report = report

        if not closing_report.country_id and closing_report.root_report_id:
            # Fallback to root report if we're using a non-localized variant (typically the grouped tax reports)
            closing_report = closing_report.root_report_id

        target_country = (fpos and fpos.country_id) or self.env.company.account_fiscal_country_id
        country_variants = [variant for variant in (closing_report.root_report_id or closing_report).variant_report_ids if variant.country_id == target_country]
        if len(country_variants) > 1:
            # More than one national variant available: use the generic tax report
            closing_report = self.env.ref('account.generic_tax_report')
        elif country_variants and closing_report.country_id != target_country:
            # Only one national variant available: select it
            closing_report = country_variants[0]

        return closing_report

    def _get_and_update_tax_closing_moves(self, in_period_date, report, fiscal_positions=None, include_domestic=False):
        """ Searches for tax closing moves. If some are missing for the provided parameters,
        they are created in draft state. Also, existing moves get updated in case of configuration changes
        (closing journal or periodicity, for example). Note the content of these moves stays untouched.

        :param in_period_date: A date within the tax closing period we want the closing for.
        :param fiscal_positions: The fiscal positions we want to generate the closing for (as a recordset).
        :param include_domestic: Whether or not the domestic closing (i.e. the one without any fiscal_position_id) must be included

        :return: The closing moves, as a recordset.
        """
        self.ensure_one()

        if not fiscal_positions:
            fiscal_positions = []

        # Compute period dates depending on the date
        tax_closing_journal = self._get_tax_closing_journal()

        all_closing_moves = self.env['account.move']
        for fpos in itertools.chain(fiscal_positions, [False] if include_domestic else []):
            closing_report = self._get_closing_report_for_tax_closing_move(report, fpos)

            period_start, period_end = self._get_tax_closing_period_boundaries(in_period_date, closing_report)
            periodicity = self._get_tax_periodicity(closing_report)

            fpos_id = fpos.id if fpos else False
            tax_closing_move = self.env['account.move'].search([
                ('state', '=', 'draft'),
                ('company_id', '=', self.id),
                ('tax_closing_report_id', '=', closing_report.id),
                ('date', '>=', period_start),
                ('date', '<=', period_end),
                ('fiscal_position_id', '=', fpos.id if fpos else None),
            ])

            # This should never happen, but can be caused by wrong manual operations
            if len(tax_closing_move) > 1:
                if fpos:
                    error = _("Multiple draft tax closing entries exist for fiscal position %(position)s after %(period_start)s. There should be at most one. \n %(closing_entries)s",
                              position=fpos.name, period_start=period_start, closing_entries=tax_closing_move.mapped('display_name'))

                else:
                    error = _("Multiple draft tax closing entries exist for your domestic region after %(period_start)s. There should be at most one. \n %(closing_entries)s",
                              period_start=period_start, closing_entries=tax_closing_move.mapped('display_name'))

                raise UserError(error)

            # Compute tax closing description
            ref = _("%(report_label)s: %(period)s", report_label=self._get_tax_closing_report_display_name(closing_report), period=self._get_tax_closing_move_description(periodicity, period_start, period_end, fpos, closing_report))

            # Values for update/creation of closing move
            closing_vals = {
                'company_id': self.id,# Important to specify together with the journal, for branches
                'journal_id': tax_closing_journal.id,
                'date': period_end,
                'tax_closing_report_id': closing_report.id,
                'fiscal_position_id': fpos_id,
                'ref': ref,
                'name': '/', # Explicitly set a void name so that we don't set the sequence for the journal and don't consume a sequence number
            }

            if tax_closing_move:
                tax_closing_move.write(closing_vals)
            else:
                # Create a new, empty, tax closing move
                tax_closing_move = self.env['account.move'].create(closing_vals)

            # Create a reminder activity if it doesn't exist
            activity = self._get_tax_closing_reminder_activity(closing_report.id, period_end, fpos_id)
            tax_closing_options = tax_closing_move._get_tax_closing_report_options(tax_closing_move.company_id, tax_closing_move.fiscal_position_id, tax_closing_move.tax_closing_report_id, tax_closing_move.date)
            if not activity and closing_report._get_sender_company_for_export(tax_closing_options) == tax_closing_move.company_id:
                self._generate_tax_closing_reminder_activity(closing_report, period_end, fpos)

            all_closing_moves += tax_closing_move

        return all_closing_moves

    def _get_tax_closing_report_display_name(self, report):
        if report.get_external_id().get(report.id) in ('account.generic_tax_report', 'account.generic_tax_report_account_tax', 'account.generic_tax_report_tax_account'):
            return _("Tax return")

        return report.display_name

    def _generate_tax_closing_reminder_activity(self, report, date_in_period=None, fiscal_position=None):
        """
        Create a reminder on the current tax_closing_journal for a certain report with a fiscal_position or not if None.
        The reminder will target the period from which the date sits in
        """
        self.ensure_one()
        if not date_in_period:
            date_in_period = fields.Date.today()
        # Search for an existing tax closing move
        tax_closing_activity_type = self.env.ref('account_reports.tax_closing_activity_type')

        # Tax period
        period_start, period_end = self._get_tax_closing_period_boundaries(date_in_period, report)
        periodicity = self._get_tax_periodicity(report)
        activity_deadline = period_end + relativedelta(days=self.account_tax_periodicity_reminder_day)

        # Reminder title
        summary = _(
            "%(report_label)s: %(period)s",
            report_label=self._get_tax_closing_report_display_name(report),
            period=self._get_tax_closing_move_description(periodicity, period_start, period_end, fiscal_position, report)
        )

        activity_user = tax_closing_activity_type.default_user_id if tax_closing_activity_type else self.env['res.users']
        if activity_user and not (self in activity_user.company_ids and activity_user.has_group('account.group_account_manager')):
            activity_user = self.env['res.users']

        if not activity_user:
            activity_user = self.env['res.users'].search(
                [('company_ids', 'in', self.ids), ('groups_id', 'in', self.env.ref('account.group_account_manager').ids)],
                limit=1, order="id ASC",
            )

        self.env['mail.activity'].with_context(mail_activity_quick_update=True).create({
            'res_id': self._get_tax_closing_journal().id,
            'res_model_id': self.env['ir.model']._get_id('account.journal'),
            'activity_type_id': tax_closing_activity_type.id,
            'date_deadline': activity_deadline,
            'automated': True,
            'summary': summary,
            'user_id':  activity_user.id or self.env.user.id,
            'account_tax_closing_params': {
                'report_id': report.id,
                'tax_closing_end_date': fields.Date.to_string(period_end),
                'fpos_id': fiscal_position.id if fiscal_position else False,
            },
        })

    def _get_tax_closing_reminder_activity(self, report_id, period_end, fpos_id=False):
        self.ensure_one()
        tax_closing_activity_type = self.env.ref('account_reports.tax_closing_activity_type')
        return self._get_tax_closing_journal().activity_ids.filtered(
            lambda act: act.account_tax_closing_params and (act.activity_type_id == tax_closing_activity_type and act.account_tax_closing_params['report_id'] == report_id
                                                            and fields.Date.from_string(act.account_tax_closing_params['tax_closing_end_date']) == period_end
                                                            and act.account_tax_closing_params['fpos_id'] == fpos_id)
        )

    def _get_tax_closing_move_description(self, periodicity, period_start, period_end, fiscal_position, report):
        """ Returns a string description of the provided period dates, with the
        given tax periodicity.
        """
        self.ensure_one()

        foreign_vat_fpos_count = self.env['account.fiscal.position'].search_count([
            ('company_id', '=', self.id),
            ('foreign_vat', '!=', False)
        ])
        if foreign_vat_fpos_count:
            if fiscal_position:
                country_code = fiscal_position.country_id.code
                state_codes = fiscal_position.mapped('state_ids.code') if fiscal_position.state_ids else []
            else:
                # On domestic country
                country_code = self.account_fiscal_country_id.code

                # Only consider the state in case there are foreign VAT fpos on states in this country
                vat_fpos_with_state_count = self.env['account.fiscal.position'].search_count([
                    ('company_id', '=', self.id),
                    ('foreign_vat', '!=', False),
                    ('country_id', '=', self.account_fiscal_country_id.id),
                    ('state_ids', '!=', False),
                ])
                state_codes = [self.state_id.code] if self.state_id and vat_fpos_with_state_count else []

            if state_codes:
                region_string = " (%s - %s)" % (country_code, ', '.join(state_codes))
            else:
                region_string = " (%s)" % country_code
        else:
            # Don't add region information in case there is no foreign VAT fpos
            region_string = ''

        # Shift back to normal dates if we are using a start date so periods aren't broken
        start_day, start_month = self._get_tax_closing_start_date_attributes(report)
        if start_day != 1 or start_month != 1:
            return f"{format_date(self.env, period_start)} - {format_date(self.env, period_end)}{region_string}"

        if periodicity == 'year':
            return f"{period_start.year}{region_string}"
        elif periodicity == 'trimester':
            return f"{format_date(self.env, period_start, date_format='qqq yyyy')}{region_string}"
        elif periodicity == 'monthly':
            return f"{format_date(self.env, period_start, date_format='LLLL yyyy')}{region_string}"
        else:
            return f"{format_date(self.env, period_start)} - {format_date(self.env, period_end)}{region_string}"

    def _get_tax_closing_period_boundaries(self, date, report):
        """ Returns the boundaries of the tax period containing the provided date
        for this company, as a tuple (start, end).

        This function needs to stay consitent with the one inside Javascript in the filters for the tax report
        """
        self.ensure_one()
        period_months = self._get_tax_periodicity_months_delay(report)
        start_day, start_month = self._get_tax_closing_start_date_attributes(report)
        aligned_date = date + relativedelta(days=-(start_day - 1))  # we offset the date back from start_day amount of day - 1 so we can compute months periods aligned to the start and end of months
        year = aligned_date.year
        month_offset = aligned_date.month - start_month
        period_number = (month_offset // period_months) + 1

        # If the date is before the start date and start month of this year, this mean we are in the previous period
        # So the initial_date should be one year before and the period_number should be computed in reverse because month_offset is negative
        if date < datetime.date(date.year, start_month, start_day):
            year -= 1
            period_number = ((12 + month_offset) // period_months) + 1

        month_delta = period_number * period_months

        # We need to work with offsets because it handle automatically the end of months (28, 29, 30, 31)
        end_date = datetime.date(year, start_month, 1) + relativedelta(months=month_delta, days=start_day - 2)  # -1 because the first days is aldready counted and -1 because the first day of the next period must not be in this range
        start_date = datetime.date(year, start_month, 1) + relativedelta(months=month_delta - period_months, day=start_day)

        return start_date, end_date

    def _get_available_tax_unit(self, report):
        """
        Must ensures that report has a country_id to search for a tax unit

        :return: A recordset of available tax units for this report country_id and this company
        """
        self.ensure_one()
        return self.env['account.tax.unit'].search([
            ('company_ids', 'in', self.id),
            ('country_id', '=', report.country_id.id),
        ], limit=1)

    def _get_tax_periodicity(self, report):
        main_company = self
        if report.filter_multi_company == 'tax_units' and report.country_id and (tax_unit := self._get_available_tax_unit(report)):
            main_company = tax_unit.main_company_id

        return main_company.account_tax_periodicity

    def _get_tax_closing_start_date_attributes(self, report):
        if not report.tax_closing_start_date:
            start_year = fields.Date.start_of(fields.Date.today(), 'year')
            return start_year.day, start_year.month

        main_company = self
        if report.filter_multi_company == 'tax_units' and report.country_id and (tax_unit := self._get_available_tax_unit(report)):
            main_company = tax_unit.main_company_id

        start_date = report.with_company(main_company).tax_closing_start_date

        return start_date.day, start_date.month

    def _get_tax_periodicity_months_delay(self, report):
        """ Returns the number of months separating two tax returns with the provided periodicity
        """
        self.ensure_one()
        periodicities = {
            'year': 12,
            'semester': 6,
            '4_months': 4,
            'trimester': 3,
            '2_months': 2,
            'monthly': 1,
        }
        return periodicities[self._get_tax_periodicity(report)]

    def  _get_branches_with_same_vat(self, accessible_only=False):
        """ Returns all companies among self and its branch hierachy (considering children and parents) that share the same VAT number
        as self. An empty VAT number is considered as being the same as the one of the closest parent with a VAT number.

        self is always returned as the first element of the resulting recordset (so that this can safely be used to restore the active company).

        Example:
        - main company ; vat = 123
            - branch 1
                - branch 1_1
            - branch 2 ; vat = 456
                - branch 2_1 ; vat = 789
                - branch 2_2

        In this example, the following VAT numbers will be considered for each company:
        - main company: 123
        - branch 1: 123
        - branch 1_1: 123
        - branch 2: 456
        - branch 2_1: 789
        - branch 2_2: 456

        :param accessible_only: whether the returned companies should exclude companies that are not in self.env.companies
        """
        self.ensure_one()

        current = self.sudo()
        same_vat_branch_ids = [current.id] # Current is always available
        current_strict_parents = current.parent_ids - current
        if accessible_only:
            candidate_branches = current.root_id._accessible_branches()
        else:
            candidate_branches = self.env['res.company'].sudo().search([('id', 'child_of', current.root_id.ids)])

        current_vat_check_set = {current.vat} if current.vat else set()
        for branch in candidate_branches - current:
            parents_vat_set = set(filter(None, (branch.parent_ids - current_strict_parents).mapped('vat')))
            if parents_vat_set == current_vat_check_set:
                # If all the branches between the active company and branch (both included) share the same VAT number as the active company,
                # we want to add the branch to the selection.
                same_vat_branch_ids.append(branch.id)

        return self.browse(same_vat_branch_ids)
