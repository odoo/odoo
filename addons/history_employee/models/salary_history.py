# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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


class SalaryHistory(models.Model):
    """Model  for tracking salary history information."""
    _name = 'salary.history'
    _description = 'Salary History'
    _rec_name = 'employee_name'

    employee = fields.Char(string='Employee ID',
                           help="ID of the employee associated with the salary "
                                "history record.")
    employee_name = fields.Char(string='Employee Name',
                                help="Name of the employee whose salary history"
                                     " has being updated.")
    updated_date = fields.Date(string='Updated On',
                               help="Date when the salary was updated.")
    current_value = fields.Char(string='Current Salary',
                                help="Updated salary amount.")
