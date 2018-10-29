# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import api, fields, models, _
from odoo.exceptions import Warning



class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    leave_ids = fields.One2many('hr.leave', 'calendar_leave_id')
    generate_hr_leaves = fields.Boolean("Leaves are generated", default=False)
    holiday_id = fields.Many2one("hr.leave", string='Leave Request')

    @api.model
    def create(self, values):
        result = super(ResourceCalendarLeaves, self).create(values)
        return result

    def write(self, values):
        res = super(ResourceCalendarLeaves, self).write(values)
        if not self.resource_id:
            date_from = values.get('date_from', self.date_from)
            date_to = values.get('date_to', self.date_to)
            if isinstance(date_from, str):
                date_from = fields.Datetime.from_string(date_from)
            if isinstance(date_to, str):
                date_to = fields.Datetime.from_string(date_to)
            time_delta = date_to - date_from
            number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

            leaves = self.leave_ids.with_context(mail_notrack=True, tracking_disable=True, no_resource_remove=True, auto_leave_create_disable=True)
            leaves.action_refuse()
            leaves.action_draft()

            for leave in leaves:
                leave.write({
                    'name': values.get('name', self.name),
                    'holiday_status_id': values.get('company_id', self.company_id).bank_leaves_type_id.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'request_date_from': date_from,
                    'request_date_to': date_to,
                    'number_of_days': number_of_days,
                })
            leaves.action_confirm()
            leaves.action_validate()
        return res

    def unlink(self):
        to_delete = self.env['hr.leave'].with_context(mail_notrack=True, tracking_disable=True, no_resource_remove=True)
        for leave in self:
            to_delete |= leave.leave_ids
        to_delete.action_refuse()
        to_delete.action_draft()
        to_delete.unlink()
        super(ResourceCalendarLeaves, self).unlink()

    def create_leaves(self, values={}):
        date_from = values.get('date_from', self.date_from)
        date_to = values.get('date_to', self.date_to)
        if isinstance(date_from, str):
            date_from = fields.Datetime.from_string(date_from)
        if isinstance(date_to, str):
            date_to = fields.Datetime.from_string(date_to)
        time_delta = date_to - date_from
        number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

        employees = self.env['hr.employee'].search([('resource_calendar_id', '=', values.get('calendar_id', self.calendar_id.id))])
        Leave = self.env['hr.leave'].sudo().with_context(mail_notrack=True, tracking_disable=True, auto_leave_create_disable=True, mail_activity_quick_update=True)

        problem_name = []

        leaves = Leave
        for employee in employees:
            company = self.env['resource.calendar'].browse(values.get('calendar_id', self.calendar_id.id)).company_id

            try:
                leaves = leaves | Leave.create({
                    'name': values.get('name', self.name),
                    'employee_id': employee.id,
                    'holiday_status_id': company.bank_leaves_type_id.id,
                    'request_date_from': values.get('date_from', self.date_from),
                    'request_date_to': values.get('date_to', self.date_to),
                    'date_from': values.get('date_from', self.date_from),
                    'date_to': values.get('date_to', self.date_to),
                    'calendar_leave_id': values.get('res', False).id,
                    'request_unit_custom': True,
                    'number_of_days': number_of_days,
                })

            except:
                problem_name.append(self.env['hr.employee'].browse(employee.id).name)
                continue

        if len(problem_name):
            raise Warning(_('Conflict with employee(s):\n %(employee)s') % {'employee': '\n'.join(problem_name)})

        leaves.sudo().action_approve()

    @api.multi
    def action_generate_hr_leaves(self):
        self.generate_hr_leaves = True
        values = {
            'res': self,
            'calendar_id': self.calendar_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'name': self.name,
            'generate_hr_leaves': self.generate_hr_leaves,
        }
        self.create_leaves(values)
