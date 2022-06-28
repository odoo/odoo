# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from datetime import datetime

from odoo import api, fields, models
from odoo.osv import expression


_logger = logging.getLogger(__name__)


class MailMessageScheduled(models.Model):
    """Mail message scheduled queue.

    This model is used to store the mail messages scheduled. So we can
    delay the sending of the notifications. A scheduled date field already
    exists on the <mail.mail> but it does not allow us to delay the sending
    of the <bus.bus> notifications.
    """
    _name = 'mail.message.scheduled'
    _description = 'Message Scheduled'
    _order = 'id DESC'
    _rec_name = 'message_id'

    message_id = fields.Many2one('mail.message', string='Message', ondelete='cascade')
    additionnal_parameters = fields.Text('Notification Parameter')

    scheduled_datetime = fields.Datetime(
        'Scheduled Send Date', required=True,
        help='When we should send the notification. If False, send them immediately.')

    @api.model
    def _send_notifications_cron(self):
        messages_scheduled = self.env['mail.message.scheduled'].search(
            expression.OR([
                [('scheduled_datetime', '=', False)],
                [('scheduled_datetime', '<=', datetime.utcnow())],
            ]),
        )

        _logger.info('Send %i scheduled messages', len(messages_scheduled))
        messages_scheduled._send_notifications()

    def _send_notifications(self):
        for message_scheduled in self:
            message = message_scheduled.message_id
            kwargs = json.loads(message_scheduled.additionnal_parameters)
            kwargs.pop('scheduled_datetime', None)

            if message.model:
                record = self.env[message.model].browse(message.res_id)
            else:
                record = self.env['mail.thread']

            record._notify_thread(message, **kwargs)

        self.unlink()
