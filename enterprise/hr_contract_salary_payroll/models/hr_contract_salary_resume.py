# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractSalaryResume(models.Model):
    _inherit = 'hr.contract.salary.resume'

    def _get_available_fields(self):
        result = super()._get_available_fields()
        return result + [('BASIC', 'Basic'), ('SALARY', 'Salary'), ('GROSS', 'Taxable Salary'), ('NET', 'Net')]

    code = fields.Selection(_get_available_fields)
    value_type = fields.Selection(selection_add=[
        ('payslip', 'Payslip Value'),
        ('sum', )
    ], ondelete={'payslip': 'set default'})
