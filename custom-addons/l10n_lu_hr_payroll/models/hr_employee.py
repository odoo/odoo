# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_lu_tax_classification = fields.Selection(
        [('1', '1'),
         ('1a', '1a'),
         ('2', '2')
        ], string="Tax Classification",
        compute='_compute_l10n_lu_tax_classification', store=True, readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_travel_expense = fields.Float(
        "Travel Expense Monthly Compensation", groups="hr_payroll.group_hr_payroll_user")
    l10n_lu_tax_card_number = fields.Char("Tax Card Number", groups="hr_payroll.group_hr_payroll_user")

    @api.depends('children', 'marital', 'birthday')
    def _compute_l10n_lu_tax_classification(self):
        def _get_age_on_2017(employee):
            start = employee.birthday or date.today()
            end = date(2017, 1, 1)
            age = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
            return age

        # Source: https://impotsdirects.public.lu/dam-assets/fr/baremes/recueil-bareme-01012017.pdf
        for employee in self:
            if employee.company_country_code != 'LU':
                continue
            result = ''
            if employee.marital == 'single':
                if not employee.children:
                    result = '1'
                elif employee.children:
                    result = '1a'
                if _get_age_on_2017(employee) >= 64:
                    result = '1a'
            elif employee.marital in ['married', 'cohabitant']:
                if not employee.children:
                    result = '2'
                elif employee.children:
                    result = '2'
                if _get_age_on_2017(employee) >= 64:
                    result = '2'
            elif employee.marital == 'divorced':
                if not employee.children:
                    result = '1'
                elif employee.children:
                    result = '1a'
                if _get_age_on_2017(employee) >= 64:
                    result = '1a'
            elif employee.marital == 'widower':
                if not employee.children:
                    result = '1a'
                elif employee.children:
                    result = '1a'
                if _get_age_on_2017(employee) >= 64:
                    result = '1a'
            if result and result != employee.l10n_lu_tax_classification:
                employee.l10n_lu_tax_classification = result
