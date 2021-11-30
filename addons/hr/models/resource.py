# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from pytz import utc, timezone
from datetime import datetime

from odoo import fields, models
from odoo.addons.resource.models.resource import Intervals


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', domain="[('company_id', '=', company_id)]")

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        """
            Returns a dict of dict with resource's id as first key and resource's calendar as secondary key
            The value is the validity interval of the calendar for the given resource.

            The validity interval of the employee resource calendar is the lifetime of the employee, from creation to departure.
        """
        assert start.tzinfo and end.tzinfo
        calendars_within_period_per_resource = super()._get_calendars_validity_within_period(start, end, default_company=default_company)
        for resource in self:
            if not resource.employee_id:
                continue
            create_date = max(start, utc.localize(resource.employee_id.create_date))
            if resource.employee_id.departure_date and resource.employee_id.departure_date <= end.date():
                departure_datetime = timezone(resource.tz).localize(datetime.combine(resource.employee_id.departure_date, datetime.max.time()))
                departure_datetime = min(departure_datetime, end)
            else:
                departure_datetime = end
            interval = Intervals([(create_date, departure_datetime, self.env['resource.calendar.attendance'])])
            for calendar in calendars_within_period_per_resource[resource.id]:
                calendars_within_period_per_resource[resource.id][calendar] &= interval
        return calendars_within_period_per_resource
