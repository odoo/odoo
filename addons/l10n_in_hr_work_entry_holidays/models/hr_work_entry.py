# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _filter_indian_sandwich_leave_entries(self):
        return self.filtered(lambda we:
            we.company_id.country_id.code == 'IN'
            and we.leave_ids.l10n_in_contains_sandwich_leaves
        )

    def _mark_leaves_outside_schedule(self):
        return super(HrWorkEntry, self - self._filter_indian_sandwich_leave_entries())._mark_leaves_outside_schedule()

    def _get_duration_batch(self):
        duration_per_work_entry = super()._get_duration_batch()
        indian_sandwich_leave_work_entries = self._filter_indian_sandwich_leave_entries()
        for entry in indian_sandwich_leave_work_entries:
            if entry.id in duration_per_work_entry and duration_per_work_entry[entry.id] == 0:
                calendar = entry.version_id.resource_calendar_id or entry.company_id.resource_calendar_id
                duration_per_work_entry[entry.id] = entry.duration or (calendar.hours_per_day if calendar else 0.0)
        return duration_per_work_entry
