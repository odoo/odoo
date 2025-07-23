# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _filter_french_part_time_entries(self):
        french_part_time_work_entries = self.filtered(lambda w:
            w.company_id.country_id.code == 'FR'
            and w.employee_id.resource_calendar_id != w.company_id.resource_calendar_id)
        return french_part_time_work_entries

    def _mark_leaves_outside_schedule(self):
        french_part_time_work_entries = self._filter_french_part_time_entries()
        if not french_part_time_work_entries:
            return super()._mark_leaves_outside_schedule()
        other_work_entries = self - french_part_time_work_entries
        if other_work_entries:
            return other_work_entries._mark_leaves_outside_schedule()
        return False

    def _get_duration_batch(self):
        res = super()._get_duration_batch()
        french_part_time_work_entries = self._filter_french_part_time_entries()
        if not french_part_time_work_entries:
            return res
        for entry in french_part_time_work_entries:
            if entry.id in res and res[entry.id] == 0 and entry.date_start and entry.date_stop:
                res[entry.id] = (entry.date_stop - entry.date_start).seconds/3600
        return res
