# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    def _apply_attendance_output(self, excess, deficit, source_intervals_by_employee=None):
        """Apply the results on attendances, then credit or deduct the allocations
        (``hr.time.rule._apply_allocation_credits``).

        Deficits that would overdraw the allocation are dropped first
        (``_filter_deficit_exceeding_allocation``): they create neither output nor deduction.

        :return: the result of the base method, see ``hr.time.rule._apply_output``
        :rtype: tuple
        """
        deficit = self._filter_deficit_exceeding_allocation(deficit)
        result = super()._apply_attendance_output(excess, deficit, source_intervals_by_employee=source_intervals_by_employee)
        _new_records, _all_source_ids, excess_allocation_credits, deficit_allocation_credits = result
        self._apply_allocation_credits(excess_allocation_credits, deficit_allocation_credits)
        return result
