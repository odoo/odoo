# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Alarm(models.Model):
    _name = 'calendar.alarm'
    _description = 'Event Alarm'

    @api.depends('interval', 'duration')
    def _compute_duration_minutes(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    _interval_selection = {'minutes': 'Minutes', 'hours': 'Hours', 'days': 'Days'}

    name = fields.Char('Name', translate=True, required=True)
    alarm_type = fields.Selection([('notification', 'Notification'), ('email', 'Email')], string='Type', required=True, default='email')
    duration = fields.Integer('Remind Before', required=True, default=1)
    interval = fields.Selection(list(_interval_selection.items()), 'Unit', required=True, default='hours')
    duration_minutes = fields.Integer('Duration in minutes', compute='_compute_duration_minutes', store=True, help="Duration in minutes")

    @api.onchange('duration', 'interval', 'alarm_type')
    def _onchange_duration_interval(self):
        display_interval = self._interval_selection.get(self.interval, '')
        display_alarm_type = {key: value for key, value in self._fields['alarm_type']._description_selection(self.env)}[self.alarm_type]
        self.name = "%s - %s %s" % (display_alarm_type, self.duration, display_interval)

    def _update_cron(self):
        try:
            cron = self.env['ir.model.data'].sudo().get_object('calendar', 'ir_cron_scheduler_alarm')
        except ValueError:
            return False
        return cron.toggle(model=self._name, domain=[('alarm_type', '=', 'email')])

    @api.model
    def create(self, values):
        result = super(Alarm, self).create(values)
        self._update_cron()
        return result

    def write(self, values):
        result = super(Alarm, self).write(values)
        self._update_cron()
        return result

    def unlink(self):
        result = super(Alarm, self).unlink()
        self._update_cron()
        return result
