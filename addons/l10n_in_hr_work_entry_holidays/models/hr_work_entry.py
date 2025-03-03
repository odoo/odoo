# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _filter_indian_sandwich_leave_entries(self):
        indian_sandwich_leave_work_entries = self.filtered(lambda w:
            w.company_id.country_id.code == 'IN'
            and w.leave_id.l10n_in_contains_sandwich_leaves)
        return indian_sandwich_leave_work_entries

    def _mark_leaves_outside_schedule(self):
        indian_sandwich_leave_work_entries = self._filter_indian_sandwich_leave_entries()
        if not indian_sandwich_leave_work_entries:
            return super()._mark_leaves_outside_schedule()
        other_work_entries = self - indian_sandwich_leave_work_entries
        if other_work_entries:
            return other_work_entries._mark_leaves_outside_schedule()
        return False

    def _get_duration_batch(self):
        res = super()._get_duration_batch()
        indian_sandwich_leave_work_entries = self._filter_indian_sandwich_leave_entries()
        if not indian_sandwich_leave_work_entries:
            return res
        for entry in indian_sandwich_leave_work_entries:
            if entry.id in res and res[entry.id] == 0:
                res[entry.id] = (entry.date_stop - entry.date_start).seconds/3600
        return res
