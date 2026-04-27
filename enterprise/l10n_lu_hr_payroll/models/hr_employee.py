# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_lu_tax_id_number = fields.Char(
        string="Tax Identification Number",
        groups="hr_payroll.group_hr_payroll_user",
        tracking=True)
    l10n_lu_tax_classification = fields.Selection([
        ('1', '1'),
        ('1a', '1a'),
        ('2', '2'),
        ('without', 'Without')],
        string="Tax Classification",
        default='1', store=True, readonly=False, required=True,
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_tax_rate_no_classification = fields.Float(
        string="Tax Rate",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_fd_daily = fields.Monetary(
        string="FD",
        help="Travel Expenses",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_fd_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fd",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_fd_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fd",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_ac_ae_daily = fields.Monetary(
        string="AC/AE",
        help="Spousal Deduction / Extra-professional Deduction",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ac_ae_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ac_ae",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ac_ae_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ac_ae",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_ce_daily = fields.Monetary(
        string="CE",
        help="Extraordinary Charges",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ce_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ce",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ce_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ce",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_ds_daily = fields.Monetary(
        string="DS",
        help="Special Expenses",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ds_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ds",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_ds_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_ds",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_fo_daily = fields.Monetary(
        string="FO",
        help="Obtaining Fees",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_fo_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fo",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_fo_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_fo",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_deduction_amd_daily = fields.Monetary(
        string="AMD",
        help="Sustainable Mobility Deduction",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_amd_monthly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_amd",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_deduction_amd_yearly = fields.Monetary(
        compute="_compute_l10n_lu_deduction_amd",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_package_ffo_daily = fields.Monetary(
        string="FFO",
        help="Obtaining Fees Package",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_package_ffo_monthly = fields.Monetary(
        compute="_compute_l10n_lu_package_ffo",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_package_ffo_yearly = fields.Monetary(
        compute="_compute_l10n_lu_package_ffo",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_package_fds_daily = fields.Monetary(
        string="FDS",
        help="Special Expenses Package",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_package_fds_monthly = fields.Monetary(
        compute="_compute_l10n_lu_package_fds",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_package_fds_yearly = fields.Monetary(
        compute="_compute_l10n_lu_package_fds",
        groups="hr_payroll.group_hr_payroll_user")

    l10n_lu_tax_credit_cis = fields.Boolean(
        string="CIS",
        help="Employee Tax Credit",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_tax_credit_cip = fields.Boolean(
        string="CIP",
        help="Retiree Tax Credit",
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_tax_credit_cim = fields.Boolean(
        string="CIM",
        help="Single-parent Tax Credit",
        groups="hr_payroll.group_hr_payroll_user")

    @api.depends('l10n_lu_deduction_fd_daily')
    def _compute_l10n_lu_deduction_fd(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_fd_monthly = employee.l10n_lu_deduction_fd_daily * days_per_month
            employee.l10n_lu_deduction_fd_yearly = employee.l10n_lu_deduction_fd_monthly * 12

    @api.depends('l10n_lu_deduction_ac_ae_daily')
    def _compute_l10n_lu_deduction_ac_ae(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_ac_ae_monthly = employee.l10n_lu_deduction_ac_ae_daily * days_per_month
            employee.l10n_lu_deduction_ac_ae_yearly = employee.l10n_lu_deduction_ac_ae_monthly * 12

    @api.depends('l10n_lu_deduction_ce_daily')
    def _compute_l10n_lu_deduction_ce(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_ce_monthly = employee.l10n_lu_deduction_ce_daily * days_per_month
            employee.l10n_lu_deduction_ce_yearly = employee.l10n_lu_deduction_ce_monthly * 12

    @api.depends('l10n_lu_deduction_ds_daily')
    def _compute_l10n_lu_deduction_ds(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_ds_monthly = employee.l10n_lu_deduction_ds_daily * days_per_month
            employee.l10n_lu_deduction_ds_yearly = employee.l10n_lu_deduction_ds_monthly * 12

    @api.depends('l10n_lu_deduction_fo_daily')
    def _compute_l10n_lu_deduction_fo(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_fo_monthly = employee.l10n_lu_deduction_fo_daily * days_per_month
            employee.l10n_lu_deduction_fo_yearly = employee.l10n_lu_deduction_fo_monthly * 12

    @api.depends('l10n_lu_deduction_amd_daily')
    def _compute_l10n_lu_deduction_amd(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_deduction_amd_monthly = employee.l10n_lu_deduction_amd_daily * days_per_month
            employee.l10n_lu_deduction_amd_yearly = employee.l10n_lu_deduction_amd_monthly * 12

    @api.depends('l10n_lu_package_ffo_daily')
    def _compute_l10n_lu_package_ffo(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_package_ffo_monthly = employee.l10n_lu_package_ffo_daily * days_per_month
            employee.l10n_lu_package_ffo_yearly = employee.l10n_lu_package_ffo_monthly * 12

    @api.depends('l10n_lu_package_fds_daily')
    def _compute_l10n_lu_package_fds(self):
        days_per_month = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_days_per_month', raise_if_not_found=False) or 25
        for employee in self:
            employee.l10n_lu_package_fds_monthly = employee.l10n_lu_package_fds_daily * days_per_month
            employee.l10n_lu_package_fds_yearly = employee.l10n_lu_package_fds_monthly * 12
