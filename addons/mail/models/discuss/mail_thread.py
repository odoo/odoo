# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, fields
from odoo.addons.phone_validation.tools import phone_validation
from odoo.tools import html2plaintext, plaintext2html

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        message_format = message.message_format()[0]
        message_format = dict(message_format or message.message_format()[0])
        notifications = []
        for thread in self:
            payload = {
                'message': message_format,
                'thread_id': thread.id,
                'thread_model': thread._name,
            }
            notifications.append(('/discuss/thread/'+ thread._name + '/' + thread.id, 'discuss/new_message', payload))
        notifications
        self.env['bus.bus'].sudo()._sendmany(notifications)
        return rdata
