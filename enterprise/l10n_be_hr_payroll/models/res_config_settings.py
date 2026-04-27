# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_commission_on_target = fields.Float(
        string="Commission on Target",
        default_model="hr.contract")
    default_fuel_card = fields.Float(
        string="Fuel Card",
        default_model="hr.contract")
    default_representation_fees = fields.Float(
        string="Representation Fees",
        default_model="hr.contract")
    default_internet = fields.Float(
        string="Internet",
        default_model="hr.contract")
    default_mobile = fields.Float(
        string="Mobile",
        default_model="hr.contract")
    default_meal_voucher_amount = fields.Float(
        string="Meal Vouchers",
        default_model="hr.contract")
    default_eco_checks = fields.Float(
        string="Eco Vouchers",
        default_model="hr.contract")
    onss_company_id = fields.Char(
        related='company_id.onss_company_id',
        readonly=False)
    onss_registration_number = fields.Char(
        related='company_id.onss_registration_number',
        readonly=False)
    dmfa_employer_class = fields.Char(
        related='company_id.dmfa_employer_class',
        readonly=False)
    l10n_be_company_number = fields.Char(
        'Company Number',
        related='company_id.l10n_be_company_number',
        readonly=False)
    l10n_be_revenue_code = fields.Char(
        'Revenue Code',
        related='company_id.l10n_be_revenue_code',
        readonly=False)
    hospital_insurance_amount_child = fields.Float(
        string="Hospital Insurance Amount per Child",
        config_parameter='hr_contract_salary.hospital_insurance_amount_child')
    hospital_insurance_amount_adult = fields.Float(
        string="Hospital Insurance Amount per Adult",
        config_parameter='hr_contract_salary.hospital_insurance_amount_adult')
    default_l10n_be_canteen_cost = fields.Float(
        string="Canteen Cost",
        default_model="hr.contract")
    l10n_be_ffe_employer_type = fields.Selection(
        related='company_id.l10n_be_ffe_employer_type', string='Ffe Employer Type',
        readonly=False)
    onss_expeditor_number = fields.Char(
        related="company_id.onss_expeditor_number",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
    onss_certificate_id = fields.Many2one(
        related="company_id.onss_certificate_id",
        readonly=False)
    accident_insurance_name = fields.Char(
        related="company_id.accident_insurance_name",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
    accident_insurance_number = fields.Char(
        related="company_id.accident_insurance_number",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
