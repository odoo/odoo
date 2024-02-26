# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import threading

from collections import namedtuple
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.tools import exception_to_unicode
from odoo.tools.translate import _
from odoo.exceptions import MissingError, ValidationError


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

    @api.model
    def _selection_template_model(self):
        return [('mail.template', 'Mail')]

    event_type_id = fields.Many2one(
        'event.type', string='Event Type',
        ondelete='cascade', required=True)
    notification_type = fields.Selection([('mail', 'Mail')], string='Send', default='mail', required=True)
    interval_nbr = fields.Integer('Interval', default=1)
    interval_unit = fields.Selection([
        ('now', 'Immediately'),
        ('hours', 'Hours'), ('days', 'Days'),
        ('weeks', 'Weeks'), ('months', 'Months')],
        string='Unit', default='hours', required=True)
    interval_type = fields.Selection([
        ('after_sub', 'After each registration'),
        ('before_event', 'Before the event'),
        ('after_event', 'After the event')],
        string='Trigger', default="before_event", required=True)
    template_model_id = fields.Many2one('ir.model', string='Template Model', compute='_compute_template_model_id', compute_sudo=True)
    template_ref = fields.Reference(string='Template', selection='_selection_template_model', required=True)

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        mail_model = self.env['ir.model']._get('mail.template')
        for mail in self:
            mail.template_model_id = mail_model if mail.notification_type == 'mail' else False

    def _prepare_event_mail_values(self):
        self.ensure_one()
        return namedtuple("MailValues", ['notification_type', 'interval_nbr', 'interval_unit', 'interval_type', 'template_ref'])(
            self.notification_type,
            self.interval_nbr,
            self.interval_unit,
            self.interval_type,
            '%s,%i' % (self.template_ref._name, self.template_ref.id)
        )

