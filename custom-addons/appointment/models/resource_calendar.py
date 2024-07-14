# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        intervals = super()._unavailable_intervals_batch(start_dt, end_dt, resources, domain, tz)
        resource_ids = self.env['appointment.resource'].sudo().search([]).resource_id.ids

        result = {}
        for resource in intervals:
            result[resource] = [
                interval for interval in intervals[resource]
                if (interval[1] - interval[0]).total_seconds() > 60
            ] if resource in resource_ids else intervals[resource]

        return result
