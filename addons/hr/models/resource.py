# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models
from odoo.orm.domains import Domain


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', check_company=True, context={'active_test': False})

    job_title = fields.Char(related='employee_id.job_title')
    department_id = fields.Many2one(related='employee_id.department_id')
    work_email = fields.Char(related='employee_id.work_email')
    work_phone = fields.Char(related='employee_id.work_phone')
    show_hr_icon_display = fields.Boolean(related='employee_id.show_hr_icon_display')
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display')

    contracts_count = fields.Integer("# Contracts using it", compute='_compute_contracts_count', groups="hr.group_hr_contract_manager")
    contract_ids = fields.One2many('hr.contract', 'resource_calendar_id', groups="hr.group_hr_contract_manager")

    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """
            Transfer some resource.calendar.leaves from 'self' to another calendar 'other_calendar'.
            Transfered leaves linked to `resources` (or all if `resources` is None) and starting
            after 'from_date' (or today if None).
        """
        from_date = from_date or fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = Domain.AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })

    @api.depends('contract_ids')
    def _compute_contracts_count(self):
        contracts_data = self.env['hr.contract']._read_group(
            domain=[
                ('resource_calendar_id', 'in', self.ids),
                ('company_id', 'in', self.env.companies.ids),
                ('employee_id', '!=', False)],
            groupby=['resource_calendar_id'],
            aggregates=['__count']
        )
        contracts_count = defaultdict(int)
        for calendar, state, count in contracts_data:
            if calendar.date_start <= fields.Date.today() and (not calendar.date_end or calendar.date_end <= fields.Date.today()):
                contracts_count[calendar.id] = count
        for calendar in self:
            calendar.contracts_count = contracts_count[calendar.id]

    def action_open_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr.action_hr_version")
        action.update({
            'display_name': 'Contracts',
            'domain': [('resource_calendar_id', '=', self.id), ('employee_id', '!=', False)]
        })
        return action

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
