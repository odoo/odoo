# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from datetime import datetime

from odoo import api, fields, models
from odoo.tools import OrderedSet

_logger = logging.getLogger(__name__)


class MailMessageSchedule(models.Model):
    """ Mail message notification schedule queue.

    This model is used to store the mail messages scheduled. So we can
    delay the sending of the notifications. A scheduled date field already
    exists on the <mail.mail> but it does not allow us to delay the sending
    of the <bus.bus> notifications.
    """
    _name = 'mail.message.schedule'
    _description = 'Scheduled Message'
    _order = 'scheduled_datetime DESC, id DESC'
    _rec_name = 'mail_message_id'

    mail_message_id = fields.Many2one(
        'mail.message', string='Message',
        ondelete='cascade', required=True)
    notification_parameters = fields.Text('Notification Parameter')
    scheduled_datetime = fields.Datetime(
        'Scheduled Send Date', required=True,
        help='Datetime at which notification should be sent.')

    @api.model_create_multi
    def create(self, vals_list):
        schedules = super().create(vals_list)
        if schedules:
            self.env.ref('mail.ir_cron_send_scheduled_message')._trigger_list(
                set(schedules.mapped('scheduled_datetime'))
            )
        return schedules

    @api.model
    def _send_notifications_cron(self):
        messages_scheduled = self.env['mail.message.schedule'].search(
            [('scheduled_datetime', '<=', datetime.utcnow())]
        )
        if messages_scheduled:
            _logger.info('Send %s scheduled messages', len(messages_scheduled))
            messages_scheduled._send_notifications()

    def force_send(self):
        """ Launch notification process independently from the expected date. """
        return self._send_notifications()

    def _send_notifications(self, default_notify_kwargs=None):
        """ Send notification for scheduled messages.

        :param dict default_notify_kwargs: optional parameters to propagate to
          ``notify_thread``. Those are default values overridden by content of
          ``notification_parameters`` field.
        """
        for model, schedules in self._group_by_model().items():
            if model:
                existing = self.env[model].browse(schedules.mail_message_id.mapped('res_id')).exists()
                existing_ids = set(existing.ids)
                schedules = schedules.filtered(lambda schedule: schedule.mail_message_id.res_id in existing_ids)
            else:
                existing = self.env['mail.thread']

            # notify in batch messages sharing the same notification parameters
            message_ids_by_parameters = {}
            for schedule in schedules:
                message_ids_by_parameters.setdefault(schedule.notification_parameters, []).append(schedule.mail_message_id.id)

            for notification_parameters, message_ids in message_ids_by_parameters.items():
                notify_kwargs = dict(default_notify_kwargs or {}, skip_existing=True)
                try:
                    schedule_notify_kwargs = json.loads(notification_parameters)
                except Exception:
                    pass
                else:
                    schedule_notify_kwargs.pop('scheduled_date', None)
                    notify_kwargs.update(schedule_notify_kwargs)

                messages = self.env['mail.message'].browse(message_ids)
                records = existing.browse(OrderedSet(messages.mapped('res_id'))) if model else existing
                records._notify_thread_batch(messages, **notify_kwargs)

        self.unlink()
        return True

    @api.model
    def _send_message_notifications(self, messages, default_notify_kwargs=None):
        """ Send scheduled notification for given messages.

        :param <mail.message> messages: scheduled sending related to those messages
          will be sent now;
        :param dict default_notify_kwargs: optional parameters to propagate to
          ``notify_thread``. Those are default values overridden by content of
          ``notification_parameters`` field.

        :returns: False if no schedule has been found, True otherwise
        :rtype: bool
        """
        messages_scheduled = self.search(
            [('mail_message_id', 'in', messages.ids)]
        )
        if not messages_scheduled:
            return False

        messages_scheduled._send_notifications(default_notify_kwargs=default_notify_kwargs)
        return True

    @api.model
    def _update_message_scheduled_datetime(self, messages, new_datetime):
        """ Update scheduled datetime for scheduled sending related to messages.

        :param <mail.message> messages: scheduled sending related to those messages
          will be updated. Missing one are skipped;
        :param datetime new_datetime: new datetime for sending. New triggers
          are created based on it;

        :returns: False if no schedule has been found, True otherwise
        :rtype: bool
        """
        messages_scheduled = self.search(
            [('mail_message_id', 'in', messages.ids)]
        )
        if not messages_scheduled:
            return False

        messages_scheduled.scheduled_datetime = new_datetime
        self.env.ref('mail.ir_cron_send_scheduled_message')._trigger(new_datetime)
        return True

    def _group_by_model(self):
        grouped = {}
        for schedule in self:
            model = schedule.mail_message_id.model if schedule.mail_message_id.model and schedule.mail_message_id.res_id else False
            if model not in grouped:
                grouped[model] = schedule
            else:
                grouped[model] += schedule
        return grouped
