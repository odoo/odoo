# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
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

from osv import osv
from osv import fields

class mail_followers(osv.Model):
    """ mail_followers holds the data related to the follow mechanism inside
    OpenERP. Partners can choose to follow documents (records) of any kind that
    inherits from mail.thread. Following documents allow to receive
    notifications for new messages.
    A subscription is characterized by:
        :param: res_model: model of the followed objects
        :param: res_id: ID of resource (may be 0 for every objects)
    """
    _name = 'mail.followers'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Document Followers'
    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'partner_id': fields.many2one('res.partner', string='Related Partner',
                        ondelete='cascade', required=True, select=1),
    }


class mail_notification(osv.Model):
    _name = 'mail.notification'
    _rec_name = 'partner_id'
    _log_access = False
    _description = 'Notifications'
    _columns = {
        'partner_id': fields.many2one('res.partner', string='Contact',
                        ondelete='cascade', required=True, select=1),
        'read': fields.boolean('Read'),
        # this will be added in mail_message.py
        #'message_id': fields.many2one('mail.message', string='Message',
        #                ondelete='cascade', required=True, select=1),
    }
    _defaults = {
        'read': False,
    }
    # FP Note: todo: check that we can not create a notification for
    # a message we can not read.
    # def create(self, ...)


    # Create notification in the wall of each user
    # Send by email the notification depending on the user preferences
    def notify(self, cr, uid, partner_ids, msg_id, context=None):
        context = context or {}
        partner_obj = self.pool.get('res.partner')
        msg_obj = self.pool.get('mail.message')
        msg = msg_obj.browse(cr, uid, msg_id, context=context)

        towrite = {
            'email_to': '',
            'subject': msg.subject
        }
        for partner in partner_obj.browse(cr, uid, partner_ids, context=context):
            notification_obj.create(cr, uid, {
                'partner_id': partner.id,
                'message_id': msg_id
            }, context=context)
            if partner.notification_email_pref=='none' or not partner.email:
                continue

            if partner.notification_email_pref=='comment' and msg.type in ('email','comment'):
                continue

            if not msg.email_from:
                current_user = res_users_obj.browse(cr, uid, uid, context=context)
                towrite['email_from'] = current_user.email

            towrite['state'] = 'outgoing'
            if not towrite.get('email_to', False):
                towrite['email_to'] = email_to
            else:
                if email_to not in towrite['email_to']:
                    towrite['email_to'] = towrite['email_to'] + ', ' + email_to

        if towrite.get('state', False) and not context.get('noemail', False):
            if towrite.get('subject', False):
                towrite['subject'] = msg.name_get(cr, uid, [msg.id], context=context)[0][1]
            towrite['message_id'] = msg.id
            self.pool.get('mail.mail').create(cr, uid, towrite, context=context)
        return True


