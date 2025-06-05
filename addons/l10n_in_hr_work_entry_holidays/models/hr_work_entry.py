# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _filter_indian_sandwich_leave_entries(self):
        return self.filtered(lambda we:
            we.company_id.country_id.code == 'IN'
            and we.leave_id.l10n_in_contains_sandwich_leaves
        )

    def _mark_leaves_outside_schedule(self):
        return super(HrWorkEntry, self - self._filter_indian_sandwich_leave_entries())._mark_leaves_outside_schedule()

    def _get_duration_batch(self):
        duration_per_work_entry = super()._get_duration_batch()
        indian_sandwich_leave_work_entries = self._filter_indian_sandwich_leave_entries()
        for entry in indian_sandwich_leave_work_entries:
            if entry.id in duration_per_work_entry and duration_per_work_entry[entry.id] == 0:
                duration_per_work_entry[entry.id] = (entry.date_stop - entry.date_start).seconds / 3600
        return duration_per_work_entry
