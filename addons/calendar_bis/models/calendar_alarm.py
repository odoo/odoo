from odoo import api, fields, models
from odoo.tools import get_timedelta

from datetime import timedelta

class Alarm(models.Model):
    _name = 'calendar.alarm_bis'
    _description = 'Event Alarm'

    name = fields.Char('Name', required=True)
    type = fields.Selection([('mail', 'Mail'), ('notif', 'Notification')], required=True)

    time_unit = fields.Selection([('min', 'Minutes'), ('hour', 'Hours'), ('day', 'Days')])
    time_value = fields.Integer()

    mail_template_id = fields.Many2one(
        'mail.template', string="Email Template",
        domain=[('model', 'in', ['calendar.attendee'])],
        compute='_compute_mail_template_id', readonly=False, store=True,
        help="Template used to render mail reminder content.")

    body = fields.Text("Additional Message", help="Additional message that would be sent with the notification for the reminder")

    @property
    def time_delta(self):
        if not self.time_unit or not self.time_value:
            return False
        return get_timedelta(self.time_value, self.time_unit)

    @api.depends('alarm_type', 'mail_template_id')
    def _compute_mail_template_id(self):
        for alarm in self:
            if alarm.alarm_type == 'email' and not alarm.mail_template_id:
                alarm.mail_template_id = self.env['ir.model.data']._xmlid_to_res_id('calendar.calendar_template_meeting_reminder')
            elif alarm.alarm_type != 'email' or not alarm.mail_template_id:
                alarm.mail_template_id = False

    def _notify(self, event_id):
        self.ensure_one()
        if self.type == 'mail':
            return self._notify_mail(event_id)
        elif self.type == 'notif':
            return self._notify_bus(event_id)

    def _notify_mail(self, event_id):
        pass

    def _notify_bus(self, event_id):
        pass


class AlarmNotification(models.Model):
    _name = 'calendar.alarm_bis_notification'
    _description = 'Event Alarm Notification'

    alarm_id = fields.Many2one('calendar.alarm_bis')
    event_id = fields.Many2one('calendar.event_bis')

    notification_dt = fields.Datetime()
    event_dt = fields.Datetime()

    def notify(self):
        now = fields.Datetime.now() - timedelta(minutes=10)
        for notif in self:
            if now < notif.event_dt:
                notif.alarm_id.notify(notif.event_id)

    def reschedule(self):
        res = self.env['calendar.alarm_bis_notification']
        for notif in self:
            next_timeslot_date = notif.event_id.is_recurring and notif.event_id.next_timeslot_date(notif.event_dt)
            if next_timeslot_date:
                notif.event_dt = next_timeslot_date
                notif.notification_dt = next_timeslot_date - notif.alarm_id.time_delta
                res += notif
        return res

    @api.model
    def _create_next_trigger(self):
        next_trigger = fields.Datetime.now() + timedelta(minutes=10)
        res = self._read_group([], [], ['notification_dt:min'])
        next_notif_time = res and res[0][0]
        if next_notif_time:
            next_trigger = max(next_trigger, next_notif_time)
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm').sudo()
        cron._trigger(at=next_trigger)

    @api.model()
    def _cron_alarm_notification(self):
        notifications = self.search([('notification_dt', '>', fields.Datetime.now())])
        notifications.notify()
        rescheduled = notifications.reschedule()
        (notifications - rescheduled).unlink()
        self._create_next_trigger()
