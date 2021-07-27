# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.tools import exception_to_unicode
from odoo.tools.translate import _

import random
import logging
_logger = logging.getLogger(__name__)

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
    _description = 'Mail Scheduling on Event Category'

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
    mail_sent = fields.Boolean('Mail Sent on Event', copy=False)
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

            self.scheduled_date = date + _INTERVALS[self.interval_unit](sign * self.interval_nbr)

    @api.one
    def execute(self):
        now = fields.Datetime.now()
        if self.interval_type == 'after_sub':
            # update registration lines
            lines = [
                (0, 0, {'registration_id': registration.id})
                for registration in (self.event_id.registration_ids - self.mapped('mail_registration_ids.registration_id'))
            ]
            if lines:
                self.write({'mail_registration_ids': lines})
            # execute scheduler on registrations
            self.mail_registration_ids.filtered(lambda reg: reg.scheduled_date and reg.scheduled_date <= now).execute()
        else:
            # Do not send emails if the mailing was scheduled before the event but the event is over
            if not self.mail_sent and (self.interval_type != 'before_event' or self.event_id.date_end > now):
                self.event_id.mail_attendees(self.template_id.id)
                self.write({'mail_sent': True})
        return True

    @api.model
    def _warn_template_error(self, scheduler, exception):
        # We warn ~ once by hour ~ instead of every 10 min if the interval unit is more than 'hours'.
        if random.random() < 0.1666 or scheduler.interval_unit in ('now', 'hours'):
            ex_s = exception_to_unicode(exception)
            try:
                event, template = scheduler.event_id, scheduler.template_id
                emails = list(set([event.organizer_id.email, event.user_id.email, template.write_uid.email]))
                subject = _("WARNING: Event Scheduler Error for event: %s" % event.name)
                body = _("""Event Scheduler for:
                              - Event: %s (%s)
                              - Scheduled: %s
                              - Template: %s (%s)

                            Failed with error:
                              - %s

                            You receive this email because you are:
                              - the organizer of the event,
                              - or the responsible of the event,
                              - or the last writer of the template."""
                         % (event.name, event.id, scheduler.scheduled_date, template.name, template.id, ex_s))
                email = self.env['ir.mail_server'].build_email(
                    email_from=self.env.user.email,
                    email_to=emails,
                    subject=subject, body=body,
                )
                self.env['ir.mail_server'].send_email(email)
            except Exception as e:
                _logger.error("Exception while sending traceback by email: %s.\n Original Traceback:\n%s", e, exception)
                pass

    @api.model
    def run(self, autocommit=False):
        schedulers = self.search([('done', '=', False), ('scheduled_date', '<=', datetime.strftime(fields.datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT))])
        for scheduler in schedulers:
            try:
                with self.env.cr.savepoint():
                    # Prevent a mega prefetch of the registration ids of all the events of all the schedulers
                    self.browse(scheduler.id).execute()
            except Exception as e:
                _logger.exception(e)
                self.invalidate_cache()
                self._warn_template_error(scheduler, e)
            else:
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
            date_open_datetime = date_open or fields.Datetime.now()
            self.scheduled_date = date_open_datetime + _INTERVALS[self.scheduler_id.interval_unit](self.scheduler_id.interval_nbr)
        else:
            self.scheduled_date = False
