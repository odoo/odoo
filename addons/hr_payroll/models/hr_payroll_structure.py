#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPayrollStructure(models.Model):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """

    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'

    def _get_parent_id(self):
        return self.env['ir.model.data'].search([('model', '=', 'hr.payroll.structure'), ('name', '=', 'structure_base')], limit=1).res_id

    name = fields.Char(required=True)
    code = fields.Char('Reference', size=64, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, copy=False, default=lambda self: self.env.user.company_id)
    note = fields.Text('Description')
    parent_id = fields.Many2one('hr.payroll.structure', default=_get_parent_id, string='Parent')
    children_ids = fields.One2many('hr.payroll.structure', 'parent_id', 'Children', copy=True)
    rule_ids = fields.Many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', string='Salary Rules')

    @api.constrains('parent_id')
    def check_recursion(self):
        for structure in self:
            if not structure._check_recursion():
                raise ValidationError(
                    _('Error ! You cannot create a recursive Salary Structure.'))

    @api.multi
    def copy(self, default):
        self.ensure_one()
        return super(HrPayrollStructure, self).copy(default=dict(default, code=_("%s (copy)") % self.code))

    def get_all_rules(self):
        """
        :return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids._recursive_search_of_rules()
        return all_rules

    def _get_parent_structure(self):
        if not self:
            return []
        return self.mapped('parent_id')._get_parent_structure() + self.ids
