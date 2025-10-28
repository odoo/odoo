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
from odoo import fields, models, _


class HrEmployee(models.Model):
    """ Inherited model 'hr.employee' with additional
    fields and methods related to announcements."""
    _inherit = 'hr.employee'

    announcement_count = fields.Integer(compute='_compute_announcement_count',
                                        string='# Announcements',
                                        help="Count of Announcements")

    def _compute_announcement_count(self):
        """ Compute announcement count for an employee """
        for employee in self:
            announcement_ids_general = self.env[
                'hr.announcement'].sudo().search_count(
                [('is_announcement', '=', True),
                 ('state', '=', 'approved'),
                 ('date_start', '<=', fields.Date.today())])
            announcement_ids_emp = (self.env['hr.announcement'].
            sudo().search_count(
                [('employee_ids', 'in', self.id),
                 ('state', '=', 'approved'),
                 ('date_start', '<=', fields.Date.today())]))
            announcement_ids_dep = (self.env['hr.announcement'].
            sudo().search_count(
                [('department_ids', 'in', self.department_id.id),
                 ('state', '=', 'approved'),
                 ('date_start', '<=', fields.Date.today())]))
            announcement_ids_job = (self.env['hr.announcement'].
            sudo().search_count(
                [('position_ids', 'in', self.job_id.id),
                 ('state', '=', 'approved'),
                 ('date_start', '<=', fields.Date.today())]))
            employee.announcement_count = (announcement_ids_general +
                                           announcement_ids_emp +
                                           announcement_ids_dep +
                                           announcement_ids_job)

    def action_open_announcements(self):
        """ Open a view displaying announcements related to the employee. """
        announcement_ids_general = self.env[
            'hr.announcement'].sudo().search(
            [('is_announcement', '=', True),
             ('state', '=', 'approved'),
             ('date_start', '<=', fields.Date.today())])
        announcement_ids_emp = self.env['hr.announcement'].sudo().search(
            [('employee_ids', 'in', self.id),
             ('state', '=', 'approved'),
             ('date_start', '<=', fields.Date.today())])
        announcement_ids_dep = self.env['hr.announcement'].sudo().search(
            [('department_ids', 'in', self.department_id.id),
             ('state', '=', 'approved'),
             ('date_start', '<=', fields.Date.today())])
        announcement_ids_job = self.env['hr.announcement'].sudo().search(
            [('position_ids', 'in', self.job_id.id),
             ('state', '=', 'approved'),
             ('date_start', '<=', fields.Date.today())])
        announcement_ids = (announcement_ids_general.ids +
                            announcement_ids_emp.ids +
                            announcement_ids_job.ids + announcement_ids_dep.ids)
        view_id = self.env.ref('hr_reward_warning.hr_announcement_view_form').id
        if announcement_ids:
            if len(announcement_ids) > 1:
                value = {
                    'domain': [('id', 'in', announcement_ids)],
                    'view_mode': 'list,form',
                    'res_model': 'hr.announcement',
                    'type': 'ir.actions.act_window',
                    'name': _('Announcements'),
                }
            else:
                value = {
                    'view_mode': 'form',
                    'res_model': 'hr.announcement',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Announcements'),
                    'res_id': announcement_ids and announcement_ids[0],
                }
            return value
