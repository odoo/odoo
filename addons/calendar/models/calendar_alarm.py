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
    alarm_type = fields.Selection(
        [('notification', 'Notification'), ('email', 'Email')],
        string='Type', required=True, default='email')
    duration = fields.Integer('Remind Before', required=True, default=1)
    interval = fields.Selection(
        list(_interval_selection.items()), 'Unit', required=True, default='hours')
    duration_minutes = fields.Integer(
        'Duration in minutes', store=True,
        search='_search_duration_minutes', compute='_compute_duration_minutes',
        help="Duration in minutes")

    def _search_duration_minutes(self, operator, value):
        return [
            '|', '|',
            '&', ('interval', '=', 'minutes'), ('duration', operator, value),
            '&', ('interval', '=', 'hours'), ('duration', operator, value / 60),
            '&', ('interval', '=', 'days'), ('duration', operator, value / 60 / 24),
        ]

    @api.onchange('duration', 'interval', 'alarm_type')
    def _onchange_duration_interval(self):
        display_interval = self._interval_selection.get(self.interval, '')
        display_alarm_type = {
            key: value for key, value in self._fields['alarm_type']._description_selection(self.env)
        }[self.alarm_type]
        self.name = "%s - %s %s" % (display_alarm_type, self.duration, display_interval)
