# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import utc
from random import shuffle

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_planning_hours_to_plan(self):
        planning_rental_sols = self.filtered(
            lambda sol:
                sol.is_rental
                and sol.state not in ['draft', 'sent']
                and sol.product_id.planning_enabled
        )

        for line in planning_rental_sols:
            if line.planning_slot_ids.resource_id.calendar_id:
                days_per_week = line.company_id.resource_calendar_id.get_work_duration_data(line.start_date, line.return_date)['days']
            else:
                days_per_week = line.order_id.duration_days + (1 if line.order_id.remaining_hours else 0)
            line.planning_hours_to_plan = line.company_id.resource_calendar_id.hours_per_day * days_per_week
        super(SaleOrderLine, self - planning_rental_sols)._compute_planning_hours_to_plan()

    def _planning_slot_vals_list(self):
        vals_list = super()._planning_slot_vals_list()
        assigned_resource_ids = []
        for sol, vals in zip(self, vals_list):
            if not sol.is_rental:
                continue

            vals.update({
                'start_datetime': sol.start_date,
                'end_datetime': sol.return_date,
            })
            available_resources = sol.product_id.planning_role_id.resource_ids
            if not available_resources:
                return vals

            unavailable_resource_slots = sol.env['planning.slot'].search([
                ('resource_id', 'in', available_resources.ids),
                ('start_datetime', '<=', sol.return_date),
                ('end_datetime', '>=', sol.start_date),
            ])
            resource_leaves = sol.env['resource.calendar.leaves'].search([
                ('resource_id', 'in', available_resources.ids),
                ('date_from', '<=', sol.return_date),
                ('date_to', '>=', sol.start_date),
            ])
            available_resources -= (unavailable_resource_slots.resource_id + resource_leaves.resource_id)
            if not available_resources:
                return vals

            date_from = utc.localize(sol.start_date)
            date_to = utc.localize(sol.return_date)
            work_intervals_per_resource, _dummy = available_resources._get_valid_work_intervals(date_from, date_to, available_resources.calendar_id)
            free_resource_ids = []
            flexible_resource_ids = []
            for available_resource in available_resources:
                if not available_resource.calendar_id:
                    flexible_resource_ids.append(available_resource.id)
                elif not work_intervals_per_resource[available_resource.id]:
                    continue
                if not (assigned_resource_ids and available_resource.id in assigned_resource_ids):
                    free_resource_ids.append(available_resource.id)

            shuffle(free_resource_ids)

            if free_resource_ids and free_resource_ids[0] not in flexible_resource_ids:
                days_per_week = sol.company_id.resource_calendar_id.get_work_duration_data(sol.start_date, sol.return_date)['days']
                sol.planning_hours_to_plan = sol.company_id.resource_calendar_id.hours_per_day * days_per_week

            resource_id = False
            if free_resource_ids:
                resource_id = free_resource_ids[0]
                assigned_resource_ids.append(resource_id)
            vals['resource_id'] = resource_id
        return vals_list
