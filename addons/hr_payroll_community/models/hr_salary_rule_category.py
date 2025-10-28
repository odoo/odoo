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


class HrSalaryRuleCategory(models.Model):
    """Create new model for Salary Rule Category"""
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'

    name = fields.Char(required=True, translate=True, string="Name",
                       help="Hr Salary Rule Category Name")
    code = fields.Char(required=True, string="Code",
                       help="Hr Salary Rule Category Code")
    parent_id = fields.Many2one('hr.salary.rule.category',
                                string='Parent',
                                help="Linking a salary category to its parent"
                                     "is used only for the reporting purpose.")
    children_ids = fields.One2many('hr.salary.rule.category',
                                   'parent_id',
                                   string='Children',
                                   help="Choose Hr Salary Rule Category")
    note = fields.Text(string='Description',
                       help="Description for Salary Category")

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company.id
    )

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Function to add constrains for parent_id field"""
        if self._has_cycle():
            raise ValidationError(
                _('Error! You cannot create recursive '
                  'hierarchy of Salary Rule Category.'))
