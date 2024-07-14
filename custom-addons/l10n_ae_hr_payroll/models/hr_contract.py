# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HRContract(models.Model):
    _inherit = "hr.contract"

    l10n_ae_housing_allowance = fields.Monetary(string="Housing Allowance")
    l10n_ae_transportation_allowance = fields.Monetary(string="Transportation Allowance")
    l10n_ae_other_allowances = fields.Monetary(string="Other Allowances")
    l10n_ae_number_of_days = fields.Integer(string="Number of Days",
                                            help="Number of days of basic salary to be added to the end of service provision per year")

    _sql_constraints = [
        ('l10n_ae_hr_payroll_number_of_days_constraint', 'CHECK(l10n_ae_number_of_days >= 0)',
         'Number of Days must be equal to or greater than 0')
    ]
