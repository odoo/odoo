# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, models

from odoo.addons.mail.models.mail_message import decode
from odoo.addons.mail.models.mail_thread import decode_header


_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied emails
    in message_process. """
    _inherit = 'mail.thread'

    def message_route_check_bounce(self, message):
        """ Override to verify that the email_to is the bounce alias. If it is the
        case, log the bounce, set the parent and related document as bounced and
        return False to end the routing process. """
        bounce_alias = self.env['ir.config_parameter'].get_param("mail.bounce.alias")
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')

        # 0. Verify whether this is a bounced email (wrong destination,...) -> use it to collect data, such as dead leads
        if bounce_alias and bounce_alias in email_to:
            # Bounce regex
            # Typical form of bounce is bounce_alias-128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
            bounce_re = re.compile("%s-(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                bounced_model, bounced_thread_id = None, False
                bounced_mail_id = bounce_match.group(1)
                statistics = self.env['mail.mail.statistics'].set_bounced(mail_mail_ids=[bounced_mail_id])
                for stat in statistics:
                    bounced_model = stat.model
                    bounced_thread_id = stat.res_id
                _logger.info('Routing mail from %s to %s with Message-Id %s: bounced mail from mail %s, model: %s, thread_id: %s',
                             email_from, email_to, message_id, bounced_mail_id, bounced_model, bounced_thread_id)
                if bounced_model and bounced_model in self.pool and hasattr(self.env[bounced_model], 'message_receive_bounce') and bounced_thread_id:
                    self.env[bounced_model].browse(bounced_thread_id).message_receive_bounce(mail_id=bounced_mail_id)
                return False

        return True

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        if not self.message_route_check_bounce(message):
            return []
        return super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)

    def message_receive_bounce(self, mail_id=None):
        """Called by ``message_process`` when a bounce email (such as Undelivered
        Mail Returned to Sender) is received for an existing thread. The default
        behavior is to check is an integer  ``message_bounce`` column exists.
        If it is the case, its content is incremented. """
        if 'message_bounce' in self._fields:
            for mail_thread in self:
                mail_thread.message_bounce = mail_thread.message_bounce + 1

    @api.model
    def message_route_process(self, message, message_dict, routes):
        """ Override to update the parent mail statistics. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mail.mail.statistics. """
        if message.get('References'):
            message_ids = [x.strip() for x in decode(message['References']).split()]
            self.env['mail.mail.statistics'].set_replied(mail_message_ids=message_ids)
        return super(MailThread, self).message_route_process(message, message_dict, routes)
