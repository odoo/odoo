# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Alarm(models.Model):
    _name = 'calendar.alarm'
    _description = 'Event Alarm'

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
        search='_search_duration_minutes', compute='_compute_duration_minutes')
    mail_template_id = fields.Many2one(
        'mail.template', string="Email Template",
        domain=[('model', 'in', ['calendar.attendee'])],
        compute='_compute_mail_template_id', readonly=False, store=True,
        help="Template used to render mail reminder content.")
    body = fields.Text("Additional Message", help="Additional message that would be sent with the notification for the reminder")

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

    @api.depends('alarm_type', 'mail_template_id')
    def _compute_mail_template_id(self):
        for alarm in self:
            if alarm.alarm_type == 'email' and not alarm.mail_template_id:
                alarm.mail_template_id = self.env['ir.model.data']._xmlid_to_res_id('calendar.calendar_template_meeting_reminder')
            elif alarm.alarm_type != 'email' or not alarm.mail_template_id:
                alarm.mail_template_id = False

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
