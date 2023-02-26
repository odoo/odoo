# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from datetime import datetime

from odoo import models, fields, api, _


class HrAnnouncements(models.Model):
    _inherit = 'hr.employee'

    def _announcement_count(self):
        now = datetime.now()
        now_date = now.date()
        for obj in self:
            announcement_ids_general = self.env[
                'hr.announcement'].sudo().search(
                [('is_announcement', '=', True),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_emp = self.env['hr.announcement'].sudo().search(
                [('employee_ids', 'in', self.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_dep = self.env['hr.announcement'].sudo().search(
                [('department_ids', 'in', self.department_id.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_job = self.env['hr.announcement'].sudo().search(
                [('position_ids', 'in', self.job_id.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])

            announcement_ids = announcement_ids_general.ids + announcement_ids_emp.ids + announcement_ids_dep.ids + announcement_ids_job.ids

            obj.announcement_count = len(set(announcement_ids))

    def announcement_view(self):
        now = datetime.now()
        now_date = now.date()
        for obj in self:

            announcement_ids_general = self.env[
                'hr.announcement'].sudo().search(
                [('is_announcement', '=', True),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_emp = self.env['hr.announcement'].sudo().search(
                [('employee_ids', 'in', self.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_dep = self.env['hr.announcement'].sudo().search(
                [('department_ids', 'in', self.department_id.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])
            announcement_ids_job = self.env['hr.announcement'].sudo().search(
                [('position_ids', 'in', self.job_id.id),
                 ('state', 'in', ('approved', 'done')),
                 ('date_start', '<=', now_date)])

            ann_obj = announcement_ids_general.ids + announcement_ids_emp.ids + announcement_ids_job.ids + announcement_ids_dep.ids

            ann_ids = []

            for each in ann_obj:
                ann_ids.append(each)
            view_id = self.env.ref(
                'hr_reward_warning.view_hr_announcement_form').id
            if ann_ids:
                if len(ann_ids) > 1:
                    value = {
                        'domain': str([('id', 'in', ann_ids)]),
                        'view_mode': 'tree,form',
                        'res_model': 'hr.announcement',
                        'view_id': False,
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
                        'res_id': ann_ids and ann_ids[0]
                    }
                return value

    announcement_count = fields.Integer(compute='_announcement_count',
                                        string='# Announcements',
                                        help="Count of Announcement's")
