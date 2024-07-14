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
            ('show_on_dashboard', '=', True),
        ], limit=1)

    def write(self, values):
        tax_closing_update_dependencies = ('account_tax_periodicity', 'account_tax_periodicity_reminder_day', 'account_tax_periodicity_journal_id.id')
        to_update = self.env['res.company']
        for company in self:
            if company.account_tax_periodicity_journal_id:

                need_tax_closing_update = any(
                    update_dep in values and company.mapped(update_dep)[0] != values[update_dep]
                    for update_dep in tax_closing_update_dependencies
                )

                if need_tax_closing_update:
                    to_update += company

        res = super().write(values)

        for update_company in to_update:
            update_company._update_tax_closing_after_periodicity_change()

        return res

    def _update_tax_closing_after_periodicity_change(self):
        self.ensure_one()

        vat_fiscal_positions = self.env['account.fiscal.position'].search([
            ('company_id', '=', self.id),
            ('foreign_vat', '!=', False),
        ])

        self._get_and_update_tax_closing_moves(fields.Date.today(), vat_fiscal_positions, include_domestic=True)

    def _get_and_update_tax_closing_moves(self, in_period_date, fiscal_positions=None, include_domestic=False):
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
        period_start, period_end = self._get_tax_closing_period_boundaries(in_period_date)
        activity_deadline = period_end + relativedelta(days=self.account_tax_periodicity_reminder_day)

        # Search for an existing tax closing move
        tax_closing_activity_type = self.env.ref('account_reports.tax_closing_activity_type', raise_if_not_found=False)
        tax_closing_activity_type_id = tax_closing_activity_type.id if tax_closing_activity_type else False

        all_closing_moves = self.env['account.move']
        for fpos in itertools.chain(fiscal_positions, [None] if include_domestic else []):

            tax_closing_move = self.env['account.move'].search([
                ('state', '=', 'draft'),
                ('company_id', '=', self.id),
                ('tax_closing_end_date', '>=', period_start),
                ('tax_closing_end_date', '<=', period_end),
                ('fiscal_position_id', '=', fpos.id if fpos else None),
            ])

            # This should never happen, but can be caused by wrong manual operations
            if len(tax_closing_move) > 1:
                if fpos:
                    error = _("Multiple draft tax closing entries exist for fiscal position %s after %s. There should be at most one. \n %s")
                    params = (fpos.name, period_start, tax_closing_move.mapped('display_name'))

                else:
                    error = _("Multiple draft tax closing entries exist for your domestic region after %s. There should be at most one. \n %s")
                    params = (period_start, tax_closing_move.mapped('display_name'))

                raise UserError(error % params)

            # Compute tax closing description
            ref = self._get_tax_closing_move_description(self.account_tax_periodicity, period_start, period_end, fpos)

            # Values for update/creation of closing move
            closing_vals = {
                'company_id': self.id,# Important to specify together with the journal, for branches
                'journal_id': self.account_tax_periodicity_journal_id.id,
                'date': period_end,
                'tax_closing_end_date': period_end,
                'fiscal_position_id': fpos.id if fpos else None,
                'ref': ref,
                'name': '/', # Explicitly set a void name so that we don't set the sequence for the journal and don't consume a sequence number
            }

            if tax_closing_move:
                # Update the next activity on the existing move
                for act in tax_closing_move.activity_ids:
                    if act.activity_type_id.id == tax_closing_activity_type_id:
                        act.write({'date_deadline': activity_deadline})

                tax_closing_move.write(closing_vals)
            else:
                # Create a new, empty, tax closing move
                tax_closing_move = self.env['account.move'].create(closing_vals)
                report, tax_closing_options = tax_closing_move._get_report_options_from_tax_closing_entry()

                if report._get_sender_company_for_export(tax_closing_options) == tax_closing_move.company_id:
                    # In case of VAT units or branches, only the main company's closing needs to receive the next activity
                    group_account_manager = self.env.ref('account.group_account_manager')
                    advisor_user = tax_closing_activity_type.default_user_id if tax_closing_activity_type else self.env['res.users']
                    if advisor_user and not (self in advisor_user.company_ids and group_account_manager in advisor_user.groups_id):
                        advisor_user = self.env['res.users']

                    if not advisor_user:
                        advisor_user = self.env['res.users'].search(
                            [('company_ids', 'in', self.ids), ('groups_id', 'in', group_account_manager.ids)],
                            limit=1, order="id ASC",
                        )

                    self.env['mail.activity'].with_context(mail_activity_quick_update=True).create({
                        'res_id': tax_closing_move.id,
                        'res_model_id': self.env['ir.model']._get_id('account.move'),
                        'activity_type_id': tax_closing_activity_type_id,
                        'date_deadline': activity_deadline,
                        'automated': True,
                        'user_id':  advisor_user.id or self.env.user.id
                    })

            all_closing_moves += tax_closing_move

        return all_closing_moves

    def _get_tax_closing_move_description(self, periodicity, period_start, period_end, fiscal_position):
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
                state_codes = [self.state_id.code] if vat_fpos_with_state_count else []

            if state_codes:
                region_string = " (%s - %s)" % (country_code, ', '.join(state_codes))
            else:
                region_string = " (%s)" % country_code
        else:
            # Don't add region information in case there is no foreign VAT fpos
            region_string = ''

        if periodicity == 'year':
            return _("Tax return for %s%s", period_start.year, region_string)
        elif periodicity == 'trimester':
            return _("Tax return for %s%s", format_date(self.env, period_start, date_format='qqq yyyy'), region_string)
        elif periodicity == 'monthly':
            return _("Tax return for %s%s", format_date(self.env, period_start, date_format='LLLL yyyy'), region_string)
        else:
            return _("Tax return from %s to %s%s", format_date(self.env, period_start), format_date(self.env, period_end), region_string)

    def _get_tax_closing_period_boundaries(self, date):
        """ Returns the boundaries of the tax period containing the provided date
        for this company, as a tuple (start, end).
        """
        self.ensure_one()
        period_months = self._get_tax_periodicity_months_delay()
        period_number = (date.month//period_months) + (1 if date.month % period_months != 0 else 0)
        end_date = date_utils.end_of(datetime.date(date.year, period_number * period_months, 1), 'month')
        start_date = end_date + relativedelta(day=1, months=-period_months + 1)

        return start_date, end_date

    def _get_tax_periodicity_months_delay(self):
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
        return periodicities[self.account_tax_periodicity]

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
