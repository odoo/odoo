# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import SUNDAY
from dateutil.rrule import rrule, DAILY, MONTHLY
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_lu_month_taxable_days = fields.Float(compute='_compute_taxable_days')
    l10n_lu_period_taxable_days = fields.Float(compute='_compute_taxable_days')
    l10n_lu_effective_taxable_days = fields.Float(compute='_compute_taxable_days')
    l10n_lu_is_monthly = fields.Boolean(compute='_compute_taxable_days')

    l10n_lu_presence_prorata = fields.Float(compute='_compute_prorated_wage')
    l10n_lu_prorated_wage = fields.Float(compute='_compute_prorated_wage')

    l10n_lu_tax_id_number = fields.Char(
        compute="_compute_l10n_lu_tax_id_number", store=True, readonly=False)
    l10n_lu_tax_classification = fields.Selection([
        ('1', '1'),
        ('1a', '1a'),
        ('2', '2'),
        ('without', 'Without')],
        compute='_compute_l10n_lu_tax_classification', store=True, readonly=False)
    l10n_lu_tax_rate_no_classification = fields.Float(
        compute="_compute_l10n_lu_tax_id_number", store=True, readonly=False)

    l10n_lu_deduction_fd_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fd_daily", store=True, readonly=False)
    l10n_lu_deduction_ac_ae_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ac_ae_daily", store=True, readonly=False)
    l10n_lu_deduction_ce_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ce_daily", store=True, readonly=False)
    l10n_lu_deduction_ds_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ds_daily", store=True, readonly=False)
    l10n_lu_deduction_fo_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fo_daily", store=True, readonly=False)
    l10n_lu_deduction_amd_daily = fields.Monetary(
        compute="_compute_l10n_lu_deduction_amd_daily", store=True, readonly=False)

    l10n_lu_package_ffo_daily = fields.Monetary(
        compute="_compute_l10n_lu_package_ffo_daily", store=True, readonly=False)
    l10n_lu_package_fds_daily = fields.Monetary(
        compute="_compute_l10n_lu_package_fds_daily", store=True, readonly=False)

    l10n_lu_tax_credit_cis = fields.Boolean(
        compute="_compute_l10n_lu_tax_credit_cis", store=True, readonly=False)
    l10n_lu_tax_credit_cip = fields.Boolean(
        compute="_compute_l10n_lu_tax_credit_cip", store=True, readonly=False)
    l10n_lu_tax_credit_cim = fields.Boolean(
        compute="_compute_l10n_lu_tax_credit_cim", store=True, readonly=False)

    @api.depends('date_from', 'date_to')
    def _compute_taxable_days(self):
        for payslip in self:
            taxable_scale_days = payslip._rule_parameter('l10n_lu_days_per_month')
            if payslip.company_id.country_id.code != "LU":
                continue
            start_month = payslip.date_from + relativedelta(day=1)
            end_month = payslip.date_to + relativedelta(day=1, months=1, days=-1)
            period_taxable_days = 0
            month_taxable_days = 0
            date_to = payslip.date_to
            if payslip.contract_id.date_end and payslip.contract_id.date_end < date_to:
                date_to = payslip.contract_id.date_end
            for d in rrule(DAILY, dtstart=start_month, until=end_month):
                if d.weekday() != SUNDAY:
                    month_taxable_days += 1
                    if payslip.date_from <= d.date() <= date_to:
                        period_taxable_days += 1

            payslip.l10n_lu_period_taxable_days = period_taxable_days
            payslip.l10n_lu_month_taxable_days = month_taxable_days
            payslip.l10n_lu_is_monthly = period_taxable_days >= taxable_scale_days
            if payslip.l10n_lu_is_monthly:
                payslip.l10n_lu_effective_taxable_days = taxable_scale_days
            else:
                payslip.l10n_lu_effective_taxable_days = taxable_scale_days / month_taxable_days * period_taxable_days

    @api.depends('date_from', 'date_to', 'employee_id', 'worked_days_line_ids')
    def _compute_prorated_wage(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" and payslip.contract_id.wage_type == "hourly":
                continue
            payslip.l10n_lu_presence_prorata = payslip._get_month_presence_prorata()
            payslip.l10n_lu_prorated_wage = payslip.contract_id.l10n_lu_indexed_wage * payslip.l10n_lu_presence_prorata

    @api.depends('employee_id.l10n_lu_tax_id_number', 'state')
    def _compute_l10n_lu_tax_id_number(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_id_number = payslip.employee_id.l10n_lu_tax_id_number

    @api.depends('employee_id.l10n_lu_tax_classification', 'state')
    def _compute_l10n_lu_tax_classification(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_classification = payslip.employee_id.l10n_lu_tax_classification

    @api.depends('employee_id.l10n_lu_tax_rate_no_classification', 'state')
    def _compute_l10n_lu_tax_rate_no_classification(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_rate_no_classification = payslip.employee_id.l10n_lu_tax_rate_no_classification

    @api.depends('employee_id.l10n_lu_deduction_fd_daily', 'state')
    def _compute_l10n_lu_deduction_fd_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_fd_daily = payslip.employee_id.l10n_lu_deduction_fd_daily

    @api.depends('employee_id.l10n_lu_deduction_ac_ae_daily', 'state')
    def _compute_l10n_lu_deduction_ac_ae_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_ac_ae_daily = payslip.employee_id.l10n_lu_deduction_ac_ae_daily

    @api.depends('employee_id.l10n_lu_deduction_ce_daily', 'state')
    def _compute_l10n_lu_deduction_ce_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_ce_daily = payslip.employee_id.l10n_lu_deduction_ce_daily

    @api.depends('employee_id.l10n_lu_deduction_ds_daily', 'state')
    def _compute_l10n_lu_deduction_ds_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_ds_daily = payslip.employee_id.l10n_lu_deduction_ds_daily

    @api.depends('employee_id.l10n_lu_deduction_fo_daily', 'state')
    def _compute_l10n_lu_deduction_fo_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_fo_daily = payslip.employee_id.l10n_lu_deduction_fo_daily

    @api.depends('employee_id.l10n_lu_deduction_amd_daily', 'state')
    def _compute_l10n_lu_deduction_amd_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_deduction_amd_daily = payslip.employee_id.l10n_lu_deduction_amd_daily

    @api.depends('employee_id.l10n_lu_package_ffo_daily', 'state')
    def _compute_l10n_lu_package_ffo_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_package_ffo_daily = payslip.employee_id.l10n_lu_package_ffo_daily

    @api.depends('employee_id.l10n_lu_package_fds_daily', 'state')
    def _compute_l10n_lu_package_fds_daily(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_package_fds_daily = payslip.employee_id.l10n_lu_package_fds_daily

    @api.depends('employee_id.l10n_lu_tax_credit_cis', 'state')
    def _compute_l10n_lu_tax_credit_cis(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_credit_cis = payslip.employee_id.l10n_lu_tax_credit_cis

    @api.depends('employee_id.l10n_lu_tax_credit_cip', 'state')
    def _compute_l10n_lu_tax_credit_cip(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_credit_cip = payslip.employee_id.l10n_lu_tax_credit_cip

    @api.depends('employee_id.l10n_lu_tax_credit_cim', 'state')
    def _compute_l10n_lu_tax_credit_cim(self):
        for payslip in self:
            if payslip.company_id.country_id.code != "LU" or payslip.state in ['paid', 'done']:
                continue
            payslip.l10n_lu_tax_credit_cim = payslip.employee_id.l10n_lu_tax_credit_cim

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(payslip.company_id.country_id.code == "LU" and payslip.date_from.month != payslip.date_to.month for payslip in self):
            raise ValidationError(_("Payslip 'Date From' and 'Date To' should be in the same month."))
        super()._check_dates()

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_lu_hr_payroll', [
                'data/rule_parameters/contributions_rules_data.xml',
                'data/rule_parameters/employer_rules_data.xml',
                'data/rule_parameters/general_rules_data.xml',
                'data/rule_parameters/tax_credit_rules_data.xml',
                'data/rule_parameters/withholding_taxes_rules_data.xml',
                'data/hr_work_entry_type_data.xml',
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_work_entry_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_payslip_input_type_data.xml',
                'data/hr_holidays_data.xml',
                'data/hr_payroll_dashboard_warning_data.xml',
            ])]

    def _get_rule_name(self, localdict, rule, employee_lang):
        if rule.struct_id.country_id.code == 'LU':
            if rule.struct_id.code == 'LUX_MONTHLY':
                if rule.code == 'GROSS':
                    return _('Total Gross')
                elif rule.code == 'NET':
                    return _('Net To Pay')
            if rule.struct_id.code in ['LUX_GRATIFICATION', 'LUX_13TH_MONTH']:
                if rule.code == 'BASIC':
                    return _('Basic Gratification')
                elif rule.code == 'GROSS':
                    return _('Gross Gratification')
                elif rule.code == 'NET':
                    return _('Net Gratification')
        return super()._get_rule_name(localdict, rule, employee_lang)

    def _get_paid_amount(self):
        self.ensure_one()
        if self.struct_id.country_id.code == 'LU' and self.struct_id.code == 'LUX_MONTHLY' and self.contract_id.wage_type == 'monthly':
            return self.l10n_lu_prorated_wage
        elif self.struct_id.country_id.code == 'LU' and self.struct_id.code == 'LUX_13TH_MONTH':
            return self._get_paid_amount_l10n_lu_13th_month()
        return super()._get_paid_amount()

    def _get_month_presence_prorata(self):
        self.ensure_one()
        worked_hours = self._get_paid_worked_days_line_number_of_hours()

        # YTI TOFIX: Localise start_date/end_date according to employee.tz
        start_date = self.date_from + relativedelta(day=1, hour=0, minute=0, second=0)
        end_date = self.date_to + relativedelta(day=1, months=1, days=-1, hour=23, minute=59, second=59)
        total_hours = self.employee_id.resource_calendar_id.get_work_hours_count(start_date, end_date)
        return min(1, worked_hours / total_hours)

    def _get_yearly_simulated_gross(self, current_gross=0):
        taxable_scale_days = self._rule_parameter('l10n_lu_days_per_month')
        total_gross = current_gross
        if not self.l10n_lu_is_monthly:
            total_gross *= taxable_scale_days / self.l10n_lu_period_taxable_days

        n_months = 0
        for start_month in rrule(MONTHLY, dtstart=self.date_from + relativedelta(day=1, month=1), until=self.date_to + relativedelta(day=1, month=1, years=1, days=-1)):
            end_month = start_month + relativedelta(months=1, days=-1)
            month_payslips = self.env['hr.payslip'].search([
                ('date_from', '>=', start_month),
                ('date_to', '<=', end_month),
                ('employee_id', '=', self.employee_id.id),
                ('id', '!=', self.id),
                ('state', 'in', ['paid', 'done'])
            ])

            for slip in month_payslips:
                if slip.l10n_lu_is_monthly:
                    total_gross += slip.gross_wage
                else:
                    total_gross += slip.gross_wage * taxable_scale_days / slip.l10n_lu_period_taxable_days

            if month_payslips or start_month.date() <= self.date_from <= end_month.date():
                n_months += 1
        return total_gross / n_months * 12

    def _get_paid_amount_l10n_lu_13th_month(self):
        return self._get_yearly_simulated_gross() / 12
