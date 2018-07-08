# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_hr_attendance = fields.Boolean(
        'Manual Attendance', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='hr_attendance.group_hr_attendance',
        help='The user will gain access to the human resources attendance menu, enabling him to manage his own attendance.')

    has_group_hr_attendance_use_pin = fields.Boolean(
        'Enable PIN use', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='hr_attendance.group_hr_attendance_use_pin',
        help='The user will have to enter his PIN to check in and out manually at the company screen.')

    group_hr_attendance_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_hr_attendance'),
        string='Attendance', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_hr_attendance')
