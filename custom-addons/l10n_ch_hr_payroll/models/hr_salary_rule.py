# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    l10n_ch_code = fields.Char(string="External Code")

    # 1/ AVS - Old Age & Survivor's Insurance, Disability Insurance & Loss of Earnings
    # AHV - Acronym used on a German Payslip
    # AVS - Acronym used on a French & Italian Payslip

    # 2/ AC - Unemployment Insurance
    # ALV - Acronym used on a German Payslip
    # AC - Acronym used on a French Payslip
    # AD - Acronym used on an Italian Payslip
    l10n_ch_ac_included = fields.Boolean(
        string="AVS/AC Included", help="Whether the amount is included in the basis to compute the retirement/unemployement deduction")

    # YTI TODO MASTER: FIELD TO DROP
    # 3/ Compl. AC - Additional Unemployment Insurance
    # ALVZ - Acronym used on a German Payslip
    # Compl. AC - Acronym used on a French Payslip
    # Compl. AD - Acronym used on an Italian Payslip
    l10n_ch_comp_ac_included = fields.Boolean(
        string="Complementary AC Included", help="Whether the amount is included in the basis to compute the additional retirement/unemployement deduction")

    # YTI TODO MASTER RENAME INTO l10n_ch_laa_included
    # 3/ LAA - AANP - Accident Insurance (Occupational & Non Occupational Rates)
    # NBUV - Acronym used on a German Payslip
    # AANP - Acronym used on a French Payslip
    # AINP - Acronym used on an Italian Payslip
    l10n_ch_aanp_included = fields.Boolean(
        string="AANP Included", help="Whether the amount is included in the basis to compute the accident insurance deduction")

    # 5/ IJM - Daily Sickness Insurance
    # KTG - Acronym used on a German Payslip
    # IJM - Acronym used on a French Payslip
    # IGM - Acronym used on an Italian Payslip
    l10n_ch_ijm_included = fields.Boolean(
        string="IJM Included", help="Whether the amount is included in the basis to compute the daily sick pay deduction")

    # 6/ LPP - Pension
    # BVG - Acronym used on a German Payslip
    # LPP - Acronym used on a French Payslip
    # LPP - Acronym used on an Italian Payslip

    # 7/ Withholding Tax or "Tax at Source"
    l10n_ch_source_tax_included = fields.Boolean(
        string="Source Tax Included", help="Whether the amount is included in the basis to compute the daily sick pay deduction")

    l10n_ch_wage_statement = fields.Char(string="Wage Statement")
    l10n_ch_yearly_statement = fields.Char(string="Yearly Statement")
    # YTI TODO: Drop field
    l10n_ch_october_statement = fields.Char(string="October Statement")
    l10n_ch_13th_month_included = fields.Boolean(string="13th Month Included")
