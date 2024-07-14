# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def _work_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, compute_leaves=True):
        work_intervals = super()._work_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz, compute_leaves=compute_leaves)
        if self.sudo().company_id.country_id.code != 'HK' or not compute_leaves:
            return work_intervals

        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]

        leave_attendance_intervals = self.sudo()._attendance_intervals_batch(
            start_dt, end_dt, resources=resources, domain=[('work_entry_type_id.is_leave', '=', True)], tz=tz)
        return {
            r.id: (work_intervals[r.id] - leave_attendance_intervals[r.id]) for r in resources_list
        }
