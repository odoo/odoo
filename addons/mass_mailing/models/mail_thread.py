# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import osv
from openerp.tools import decode_smtp_header

_logger = logging.getLogger(__name__)


class MailThread(osv.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied emails
    in message_process. """
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    def message_route_process(self, cr, uid, message, message_dict, routes, context=None):
        """ Override to update the parent mail statistics. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mail.mail.statistics. """
        if message.get('References'):
            message_ids = [x.strip() for x in decode_smtp_header(message['References']).split()]
            self.pool['mail.mail.statistics'].set_replied(cr, uid, mail_message_ids=message_ids, context=context)
        return super(MailThread, self).message_route_process(cr, uid, message, message_dict, routes, context=context)
