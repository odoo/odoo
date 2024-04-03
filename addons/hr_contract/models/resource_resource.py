# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime
from pytz import timezone

from odoo import models
from odoo.addons.resource.models.resource import Intervals

class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        assert start.tzinfo and end.tzinfo
        if not self:
            return super()._get_calendars_validity_within_period(start, end, default_company=default_company)
        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        # Employees that have ever had an active contract
        employee_ids_with_active_contracts = {
            contract['employee_id'][0] for contract in
            self.env['hr.contract']._read_group(
                domain=[
                    ('employee_id', 'in', self.employee_id.ids),
                    '|', ('state', '=', 'open'),
                    '|', ('state', '=', 'close'),
                         '&', ('state', '=', 'draft'), ('kanban_state', '=', 'done')
                ],
                fields=['employee_id'], groupby=['employee_id']
            )
        }
        resource_without_contract = self.filtered(
            lambda r: not r.employee_id\
                   or not r.employee_id.id in employee_ids_with_active_contracts\
                   or r.employee_id.employee_type not in ['employee', 'student']
        )
        if resource_without_contract:
            calendars_within_period_per_resource.update(
                super(ResourceResource, resource_without_contract)._get_calendars_validity_within_period(start, end, default_company=default_company)
            )
        resource_with_contract = self - resource_without_contract
        if not resource_with_contract:
            return calendars_within_period_per_resource
        timezones = {resource.tz for resource in resource_with_contract}
        date_start = min(start.astimezone(timezone(tz)).date() for tz in timezones)
        date_end = max(end.astimezone(timezone(tz)).date() for tz in timezones)
        contracts = resource_with_contract.employee_id._get_contracts(
            date_start, date_end, states=['open', 'draft', 'close']
        ).filtered(lambda c: c.state in ['open', 'close'] or c.kanban_state == 'done')
        for contract in contracts:
            tz = timezone(contract.employee_id.tz)
            calendars_within_period_per_resource[contract.employee_id.resource_id.id][contract.resource_calendar_id] |= Intervals([(
                tz.localize(datetime.combine(contract.date_start, datetime.min.time())) if contract.date_start > start.astimezone(tz).date() else start,
                tz.localize(datetime.combine(contract.date_end, datetime.max.time())) if contract.date_end and contract.date_end < end.astimezone(tz).date() else end,
                self.env['resource.calendar.attendance']
            )])
        return calendars_within_period_per_resource
