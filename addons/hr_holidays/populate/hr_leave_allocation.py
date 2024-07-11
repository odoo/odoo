# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"
    _populate_sizes = {"small": 100, "medium": 800, "large": 10000}
    _populate_dependencies = ['hr.employee', 'hr.leave.type']

    def _populate_factories(self):

        employee_ids = self.env.registry.populated_models['hr.employee']
        hr_leave_type_ids = self.env['hr.leave.type']\
            .browse(self.env.registry.populated_models['hr.leave.type'])\
            .filtered(lambda lt: lt.requires_allocation == 'yes')\
            .ids

        return [
            ('holiday_status_id', populate.randomize(hr_leave_type_ids)),
            ('employee_id', populate.randomize(employee_ids)),
        ]
