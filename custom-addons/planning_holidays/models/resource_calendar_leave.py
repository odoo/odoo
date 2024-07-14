# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, time

from odoo import api, models
from odoo.osv import expression


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _process_shifts_domain(self):
        """ Compute the domain to get all slots in the period of leaves

            When a leave is created, the slots in the period of the leave
            must be recomputed to get the correct allocated hours, for instance

            :returns: domain to get all slots in the leaves period.
        """
        if not self:
            return expression.FALSE_DOMAIN
        global_leave_start_date = leave_start_date = datetime.combine(date.today(), time.max)
        global_leave_end_date = leave_end_date = datetime.combine(date(1970, 1, 1), time.min)
        resource_ids = set()
        for leave in self:
            if leave.resource_id:
                if leave_start_date > leave.date_from:
                    leave_start_date = leave.date_from
                if leave_end_date < leave.date_to:
                    leave_end_date = leave.date_to
                resource_ids.add(leave.resource_id.id)
                continue
            if global_leave_start_date > leave.date_from:
                global_leave_start_date = leave.date_from
            if global_leave_end_date < leave.date_to:
                global_leave_end_date = leave.date_to
        domain = [
            ('start_datetime', '<=', global_leave_end_date),
            ('end_datetime', '>=', global_leave_start_date),
            ('resource_type', '!=', 'material'),
        ]
        if resource_ids:
            domain = expression.OR([
                [
                    ('start_datetime', '<=', leave_end_date),
                    ('end_datetime', '>=', leave_start_date),
                    ('resource_id', 'in', list(resource_ids)),
                ],
                domain,
            ])
        return domain

    def _recompute_shifts_in_leave_periods(self, domain=None):
        """ Recompute some fields in shifts based on the leaves

            :param domain: domain to fetch the shifts to recompute.
        """
        if domain is None and not self:  # then no shifts to recompute can be found
            return
        if domain is None:
            domain = self._process_shifts_domain()
        shifts = self.env['planning.slot'].search(domain)
        shifts._compute_allocated_hours()
        shifts._compute_working_days_count()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_shifts_in_leave_periods()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ['resource_id', 'start_datetime', 'end_datetime']):
            self._recompute_shifts_in_leave_periods()
        return res

    def unlink(self):
        domain = self._process_shifts_domain()
        res = super().unlink()
        self._recompute_shifts_in_leave_periods(domain)
        return res
