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

# FP Note: can we remove some dependencies ? Use lint

import ast
import base64
import dateutil.parser
import email
import logging
import re
import time
import datetime
from email.header import decode_header
from email.message import Message

from openerp import SUPERUSER_ID
from osv import osv
from osv import fields
import pytz
from tools import DEFAULT_SERVER_DATETIME_FORMAT
from tools.translate import _
import tools

_logger = logging.getLogger(__name__)

""" Some tools for parsing / creating email fields """
def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])

def mail_tools_to_email(text):
    """Return a list of the email addresses found in ``text``"""
    if not text: return []
    return re.findall(r'([^ ,<@]+@[^> ,]+)', text)

class mail_message(osv.Model):
    """Model holding messages: system notification (replacing res.log
    notifications), comments (for OpenChatter feature). This model also
    provides facilities to parse new email messages. Type of messages are
    differentiated using the 'type' column. """

    _name = 'mail.message'
    _description = 'Message'
    _order = 'id desc'

    # FP Note: can we remove these two methods ?
    def open_document(self, cr, uid, ids, context=None):
        """ Open the message related document. Note that only the document of
            ids[0] will be opened.
            TODO: how to determine the action to use ?
        """
        action_data = False
        if not ids:
            return action_data
        msg = self.browse(cr, uid, ids[0], context=context)
        ir_act_window = self.pool.get('ir.actions.act_window')
        action_ids = ir_act_window.search(cr, uid, [('res_model', '=', msg.model)], context=context)
        if action_ids:
            action_data = ir_act_window.read(cr, uid, action_ids[0], context=context)
            action_data.update({
                    'domain' : "[('id', '=', %d)]" % (msg.res_id),
                    'nodestroy': True,
                    'context': {}
                    })
        return action_data

    def open_attachment(self, cr, uid, ids, context=None):
        """ Open the message related attachments.
            TODO: how to determine the action to use ?
        """
        action_data = False
        if not ids:
            return action_data
        action_pool = self.pool.get('ir.actions.act_window')
        messages = self.browse(cr, uid, ids, context=context)
        att_ids = [x.id for message in messages for x in message.attachment_ids]
        action_ids = action_pool.search(cr, uid, [('res_model', '=', 'ir.attachment')], context=context)
        if action_ids:
            action_data = action_pool.read(cr, uid, action_ids[0], context=context)
            action_data.update({
                'domain': [('id', 'in', att_ids)],
                'nodestroy': True
                })
        return action_data
    # END FP Note

    def get_record_name(self, cr, uid, ids, name, arg, context=None):
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if not message.model or not message.res_id:
                continue
            result[message.id] = self.pool.get(message.model).name_get(cr, uid, [message.res_id], context=context)[0][1]
        return result

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for message in self.browse(cr, uid, ids, context=context):
            name = ''
            if message.subject:
                name = '%s: ' % (message.subject)
            if message.body_text:
                name = name + message.body_text[0:20]
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

        # partner_id should be renamed into author_id
        'author_id': fields.many2one('res.partner', 'Author', required=True),

        # this is redundant with notifications ?
        'partner_ids': fields.many2many('res.partner',
            'mail_message_destination_partner_rel',
            'message_id', 'partner_id', 'Destination partners',
            help="When sending emails through the social network composition wizard"\
                 "you may choose to send a copy of the mail to partners."),

        # 'user_id': fields.many2one('res.users', 'Author', readonly=1),

        # why don't we attach the file to the message using res_id, res_model of the attachment ?
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),

        'parent_id': fields.many2one('mail.message', 'Parent Message',
            select=True, ondelete='set null',
            help="Parent message, used for displaying as threads with hierarchy"),
        'child_ids': fields.one2many('mail.message', 'parent_id', 'Child Messages'),


        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'record_name': fields.function(get_record_name, type='string',
            string='Message Record Name',
            help="Name get of the related document."),

        'subject': fields.char('Subject', size=128),
        'date': fields.datetime('Date'),

        # FP Note: do we need this ?
        'references': fields.text('References', help='Message references, such as identifiers of previous messages', readonly=1),

        # END FP Note

        'message_id': fields.char('Message-Id', size=256, help='Message unique identifier', select=1, readonly=1),
        'body': fields.text('Content', help="Content of Message", required=True),

    }
    _defaults = {
        'type': 'email',
        'date': (lambda *a: fields.datetime.now()),
    }

    #------------------------------------------------------
    # Email api
    #------------------------------------------------------

    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def check(self, cr, uid, ids, mode, context=None):
        """Restricts the access to a mail.message, according to referred model
        """
        if not ids:
            return
        res_ids = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        cr.execute('SELECT DISTINCT model, res_id FROM mail_message WHERE id = ANY (%s)', (ids,))
        for rmod, rid in cr.fetchall():
            if not (rmod and rid):
                continue
            res_ids.setdefault(rmod,set()).add(rid)

        ima_obj = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore mail messages that are not attached to a resource anymore when checking access rights
            # (resource was deleted but message was not)
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
            for follower in modobj.follower_ids:
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
        default.update(message_id=False, original=False, headers=False)
        return super(mail_message,self).copy(cr, uid, id, default=default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        result = super(mail_message, self).write(cr, uid, ids, vals, context)
        self.check(cr, uid, ids, 'write', context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        self.check(cr, uid, ids, 'unlink', context=context)
        return super(mail_message, self).unlink(cr, uid, ids, context)

    # FP Note: to be simplified, mail.message fields only, not mail.mail
    def parse_message(self, message, save_original=False, context=None):
        """Parses a string or email.message.Message representing an
           RFC-2822 email, and returns a generic dict holding the
           message details.

           :param message: the message to parse
           :type message: email.message.Message | string | unicode
           :param bool save_original: whether the returned dict
               should include an ``original`` entry with the base64
               encoded source of the message.
           :rtype: dict
           :return: A dict with the following structure, where each
                    field may not be present if missing in original
                    message::

                    { 'message-id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'headers' : { 'X-Mailer': mailer,
                                    #.. all X- headers...
                                  },
                      'content_subtype': msg_mime_subtype,
                      'body_text': plaintext_body
                      'body_html': html_body,
                      'attachments': [('file1', 'bytes'),
                                       ('file2', 'bytes') }
                       # ...
                       'original': source_of_email,
                    }
        """
        msg_txt = message
        if isinstance(message, str):
            msg_txt = email.message_from_string(message)

        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            msg_txt = email.message_from_string(message)

        message_id = msg_txt.get('message-id', False)
        msg = {}

        if save_original:
            # save original, we need to be able to read the original email sometimes
            msg['original'] = message.as_string() if isinstance(message, Message) \
                                                  else message
            msg['original'] = base64.b64encode(msg['original']) # binary fields are b64

        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['message-id'] = message_id
            _logger.info('Parsing Message without message-id, generating a random one: %s', message_id)

        msg_fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id

        if 'Subject' in msg_fields:
            msg['subject'] = decode(msg_txt.get('Subject'))

        if 'Content-Type' in msg_fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in msg_fields:
            msg['from'] = decode(msg_txt.get('From') or msg_txt.get_unixfrom())

        if 'To' in msg_fields:
            msg['to'] = decode(msg_txt.get('To'))

        if 'Delivered-To' in msg_fields:
            msg['to'] = decode(msg_txt.get('Delivered-To'))

        if 'CC' in msg_fields:
            msg['cc'] = decode(msg_txt.get('CC'))

        if 'Cc' in msg_fields:
            msg['cc'] = decode(msg_txt.get('Cc'))

        if 'Reply-To' in msg_fields:
            msg['reply'] = decode(msg_txt.get('Reply-To'))

        if 'Date' in msg_fields:
            date_hdr = decode(msg_txt.get('Date'))
            # convert from email timezone to server timezone
            date_server_datetime = dateutil.parser.parse(date_hdr).astimezone(pytz.timezone(tools.get_server_timezone()))
            date_server_datetime_str = date_server_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            msg['date'] = date_server_datetime_str

        if 'Content-Transfer-Encoding' in msg_fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in msg_fields:
            msg['references'] = msg_txt.get('References')

        if 'In-Reply-To' in msg_fields:
            msg['in-reply-to'] = msg_txt.get('In-Reply-To')

        msg['headers'] = {}
        msg['content_subtype'] = 'plain'
        for item in msg_txt.items():
            if item[0].startswith('X-'):
                msg['headers'].update({item[0]: item[1]})
        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            body = msg_txt.get_payload(decode=True)
            if 'text/html' in msg.get('content-type', ''):
                msg['body_html'] =  body
                msg['content_subtype'] = 'html'
                if body:
                    body = tools.html2plaintext(body)
            msg['body_text'] = tools.ustr(body, encoding)

        attachments = []
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', ''):
            body = ""
            if 'multipart/alternative' in msg.get('content-type', ''):
                msg['content_subtype'] = 'alternative'
            else:
                msg['content_subtype'] = 'mixed'
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                encoding = part.get_content_charset()
                filename = part.get_filename()
                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    if filename:
                        attachments.append((filename, content))
                    content = tools.ustr(content, encoding)
                    if part.get_content_subtype() == 'html':
                        msg['body_html'] = content
                        msg['content_subtype'] = 'html' # html version prevails
                        body = tools.ustr(tools.html2plaintext(content))
                        body = body.replace('&#13;', '')
                    elif part.get_content_subtype() == 'plain':
                        body = content
                elif part.get_content_maintype() in ('application', 'image'):
                    if filename :
                        attachments.append((filename,part.get_payload(decode=True)))
                    else:
                        res = part.get_payload(decode=True)
                        body += tools.ustr(res, encoding)

            msg['body_text'] = body
        msg['attachments'] = attachments

        # for backwards compatibility:
        msg['body'] = msg['body_text']
        msg['sub_type'] = msg['content_subtype'] or 'plain'
        return msg


