# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import fields, models


class AppointmentManageLeaves(models.TransientModel):
    _name = 'appointment.manage.leaves'
    _description = 'Add or remove leaves from appointments'

    def _default_time(self, hour, minute):
        user_timezone = pytz.timezone(self.env.user.tz or self.env.context.get('tz') or 'UTC')
        user_time = user_timezone.localize(fields.Datetime.today().replace(hour=hour, minute=minute))
        return user_time.astimezone(pytz.utc).replace(tzinfo=None)

    appointment_resource_ids = fields.Many2many('appointment.resource', string="Resources", required=True)
    leave_start_dt = fields.Datetime('Start Date', required=True, default=lambda self: self._default_time(0, 0))
    leave_end_dt = fields.Datetime('End Date', required=True, default=lambda self: self._default_time(23, 59))
    reason = fields.Char('Reason')

    def action_create_leave(self):
        # need to force company to false otherwise it defaults to current company when calendar has no company :/
        self.env['resource.calendar.leaves'].create([{
            'calendar_id': resource.resource_calendar_id.id,
            'date_from': wizard.leave_start_dt,
            'date_to': wizard.leave_end_dt,
            'name': wizard.reason,
            'resource_id': resource.resource_id.id,
        } for wizard in self for resource in wizard.appointment_resource_ids]).company_id = False
        return {'type': 'ir.actions.act_window_close'}
