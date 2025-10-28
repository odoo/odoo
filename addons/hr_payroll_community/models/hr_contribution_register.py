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
from odoo import fields, models


class HrContributionRegister(models.Model):
    """Create a new model for adding fields."""
    _name = 'hr.contribution.register'
    _description = 'Contribution Register'

    company_id = fields.Many2one('res.company',string='Company',
                                 required=True,default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 help="Choose Partner for Register")
    name = fields.Char(required=True, string="Name",
                       help="Contribution Register Name")
    register_line_ids = fields.One2many('hr.payslip.line',
                                        'register_id',
                                        string='Register Line',
                                        readonly=True,
                                        help="Choose Payslip line")
    note = fields.Text(string='Description',
                       help="Set Description for Register")
