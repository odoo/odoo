# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    request_overtime = fields.Boolean(compute='_compute_request_overtime')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['request_overtime']

    @api.depends_context('uid')
    @api.depends('total_overtime')
    def _compute_request_overtime(self):
        is_holiday_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        time_off_types = self.env['hr.leave.type'].search_count([
            ('requires_allocation', '=', 'yes'),
            ('employee_requests', '=', 'yes'),
            ('overtime_deductible', '=', True)
        ])
        for user in self:
            if user.total_overtime >= 1:
                if is_holiday_user:
                    user.request_overtime = True
                else:
                    user.request_overtime = time_off_types
            else:
                user.request_overtime = False
