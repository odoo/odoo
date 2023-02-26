# -*- coding: utf-8 -*-

from odoo import fields, models


class SalaryStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    max_percent = fields.Integer(string='Max.Salary Advance Percentage', help="Maximum salary advance percentage")
    advance_date = fields.Integer(string='Salary Advance-After days', help="Salary advance after days")

