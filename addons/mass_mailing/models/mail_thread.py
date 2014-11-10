# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import logging
import re

from openerp.addons.mail.mail_message import decode
from openerp.addons.mail.mail_thread import decode_header
from openerp.osv import osv

_logger = logging.getLogger(__name__)


class MailThread(osv.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied emails
    in message_process. """
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    def message_route_check_bounce(self, cr, uid, message, context=None):
        """ Override to verify that the email_to is the bounce alias. If it is the
        case, log the bounce, set the parent and related document as bounced and
        return False to end the routing process. """
        bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')

        # 0. Verify whether this is a bounced email (wrong destination,...) -> use it to collect data, such as dead leads
        if bounce_alias in email_to:
            # Bounce regex
            # Typical form of bounce is bounce_alias-128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
            bounce_re = re.compile("%s-(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                bounced_model, bounced_thread_id = None, False
                bounced_mail_id = bounce_match.group(1)
                stat_ids = self.pool['mail.mail.statistics'].set_bounced(cr, uid, mail_mail_ids=[bounced_mail_id], context=context)
                for stat in self.pool['mail.mail.statistics'].browse(cr, uid, stat_ids, context=context):
                    bounced_model = stat.model
                    bounced_thread_id = stat.res_id
                _logger.info('Routing mail from %s to %s with Message-Id %s: bounced mail from mail %s, model: %s, thread_id: %s',
                             email_from, email_to, message_id, bounced_mail_id, bounced_model, bounced_thread_id)
                if bounced_model and bounced_model in self.pool and hasattr(self.pool[bounced_model], 'message_receive_bounce') and bounced_thread_id:
                    self.pool[bounced_model].message_receive_bounce(cr, uid, [bounced_thread_id], mail_id=bounced_mail_id, context=context)
                return False

        return True

    def message_route(self, cr, uid, message, message_dict, model=None, thread_id=None,
                      custom_values=None, context=None):
        if not self.message_route_check_bounce(cr, uid, message, context=context):
            return []
        return super(MailThread, self).message_route(cr, uid, message, message_dict, model, thread_id, custom_values, context)

    def message_receive_bounce(self, cr, uid, ids, mail_id=None, context=None):
        """Called by ``message_process`` when a bounce email (such as Undelivered
        Mail Returned to Sender) is received for an existing thread. The default
        behavior is to check is an integer  ``message_bounce`` column exists.
        If it is the case, its content is incremented. """
        if 'message_bounce' in self._fields:
            for obj in self.browse(cr, uid, ids, context=context):
                self.write(cr, uid, [obj.id], {'message_bounce': obj.message_bounce + 1}, context=context)

    def message_route_process(self, cr, uid, message, message_dict, routes, context=None):
        """ Override to update the parent mail statistics. The parent is found
        by using the References header of the incoming message and looking for
        matching message_id in mail.mail.statistics. """
        if message.get('References'):
            message_ids = [x.strip() for x in decode(message['References']).split()]
            self.pool['mail.mail.statistics'].set_replied(cr, uid, mail_message_ids=message_ids, context=context)
        return super(MailThread, self).message_route_process(cr, uid, message, message_dict, routes, context=context)
