# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
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

import dateutil.parser
import email
import logging
import re
import time
from email.header import decode_header
from email.message import Message

from osv import osv
from osv import fields
import tools

_logger = logging.getLogger(__name__)

""" Some tools for parsing / creating email fields """
def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])

class mail_message(osv.Model):
    """Model holding messages: system notification (replacing res.log
    notifications), comments (for OpenChatter feature). This model also
    provides facilities to parse new email messages. Type of messages are
    differentiated using the 'type' column. """

    _name = 'mail.message'
    _description = 'Message'
    _inherit = ['ir.needaction_mixin']
    _order = 'id desc'

    def get_record_name(self, cr, uid, ids, name, arg, context=None):
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if not message.model or not message.res_id:
                continue
            result[message.id] = self.pool.get(message.model).name_get(cr, uid, [message.res_id], context=context)[0][1]
        return result

    def name_get(self, cr, uid, ids, context=None):
        # name_get may receive int id instead of an id list
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for message in self.browse(cr, uid, ids, context=context):
            name = ''
            if message.subject:
                name = '%s: ' % (message.subject)
            if message.body:
                name = name + message.body[0:20]
            res.append((message.id, name))
        return res

    _columns = {
        # should we keep a distinction between email and comment ?
        'type': fields.selection([
                        ('email', 'email'),
                        ('comment', 'Comment'),
                        ('notification', 'System notification'),
                        ], 'Type',
            help="Message type: email for email message, notification for system "\
                  "message, comment for other messages such as user replies"),

        'author_id': fields.many2one('res.partner', 'Author', required=True),
        'partner_ids': fields.many2many('res.partner',
            'mail_notification', 'message_id', 'partner_id',
            'Recipients'),

        'attachment_ids': fields.one2many('ir.attachment', 'res_id',
            'Attachments', domain=[('res_model','=','mail.message')]),

        'parent_id': fields.many2one('mail.message', 'Parent Message',
            select=True, ondelete='set null',
            help="Initial thread message."),
        'child_ids': fields.one2many('mail.message', 'parent_id', 'Child Messages'),

        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'record_name': fields.function(get_record_name, type='string',
            string='Message Record Name',
            help="Name get of the related document."),

        'notification_ids': fields.one2many('mail.notification', 'message_id', 'Notifications'),
        'subject': fields.char('Subject', size=128),
        'date': fields.datetime('Date'),
        'message_id': fields.char('Message-Id', size=256, help='Message unique identifier', select=1, readonly=1),
        'body': fields.html('Content'),
    }

    def _get_default_author(self, cr, uid, context={}):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id

    _defaults = {
        'type': 'email',
        'date': lambda *a: fields.datetime.now(),
        'author_id': _get_default_author
    }


    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    _limit = 3
    def _message_dict_get(self, cr, uid, msg, context={}):
        attachs = self.pool.get('ir.attachment').name_get(cr, uid, [x.id for x in msg.attachment_ids], context=context)
        author = self.pool.get('res.partner').name_get(cr, uid, [msg.author_id.id], context=context)[0]
        # TDE: need user to show 'delete' link -> necessary ?
        author_user = self.pool.get('res.users').name_get(cr, uid, [x.id for x in msg.author_id.user_ids], context=context)[0]
        partner_ids = self.pool.get('res.partner').name_get(cr, uid, [x.id for x in msg.partner_ids], context=context)
        return {
            'id': msg.id,
            'type': msg.type,
            'attachment_ids': attachs,
            'body': msg.body,
            'model': msg.model,
            'res_id': msg.res_id,
            'record_name': msg.record_name,
            'subject': msg.subject,
            'date': msg.date,
            'author_id': author,
            'author_user_id': author_user,
            'partner_ids': partner_ids,
            'child_ids': []
        }

    def message_read(self, cr, uid, ids=False, domain=[], thread_level=0, context=None):
        """ 
            If IDS are provided, fetch these records, otherwise use the domain to
            fetch the matching records. After having fetched the records provided
            by IDS, it will fetch children (according to thread_level).
            
            Return [
            
            ]
        """
        context = context or {}
        if ids is False:
            ids = self.search(cr, uid, domain, context=context, limit=10)

        # FP Todo: flatten to max X level of mail_thread
        messages = self.browse(cr, uid, ids, context=context)

        result = []
        tree = {} # key: ID, value: record
        for msg in messages:
            if len(result)<(self._limit-1):
                record = self._message_dict_get(cr, uid, msg, context=context)
                if thread_level and msg.parent_id:
                    while msg.parent_id:
                        if msg.parent_id.id in tree:
                            record_parent = tree[msg.parent_id.id]
                        else:
                            record_parent = self._message_dict_get(cr, uid, msg.parent_id, context=context)
                            if msg.parent_id.parent_id:
                                tree[msg.parent_id.id] = record_parent
                        record_parent['child_ids'].append(record)
                        record = record_parent
                        msg = msg.parent_id
                if msg.id not in tree:
                    result.append(record)
                    tree[msg.id] = record
            else:
                result.append({
                    'type': 'expandable',
                    'domain': [('id','<=', msg.id)]+domain,
                    'context': context,
                    'thread_level': thread_level  # should be improve accodting to level of records
                })
                break
        return result


    #------------------------------------------------------
    # Email api
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def check(self, cr, uid, ids, mode, context=None):
        """
        You can read/write a message if:
          - you received it (a notification exists) or
          - you can read the related document (res_model, res_id)
        If a message is not attached to a document, normal access rights on
        the mail.message object apply.
        """
        if not ids:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]

        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id

        # check messages for which you have a notification
        not_obj = self.pool.get('mail.notification')
        not_ids = not_obj.search(cr, uid, [
            ('partner_id', '=', partner_id),
            ('message_id', 'in', ids),
        ], context=context)
        notifications = {}
        for notification in not_obj.browse(cr, uid, not_ids, context=context):
            if notification.message_id.id in ids:
                pass
                # FO Note: we should put this again !!!
                #ids.remove(notification.message_id.id)

        # check messages according to related documents
        res_ids = {}
        cr.execute('SELECT DISTINCT model, res_id FROM mail_message WHERE id = ANY (%s)', (ids,))
        for rmod, rid in cr.fetchall():
            if not (rmod and rid):
                continue
            res_ids.setdefault(rmod,set()).add(rid)

        ima_obj = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            mids = self.pool.get(model).exists(cr, uid, mids)
            ima_obj.check(cr, uid, model, mode)
            self.pool.get(model).check_access_rule(cr, uid, mids, mode, context=context)

    def create(self, cr, uid, values, context=None):
        newid = super(mail_message, self).create(cr, uid, values, context)
        self.check(cr, uid, [newid], mode='create', context=context)

        # notify all followers
        if values.get('model') and values.get('res_id'):
            notification_obj = self.pool.get('mail.notification')
            modobj = self.pool.get(values.get('model'))
            follower_notify = []
            for follower in modobj.browse(cr, uid, values.get('res_id'), context=context).message_follower_ids:
                if follower.id <> uid:
                    follower_notify.append(follower.id)
            self.pool.get('mail.notification').notify(cr, uid, follower_notify, newid, context=context)
        return newid

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        self.check(cr, uid, ids, 'read', context=context)
        return super(mail_message, self).read(cr, uid, ids, fields_to_read, context, load)

    def copy(self, cr, uid, id, default=None, context=None):
        """Overridden to avoid duplicating fields that are unique to each email"""
        if default is None:
            default = {}
        self.check(cr, uid, [id], 'read', context=context)
        default.update(message_id=False, headers=False)
        return super(mail_message,self).copy(cr, uid, id, default=default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        result = super(mail_message, self).write(cr, uid, ids, vals, context)
        self.check(cr, uid, ids, 'write', context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        self.check(cr, uid, ids, 'unlink', context=context)
        return super(mail_message, self).unlink(cr, uid, ids, context)


class mail_notification(osv.Model):
    """ mail_notification is a relational table modeling messages pushed to partners.
    """
    _inherit = 'mail.notification'
    _columns = {
        'message_id': fields.many2one('mail.message', string='Message',
                        ondelete='cascade', required=True, select=1),
    }


