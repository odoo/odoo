# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from pytz import timezone

from odoo import api, fields, models
from odoo.tools.intervals import Intervals


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', check_company=True, context={'active_test': False})

    job_title = fields.Char(compute='_compute_job_title', compute_sudo=True)
    department_id = fields.Many2one('hr.department', compute='_compute_department_id', compute_sudo=True)
    work_location_id = fields.Many2one(related='employee_id.work_location_id')
    work_email = fields.Char(related='employee_id.work_email')
    work_phone = fields.Char(related='employee_id.work_phone')
    show_hr_icon_display = fields.Boolean(related='employee_id.show_hr_icon_display')
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display')

    # Skills
    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')

    @api.depends('employee_id')
    def _compute_job_title(self):
        for resource in self:
            resource.job_title = resource.employee_id.job_title

    @api.depends('employee_id')
    def _compute_department_id(self):
        for resource in self:
            resource.department_id = resource.employee_id.department_id

    @api.depends('employee_id')
    def _compute_avatar_128(self):
        is_hr_user = self.env.user.has_group('hr.group_hr_user')
        if not is_hr_user:
            public_employees = self.env['hr.employee.public'].with_context(active_test=False).search([
                ('resource_id', 'in', self.ids),
            ])
            avatar_per_employee_id = {emp.id: emp.avatar_128 for emp in public_employees}

        for resource in self:
            employee = resource.employee_id
            if not employee:
                resource.avatar_128 = False
                continue
            if is_hr_user:
                resource.avatar_128 = employee[0].avatar_128
            else:
                resource.avatar_128 = avatar_per_employee_id[employee[0].id]

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        assert start.tzinfo and end.tzinfo
        if not self:
            return super()._get_calendars_validity_within_period(start, end, default_company=default_company)
        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        # Employees that have ever had an active contract
        employee_ids_with_active_contracts = {
            employee.id for [employee] in
            self.env['hr.version']._read_group(
                domain=[
                    ('employee_id', 'in', self.employee_id.ids),
                    ('contract_date_start', '!=', False),
                ],
                groupby=['employee_id'],
            )
        }
        resource_without_contract = self.filtered(
            lambda r: not r.employee_id
                   or not r.employee_id.id in employee_ids_with_active_contracts
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
        contracts = resource_with_contract.employee_id._get_versions_with_contract_overlap_with_period(date_start, date_end)
        for contract in contracts:
            tz = timezone(contract.employee_id.tz)
            calendars_within_period_per_resource[contract.employee_id.resource_id.id][contract.resource_calendar_id] |= Intervals([(
                tz.localize(datetime.combine(contract.contract_date_start, datetime.min.time())) if contract.contract_date_start > start.astimezone(tz).date() else start,
                tz.localize(datetime.combine(contract.contract_date_end, datetime.max.time())) if contract.contract_date_end and contract.contract_date_end < end.astimezone(tz).date() else end,
                self.env['resource.calendar.attendance']
            )])
        return calendars_within_period_per_resource
