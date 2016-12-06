# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import decode_smtp_header, decode_message_header


class MailThread(models.AbstractModel):
    """ Update MailThread to add the support of bounce management in mass mailing statistics. """
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Override to udpate mass mailing statistics based on bounce emails """
        email_to = decode_message_header(message, 'To')
        bounced_mail_id, _, _ = self._extract_bounce_info(email_to)
        if bounced_mail_id:
            self.env['mail.mail.statistics'].set_bounced(mail_mail_ids=[bounced_mail_id])

        return super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)

    @api.model
    def message_route_process(self, message, message_dict, routes):
        """ Override to update the parent mail statistics. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mail.mail.statistics. """
        if message.get('References'):
            message_ids = [x.strip() for x in decode_smtp_header(message['References']).split()]
            self.env['mail.mail.statistics'].set_replied(mail_message_ids=message_ids)
        return super(MailThread, self).message_route_process(message, message_dict, routes)
