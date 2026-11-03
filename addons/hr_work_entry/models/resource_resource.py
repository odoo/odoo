# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _work_intervals_from_windows(self, dt_from, dt_to, windows, domain=None, attendance_domain=None, availability=False, compute_leaves=True):
        """Remove the attendances whose work entry type counts as absence from the work intervals.

        Only when ``compute_leaves`` is set: such attendances are then treated like leaves.
        """
        work_intervals = super()._work_intervals_from_windows(
            dt_from, dt_to, windows, domain, attendance_domain, availability, compute_leaves)
        if not compute_leaves:
            return work_intervals
        absence_attendance_intervals = self.sudo()._attendance_intervals_from_windows(
            dt_from, dt_to, windows,
            Domain.AND([attendance_domain or Domain.TRUE, [('work_entry_type_id.count_as', '=', 'absence')]]),
            availability,
        )
        return {resource: work_intervals[resource] - absence_attendance_intervals[resource] for resource in self}
