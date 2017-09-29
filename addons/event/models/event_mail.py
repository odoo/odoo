# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools


_INTERVALS = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'now': lambda interval: relativedelta(hours=0),
}


class EventTypeMail(models.Model):
    """ Template of event.mail to attach to event.type. Those will be copied
    upon all events created in that type to ease event creation. """
    _name = 'event.type.mail'
    _description = 'Mail Scheduling on Event Type'

    event_type_id = fields.Many2one(
        'event.type', string='Event Type',
        ondelete='cascade', required=True)
    interval_nbr = fields.Integer('Interval', default=1)
    interval_unit = fields.Selection([
        ('now', 'Immediately'),
        ('hours', 'Hour(s)'), ('days', 'Day(s)'),
        ('weeks', 'Week(s)'), ('months', 'Month(s)')],
        string='Unit', default='hours', required=True)
    interval_type = fields.Selection([
        ('after_sub', 'After each registration'),
        ('before_event', 'Before the event'),
        ('after_event', 'After the event')],
        string='Trigger', default="before_event", required=True)
    template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.registration')], required=True, ondelete='restrict',
        help='This field contains the template of the mail that will be automatically sent')


class EventMailScheduler(models.Model):
    """ Event automated mailing. This model replaces all existing fields and
    configuration allowing to send emails on events since Odoo 9. A cron exists
    that periodically checks for mailing to run. """
    _name = 'event.mail'
    _rec_name = 'event_id'
    _description = 'Event Automated Mailing'

    event_id = fields.Many2one('event.event', string='Event', required=True, ondelete='cascade')
    sequence = fields.Integer('Display order')
    interval_nbr = fields.Integer('Interval', default=1)
    interval_unit = fields.Selection([
        ('now', 'Immediately'),
        ('hours', 'Hour(s)'), ('days', 'Day(s)'),
        ('weeks', 'Week(s)'), ('months', 'Month(s)')],
        string='Unit', default='hours', required=True)
    interval_type = fields.Selection([
        ('after_sub', 'After each registration'),
        ('before_event', 'Before the event'),
        ('after_event', 'After the event')],
        string='Trigger ', default="before_event", required=True)
    template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.registration')], required=True, ondelete='restrict',
        help='This field contains the template of the mail that will be automatically sent')
    scheduled_date = fields.Datetime('Scheduled Sent Mail', compute='_compute_scheduled_date', store=True)
    mail_registration_ids = fields.One2many('event.mail.registration', 'scheduler_id')
    mail_sent = fields.Boolean('Mail Sent on Event')
    done = fields.Boolean('Sent', compute='_compute_done', store=True)

    @api.one
    @api.depends('mail_sent', 'interval_type', 'event_id.registration_ids', 'mail_registration_ids')
    def _compute_done(self):
        if self.interval_type in ['before_event', 'after_event']:
            self.done = self.mail_sent
        else:
            self.done = len(self.mail_registration_ids) == len(self.event_id.registration_ids) and all(mail.mail_sent for mail in self.mail_registration_ids)

    @api.one
    @api.depends('event_id.state', 'event_id.date_begin', 'interval_type', 'interval_unit', 'interval_nbr')
    def _compute_scheduled_date(self):
        if self.event_id.state not in ['confirm', 'done']:
            self.scheduled_date = False
        else:
            if self.interval_type == 'after_sub':
                date, sign = self.event_id.create_date, 1
            elif self.interval_type == 'before_event':
                date, sign = self.event_id.date_begin, -1
            else:
                date, sign = self.event_id.date_end, 1

            self.scheduled_date = datetime.strptime(date, tools.DEFAULT_SERVER_DATETIME_FORMAT) + _INTERVALS[self.interval_unit](sign * self.interval_nbr)

    @api.one
    def execute(self):
        if self.interval_type == 'after_sub':
            # update registration lines
            lines = [
                (0, 0, {'registration_id': registration.id})
                for registration in (self.event_id.registration_ids - self.mapped('mail_registration_ids.registration_id'))
            ]
            if lines:
                self.write({'mail_registration_ids': lines})
            # execute scheduler on registrations
            self.mail_registration_ids.filtered(lambda reg: reg.scheduled_date and reg.scheduled_date <= datetime.strftime(fields.datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT)).execute()
        else:
            if not self.mail_sent:
                self.event_id.mail_attendees(self.template_id.id)
                self.write({'mail_sent': True})
        return True

    @api.model
    def run(self, autocommit=False):
        schedulers = self.search([('done', '=', False), ('scheduled_date', '<=', datetime.strftime(fields.datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT))])
        for scheduler in schedulers:
            scheduler.execute()
            if autocommit:
                self.env.cr.commit()
        return True


class EventMailRegistration(models.Model):
    _name = 'event.mail.registration'
    _description = 'Registration Mail Scheduler'
    _rec_name = 'scheduler_id'
    _order = 'scheduled_date DESC'

    scheduler_id = fields.Many2one('event.mail', 'Mail Scheduler', required=True, ondelete='cascade')
    registration_id = fields.Many2one('event.registration', 'Attendee', required=True, ondelete='cascade')
    scheduled_date = fields.Datetime('Scheduled Time', compute='_compute_scheduled_date', store=True)
    mail_sent = fields.Boolean('Mail Sent')

    @api.one
    def execute(self):
        if self.registration_id.state in ['open', 'done'] and not self.mail_sent:
            self.scheduler_id.template_id.send_mail(self.registration_id.id)
            self.write({'mail_sent': True})

    @api.one
    @api.depends('registration_id', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        if self.registration_id:
            date_open = self.registration_id.date_open
            date_open_datetime = date_open and datetime.strptime(date_open, tools.DEFAULT_SERVER_DATETIME_FORMAT) or fields.datetime.now()
            self.scheduled_date = date_open_datetime + _INTERVALS[self.scheduler_id.interval_unit](self.scheduler_id.interval_nbr)
        else:
            self.scheduled_date = False
