# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractSalaryResumeCategory(models.Model):
    _name = 'hr.contract.salary.resume.category'
    _description = 'Salary Package Resume Category'
    _order = 'sequence'

    name = fields.Char()
    sequence = fields.Integer(default=100)
    periodicity = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')])


class HrContractSalaryResume(models.Model):
    _name = 'hr.contract.salary.resume'
    _description = 'Salary Package Resume'
    _order = 'sequence'

    def _get_available_fields(self):
        return [(field, description['string']) for field, description in self.env['hr.contract'].fields_get().items()]

    name = fields.Char()
    sequence = fields.Integer(default=100)
    value_type = fields.Selection([
        ('fixed', 'Fixed Value'),
        ('contract', 'Contract Value'),
        ('sum', 'Sum of Benefits Values'),
        ('monthly_total', 'Monthly Total')], required=True, default='fixed',
        help='Pick how the value of the information is computed:\n'
             'Fixed value: Set a determined value static for all links\n'
             'Contract value: Get the value from a field on the contract record\n'
             'Payslip value: Get the value from a field on the payslip record\n'
             'Sum of Benefits value: You can pick in all benefits and compute a sum of them\n'
             'Monthly Total: The information will be a total of all the informations in the category Monthly Benefits')
    benefit_ids = fields.Many2many('hr.contract.salary.benefit')
    code = fields.Selection(_get_available_fields)
    fixed_value = fields.Float()
    category_id = fields.Many2one('hr.contract.salary.resume.category', required=True, help='Pick a category to display this information')
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    impacts_monthly_total = fields.Boolean(help="If checked, the value of this information will be computed in all information set as Monthly Total")
    uom = fields.Selection([
        ('days', 'Days'),
        ('percent', 'Percent'),
        ('currency', 'Currency')], string="Unit of Measure", default='currency')
    active = fields.Boolean('Active', default=True)