class EventMailScheduler(models.Model):
    """ Event automated mailing. This model replaces all existing fields and
    configuration allowing to send emails on events since Odoo 9. A cron exists
    that periodically checks for mailing to run. """
    _name = 'event.mail'
    _rec_name = 'event_id'
    _description = 'Event Automated Mailing'

    @api.model
    def _selection_template_model(self):
        return [('mail.template', 'Mail')]

    def _selection_template_model_get_mapping(self):
        return {'mail': 'mail.template'}

    @api.onchange('notification_type')
    def set_template_ref_model(self):
        mail_model = self.env['mail.template']
        if self.notification_type == 'mail':
            record = mail_model.search([('model', '=', 'event.registration')], limit=1)
            self.template_ref = "{},{}".format('mail.template', record.id) if record else False

    event_id = fields.Many2one('event.event', string='Event', required=True, ondelete='cascade')
    sequence = fields.Integer('Display order')
    notification_type = fields.Selection([('mail', 'Mail')], string='Send', default='mail', required=True)
    interval_nbr = fields.Integer('Interval', default=1)
    interval_unit = fields.Selection([
        ('now', 'Immediately'),
        ('hours', 'Hours'), ('days', 'Days'),
        ('weeks', 'Weeks'), ('months', 'Months')],
        string='Unit', default='hours', required=True)
    interval_type = fields.Selection([
        ('after_sub', 'After each registration'),
        ('before_event', 'Before the event'),
        ('after_event', 'After the event')],
        string='Trigger ', default="before_event", required=True)
    scheduled_date = fields.Datetime('Schedule Date', compute='_compute_scheduled_date', store=True)
    # contact and status
    mail_registration_ids = fields.One2many(
        'event.mail.registration', 'scheduler_id',
        help='Communication related to event registrations')
    mail_done = fields.Boolean("Sent", copy=False, readonly=True)
    mail_state = fields.Selection(
        [('running', 'Running'), ('scheduled', 'Scheduled'), ('sent', 'Sent')],
        string='Global communication Status', compute='_compute_mail_state')
    mail_count_done = fields.Integer('# Sent', copy=False, readonly=True)
    template_model_id = fields.Many2one('ir.model', string='Template Model', compute='_compute_template_model_id', compute_sudo=True)
    template_ref = fields.Reference(string='Template', selection='_selection_template_model', required=True)

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        mail_model = self.env['ir.model']._get('mail.template')
        for mail in self:
            mail.template_model_id = mail_model if mail.notification_type == 'mail' else False

    @api.depends('event_id.date_begin', 'event_id.date_end', 'interval_type', 'interval_unit', 'interval_nbr')
    def _compute_scheduled_date(self):
        for scheduler in self:
            if scheduler.interval_type == 'after_sub':
                date, sign = scheduler.event_id.create_date, 1
            elif scheduler.interval_type == 'before_event':
                date, sign = scheduler.event_id.date_begin, -1
            else:
                date, sign = scheduler.event_id.date_end, 1

            scheduler.scheduled_date = date.replace(microsecond=0) + _INTERVALS[scheduler.interval_unit](sign * scheduler.interval_nbr) if date else False

    @api.depends('interval_type', 'scheduled_date', 'mail_done')
    def _compute_mail_state(self):
        for scheduler in self:
            # registrations based
            if scheduler.interval_type == 'after_sub':
                scheduler.mail_state = 'running'
            # global event based
            elif scheduler.mail_done:
                scheduler.mail_state = 'sent'
            elif scheduler.scheduled_date:
                scheduler.mail_state = 'scheduled'
            else:
                scheduler.mail_state = 'running'

    @api.constrains('notification_type', 'template_ref')
    def _check_template_ref_model(self):
        model_map = self._selection_template_model_get_mapping()
        for record in self.filtered('template_ref'):
            model = model_map[record.notification_type]
            if record.template_ref._name != model:
                raise ValidationError(_('The template which is referenced should be coming from %(model_name)s model.', model_name=model))

    def execute(self):
        todo = self._filter_to_skip(keep_per_registration=True)
        valid_mail_schedulers = todo.filtered(lambda s: s.notification_type == "mail")._filter_template_ref(notification_type="mail")
        for scheduler in todo:
            if scheduler.interval_type == 'after_sub':
                if self.env.context.get('event_mail_registration_ids'):
                    new_registrations = self.env['event.registration'].search([
                        ('id', 'in', self.env.context['event_mail_registration_ids']),
                        ('event_id', '=', scheduler.event_id.id),
                    ]) - scheduler.mail_registration_ids.registration_id
                else:
                    new_registrations = scheduler.event_id.registration_ids.filtered_domain(
                        [('state', 'not in', ('cancel', 'draft'))]
                    ) - scheduler.mail_registration_ids.registration_id
                scheduler._create_missing_mail_registrations(new_registrations)

                # execute scheduler on registrations
                scheduler.mail_registration_ids.execute()
                total_sent = len(scheduler.mail_registration_ids.filtered(lambda reg: reg.mail_sent))
                scheduler.update({
                    'mail_done': total_sent >= (scheduler.event_id.seats_reserved + scheduler.event_id.seats_used),
                    'mail_count_done': total_sent,
                })
            elif scheduler.notification_type == 'mail' and scheduler in valid_mail_schedulers:
                scheduler.event_id.mail_attendees(scheduler.template_ref.id)
                scheduler.update({
                    'mail_done': True,
                    'mail_count_done': len(scheduler.event_id.registration_ids.filtered(lambda r: r.state != 'cancel')),
                })
        return True

    def _create_missing_mail_registrations(self, registrations):
        new = []
        for scheduler in self:
            new += [{
                'registration_id': registration.id,
                'scheduler_id': scheduler.id,
            } for registration in registrations]
        if new:
            return self.env['event.mail.registration'].create(new)
        return self.env['event.mail.registration']

    def _prepare_event_mail_values(self):
        self.ensure_one()
        return namedtuple("MailValues", ['notification_type', 'interval_nbr', 'interval_unit', 'interval_type', 'template_ref'])(
            self.notification_type,
            self.interval_nbr,
            self.interval_unit,
            self.interval_type,
            '%s,%i' % (self.template_ref._name, self.template_ref.id)
        )

    def _filter_template_ref(self, notification_type="mail"):
        """ Check for valid template reference: existing, working template """
        tpl_model, tpl_description = self._filter_template_ref_type_info(notification_type)

        schedulers = self.filtered(lambda s: s.notification_type == notification_type)
        if not schedulers:
            return self.browse()

        invalid = self.browse()
        template_ids = set()
        for scheduler in schedulers:
            if scheduler.template_ref._name != tpl_model:
                invalid += scheduler
            else:
                template_ids.add(scheduler.template_ref.id)
        existing_templates = self.env[tpl_model].browse(template_ids).exists()
        missing = schedulers.filtered(lambda s: s not in invalid and s.template_ref not in existing_templates)
        for scheduler in missing:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to non-existent %s (ID %s)",
                scheduler.id, scheduler.event_id.name, scheduler.event_id.id,
                tpl_description, scheduler.template_ref.id
            )
        for scheduler in invalid:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to invalid template %s (ID %s) (%s instead of %s)",
                scheduler.id, scheduler.event_id.name, scheduler.event_id.id,
                scheduler.template_ref.name, scheduler.template_ref.id,
                scheduler.template_ref._name, tpl_description)
        return self - missing - invalid

    def _filter_template_ref_type_info(self, notification_type):
        return "mail.template", _("mail template")

    def _filter_to_skip(self, keep_type=None, keep_per_registration=False):
        """ Filter schedulers to skip: already done or scheduled for later

        :param str keep_type: if given, a 'notification_type' defined on the
          scheduler e.g. 'mail' or 'sms' (with sms module);
        """
        now = fields.Datetime.now()
        return self.filtered(
            lambda scheduler:
                not scheduler.mail_done
                and (keep_type is None or scheduler.notification_type == keep_type)  # optional notification type filter
                and (keep_per_registration or scheduler.interval_type != 'after_sub')  # keep registration based only if asked
                and (
                    scheduler.interval_type == 'after_sub'
                    or (
                        scheduler.scheduled_date <= now
                        and (scheduler.interval_type == 'after_event' or scheduler.event_id.date_end > now)
                    )
                )
        )

    @api.model
    def _warn_template_error(self, scheduler, exception):
        # We warn ~ once by hour ~ instead of every 10 min if the interval unit is more than 'hours'.
        if random.random() < 0.1666 or scheduler.interval_unit in ('now', 'hours'):
            ex_s = exception_to_unicode(exception)
            try:
                event, template = scheduler.event_id, scheduler.template_ref
                emails = list(set([event.organizer_id.email, event.user_id.email, template.write_uid.email]))
                subject = _("WARNING: Event Scheduler Error for event: %s", event.name)
                body = _("""Event Scheduler for:
  - Event: %(event_name)s (%(event_id)s)
  - Scheduled: %(date)s
  - Template: %(template_name)s (%(template_id)s)

Failed with error:
  - %(error)s

You receive this email because you are:
  - the organizer of the event,
  - or the responsible of the event,
  - or the last writer of the template.
""",
                         event_name=event.name,
                         event_id=event.id,
                         date=scheduler.scheduled_date,
                         template_name=template.name,
                         template_id=template.id,
                         error=ex_s)
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
        """ Backward compatible method, notably if crons are not updated when
        migrating for some reason. """
        return self.schedule_communications(autocommit=autocommit)

    @api.model
    def schedule_communications(self, autocommit=False):
        schedulers = self.search([
            ('event_id.active', '=', True),
            ('mail_done', '=', False),
            ('scheduled_date', '<=', fields.Datetime.now())
        ])

        for scheduler in schedulers:
            try:
                # Prevent a mega prefetch of the registration ids of all the events of all the schedulers
                self.browse(scheduler.id).execute()
            except Exception as e:
                _logger.exception(e)
                self.env.invalidate_all()
                self._warn_template_error(scheduler, e)
            else:
                if autocommit and not getattr(threading.current_thread(), 'testing', False):
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

    def execute(self):
        todo = self._filter_to_skip(keep_type='mail')

        # Exclude schedulers linked to invalid/unusable templates
        valid_schedulers = todo.scheduler_id._filter_template_ref(notification_type="mail")
        valid = todo.filtered(lambda r: r.scheduler_id in valid_schedulers)

        for scheduler, reg_mails in valid.grouped('scheduler_id').items():
            organizer = scheduler.event_id.organizer_id
            company = self.env.company
            author = self.env.ref('base.user_root').partner_id
            if organizer.email:
                author = organizer
            elif company.email:
                author = company.partner_id
            elif self.env.user.email:
                author = self.env.user.partner_id

            email_values = {
                'author_id': author.id,
            }
            if not scheduler.template_ref.email_from:
                email_values['email_from'] = author.email_formatted
            scheduler.template_ref.send_mail_batch(reg_mails.registration_id.ids, email_values=email_values)
        valid.write({'mail_sent': True})

    def _filter_to_skip(self, keep_type=None):
        """ Filter mail registrations to skip: already done, registrations
        canceled (or draft), scheduled for later. Optional can be filtered
        on a scheduler notification type to keep.

        :param str keep_type: if given, a 'notification_type' defined on the
          scheduler e.g. 'mail' or 'sms' (with sms module);
        """
        now = fields.Datetime.now()
        return self.filtered(
            lambda reg_mail:
                not reg_mail.mail_sent  # not already done
                and reg_mail.registration_id.state in ['open', 'done']  # notify only active
                and reg_mail.scheduled_date and reg_mail.scheduled_date <= now  # really scheduled
                and (keep_type is None or reg_mail.scheduler_id.notification_type == keep_type)  # optional type filter
        )

    @api.depends('registration_id', 'scheduler_id.interval_unit', 'scheduler_id.interval_type')
    def _compute_scheduled_date(self):
        for mail in self:
            if mail.registration_id:
                mail.scheduled_date = mail.registration_id.create_date.replace(microsecond=0) + _INTERVALS[mail.scheduler_id.interval_unit](mail.scheduler_id.interval_nbr)
            else:
                mail.scheduled_date = False
