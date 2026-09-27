# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        deficit = self._filter_deficit_exceeding_allocation(deficit)
        _new_records, _all_source_ids, excess_alloc, deficit_alloc = super()._apply_attendance_output(excess, deficit, active_iv=active_iv)
        self._apply_allocation_credits(excess_alloc, deficit_alloc)
