# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    request_overtime = fields.Boolean(compute='_compute_request_overtime')

    def __init__(self, pool, cr):
        super(ResUsers, self).__init__(pool, cr)
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + ['request_overtime']

    @api.depends_context('uid')
    @api.depends('total_overtime')
    def _compute_request_overtime(self):
        self.request_overtime = False
        has_overtime = self.filtered(lambda r: r.total_overtime >= 1)
        if has_overtime:
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                has_overtime.request_overtime = True
            else:
                allocation = self.env['hr.leave.type'].search_count([
                    ('valid', '=', True),
                    ('allocation_type', '=', 'fixed_allocation'),
                    ('overtime_deductible', '=', True)
                ])
                has_overtime.request_overtime = allocation > 0
