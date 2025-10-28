# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
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

    @api.model
    def _get_parent(self):
        """Function for return parent."""
        return self.env.ref('hr_payroll_community.structure_base', False)

    name = fields.Char(required=True, string="Name",
                       help="Name for Payroll Structure")
    code = fields.Char(string='Reference', required=True,
                       help="Code for Payroll Structure")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company.id
    )
    note = fields.Text(string='Description',
                       help="Description for Payroll Structure")
    parent_id = fields.Many2one('hr.payroll.structure',
                                string='Parent',
                                default=_get_parent,
                                help="Choose Payroll Structure")
    children_ids = fields.One2many('hr.payroll.structure',
                                   'parent_id',
                                   string='Children', copy=True,
                                   help="Choose Payroll Structure")
    rule_ids = fields.Many2many('hr.salary.rule',
                                'hr_structure_salary_rule_rel',
                                'struct_id',
                                'rule_id', string='Salary Rules',
                                help="Choose Salary Rule")

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Function _has_cycle for check parent in Payroll Structure"""
        if self._has_cycle():
            raise ValidationError(
                _('You cannot create a recursive salary structure.'))

    def copy(self, default=None):
        """Function for return Payroll Structure"""
        self.ensure_one()
        default = dict(default or {}, code=_("%s (copy)") % (self.code))
        return super(HrPayrollStructure, self).copy(default)

    def get_all_rules(self):
        """
        @return: returns a list of tuple (id, sequence) of rules that are maybe
        to apply
        """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids._recursive_search_of_rules()
        return all_rules

    def _get_parent_structure(self):
        """Function for getting Parent Structure"""
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_structure()
        return parent + self
