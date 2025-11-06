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
from odoo import api, fields, models


class ResUsers(models.Model):
    """ Inherited class of res user to override the create function"""
    _inherit = 'res.users'

    employee_id = fields.Many2one('hr.employee',
                                  string='Related Employee',
                                  ondelete='restrict', auto_join=True,
                                  help='Related employee based on the'
                                       ' data of the user')

    @api.model_create_multi
    def create(self, vals_list):
        """Overrides the default 'create' method to create an employee record
        when a new user is created.

        Note: This method will NOT auto-create an employee if:
        - create_employee_id is set (user being created FROM an existing employee)
        - create_employee flag is explicitly False
        - An employee already exists for this user in the current company
        """
        result = super(ResUsers, self).create(vals_list)

        for user, vals in zip(result, vals_list):
            # Skip employee creation if user is being linked to an existing employee
            # (this happens when clicking "Create User" from an employee form)
            if vals.get('create_employee_id'):
                continue

            # Skip if create_employee flag is explicitly False
            if vals.get('create_employee') is False:
                continue

            # Check if an employee already exists for this user in the current company
            existing_employee = self.env['hr.employee'].sudo().search([
                ('user_id', '=', user.id),
                ('company_id', '=', user.company_id.id)
            ], limit=1)

            if existing_employee:
                # Link to existing employee instead of creating a new one
                user.employee_id = existing_employee
            else:
                # Create a new employee only if one doesn't exist
                user.employee_id = self.env['hr.employee'].sudo().create({
                    'name': user.name,
                    'user_id': user.id,
                    'company_id': user.company_id.id,
                })

        return result
