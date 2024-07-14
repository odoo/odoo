# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    # FIXME: [XBO] perhaps this compute will no longer be useful if we have a logic saying
    #            if the work_entry_source is different to calendar then the calendar of the
    #            contract and the resource will be False? :thinking:
    calendar_id = fields.Many2one(compute='_compute_calendar_id', compute_sudo=True, readonly=False, store=True)

    @api.depends('employee_id.contract_id.work_entry_source')
    def _compute_calendar_id(self):
        contract_read_group = self.env['hr.contract']._read_group(
            [
                ('employee_id', 'in', self.employee_id.ids),
                ('work_entry_source', 'in', ['attendance', 'planning']),
                ('state', '=', 'open'),
            ],
            ['employee_id'],
        )
        employee_ids_having_running_contract = {employee.id for [employee] in contract_read_group}
        for resource in self:
            if resource.employee_id.id in employee_ids_having_running_contract:
                resource.calendar_id = False
