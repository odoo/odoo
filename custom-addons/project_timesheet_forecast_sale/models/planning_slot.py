# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_utils
from datetime import timedelta


class PlanningShift(models.Model):
    _inherit = 'planning.slot'

    def _init_remaining_hours_to_plan(self, remaining_hours_to_plan):
        res = super()._init_remaining_hours_to_plan(remaining_hours_to_plan)
        if self.project_id and not self.sale_line_id.product_id.planning_enabled:
            if self.project_id not in remaining_hours_to_plan:
                remaining_hours_to_plan[self.project_id] = self.project_id.allocated_hours - self.project_id.total_forecast_time
            if float_utils.float_compare(remaining_hours_to_plan[self.project_id], 0.0, precision_digits=2) != 1:
                return False  # nothing left to allocate.
        return res

    def _update_remaining_hours_to_plan_and_values(self, remaining_hours_to_plan, values):
        res = super()._update_remaining_hours_to_plan_and_values(remaining_hours_to_plan, values)
        if self.project_id and not self.sale_line_id.product_id.planning_enabled:
            if float_utils.float_compare(remaining_hours_to_plan[self.project_id], 0.0, precision_digits=2) != 1:
                return False
            allocated_hours = (values['end_datetime'] - values['start_datetime']).total_seconds() / 3600
            ratio = self.allocated_percentage / 100.00
            remaining_hours = min(remaining_hours_to_plan[self.project_id] / ratio, allocated_hours)
            values['end_datetime'] = values['start_datetime'] + timedelta(hours=remaining_hours)
            values.pop('allocated_hours', None) # we want that to be computed again.
            remaining_hours_to_plan[self.project_id] -= remaining_hours * ratio
        return res
