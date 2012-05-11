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

import tools
from osv import osv
from osv import fields
from tools.translate import _
from openerp import SUPERUSER_ID

_logger = logging.getLogger('mail')

def format_date_tz(date, tz=None):
    if not date:
        return 'n/a'
    format = tools.DEFAULT_SERVER_DATETIME_FORMAT
    return tools.server_to_local_timestamp(date, format, format, tz)

def truncate_text(text):
    lines = text and text.split('\n') or []
    if len(lines) > 3:
        res = '\n\t'.join(lines[:3]) + '...'
    else:
        res = '\n\t'.join(lines)
    return res

def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])

def to_email(text):
    """Return a list of the email addresses found in ``text``"""
    if not text: return []
    return re.findall(r'([^ ,<@]+@[^> ,]+)', text)

class mail_message_common(osv.osv_memory):
    """Common abstract class for holding the main attributes of a 
       message object. It could be reused as parent model for any
       database model or wizard screen that needs to hold a kind of
       message"""

    def get_body(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if message.subtype == 'html':
                result[message.id] = message.body_html
            else:
                result[message.id] = message.body_text
        return result
    
    def search_body(self, cr, uid, obj, name, args, context=None):
        """will receive:
           - obj: mail.message object
           - name: 'body'
           - args: [('body', 'ilike', 'blah')]"""
        return ['|', '&', ('subtype', '=', 'html'), ('body_html', args[0][1], args[0][2]), ('body_text', args[0][1], args[0][2])]
    
    def get_record_name(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids, '')
        for message in self.browse(cr, uid, ids, context=context):
            if not message.model or not message.res_id:
                continue
            result[message.id] = self.pool.get(message.model).name_get(cr, uid, [message.res_id], context=context)[0][1]
        return result
    
    _name = 'mail.message.common'
    _rec_name = 'subject'
    _columns = {
        'subject': fields.char('Subject', size=512, required=True),
        'model': fields.char('Related Document Model', size=128, select=1),
        'res_id': fields.integer('Related Document ID', select=1),
        'record_name': fields.function(get_record_name, type='string', string='Message Record Name',
                        help="Name of the record, matching the result of the name_get."),
        'date': fields.datetime('Date'),
        'email_from': fields.char('From', size=128, help='Message sender, taken from user preferences.'),
        'email_to': fields.char('To', size=256, help='Message recipients'),
        'email_cc': fields.char('Cc', size=256, help='Carbon copy message recipients'),
        'email_bcc': fields.char('Bcc', size=256, help='Blind carbon copy message recipients'),
        'reply_to':fields.char('Reply-To', size=256, help='Preferred response address for the message'),
        'headers': fields.text('Message Headers', readonly=1,
                        help="Full message headers, e.g. SMTP session headers (usually available on inbound messages only)"),
        'message_id': fields.char('Message-Id', size=256, help='Message unique identifier', select=1, readonly=1),
        'references': fields.text('References', help='Message references, such as identifiers of previous messages', readonly=1),
        'subtype': fields.char('Message Type', size=32, help="Type of message, usually 'html' or 'plain', used to "
                                                             "select plaintext or rich text contents accordingly", readonly=1),
        'body_text': fields.text('Text Contents', help="Plain-text version of the message"),
        'body_html': fields.text('Rich-text Contents', help="Rich-text/HTML version of the message"),
        'body': fields.function(get_body, fnct_search = search_body, string='Message Content', type='text',
                        help="Content of the message. This content equals the body_text field for plain-test messages, and body_html for rich-text/HTML messages. This allows having one field if we want to access the content matching the message subtype."),
        'parent_id': fields.many2one('mail.message', 'Parent Message', help="Parent message, used for displaying as threads with hierarchy",
                        select=True, ondelete='set null',),
        'child_ids': fields.one2many('mail.message', 'parent_id', 'Child Messages'),
    }

    _defaults = {
        'subtype': 'plain',
        'date': (lambda *a: fields.datetime.now()),
    }

class mail_message(osv.osv):
    '''Model holding messages: system notification (replacing res.log
       notifications), comments (for OpenSocial feature) and
       RFC2822 email messages. This model also provides facilities to
       parse, queue and send new email messages. Type of messages
       are differentiated using the 'type' column.
       
       The ``display_text`` field will have a slightly different
       presentation for real emails and for log messages.
       '''

    _name = 'mail.message'
    _inherit = 'mail.message.common'
    _description = 'Mail Message (email, comment, notification)'
    _order = 'date desc'

    # XXX to review - how to determine action to use?
    def open_document(self, cr, uid, ids, context=None):
        action_data = False
        if ids:
            msg = self.browse(cr, uid, ids[0], context=context)
            model = msg.model
            res_id = msg.res_id

            ir_act_window = self.pool.get('ir.actions.act_window')
            action_ids = ir_act_window.search(cr, uid, [('res_model', '=', model)])
            if action_ids:
                action_data = ir_act_window.read(cr, uid, action_ids[0], context=context)
                action_data.update({
                    'domain' : "[('id','=',%d)]"%(res_id),
                    'nodestroy': True,
                    'context': {}
                    })
        return action_data

    # XXX to review - how to determine action to use?
    def open_attachment(self, cr, uid, ids, context=None):
        action_data = False
        action_pool = self.pool.get('ir.actions.act_window')
        message = self.browse(cr, uid, ids, context=context)[0]
        att_ids = [x.id for x in message.attachment_ids]
        action_ids = action_pool.search(cr, uid, [('res_model', '=', 'ir.attachment')])
        if action_ids:
            action_data = action_pool.read(cr, uid, action_ids[0], context=context)
            action_data.update({
                'domain': [('id','in',att_ids)],
                'nodestroy': True
                })
        return action_data

    def _get_display_text(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        tz = context.get('tz')
        result = {}

        # Read message as UID 1 to allow viewing author even if from different company
        for message in self.browse(cr, SUPERUSER_ID, ids):
            msg_txt = ''
            if message.email_from:
                msg_txt += _('%s wrote on %s: \n Subject: %s \n\t') % (message.email_from or '/', format_date_tz(message.date, tz), message.subject)
                if message.body_text:
                    msg_txt += truncate_text(message.body_text)
            else:
                msg_txt = (message.user_id.name or '/') + _(' on ') + format_date_tz(message.date, tz) + ':\n\t'
                msg_txt += (message.subject or '')
            result[message.id] = msg_txt
        return result
    
    _columns = {
        'type': fields.selection([
                        ('email', 'e-mail'),
                        ('comment', 'Comment'),
                        ('notification', 'System notification'),
                        ], 'Type', help="Message type: e-mail for e-mail message, notification for system message, comment for other messages such as user replies"),
        'partner_id': fields.many2one('res.partner', 'Related partner'),
        'user_id': fields.many2one('res.users', 'Related User', readonly=1),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),
        'display_text': fields.function(_get_display_text, method=True, type='text', size="512", string='Display Text'),
        'mail_server_id': fields.many2one('ir.mail_server', 'Outgoing mail server', readonly=1),
        'state': fields.selection([
                        ('outgoing', 'Outgoing'),
                        ('sent', 'Sent'),
                        ('received', 'Received'),
                        ('exception', 'Delivery Failed'),
                        ('cancel', 'Cancelled'),
                        ], 'State', readonly=True),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete this email after sending it, to save space"),
        'original': fields.binary('Original', help="Original version of the message, as it was sent on the network", readonly=1),
    }
        
    _defaults = {
        'type': 'email',
        'state': 'received',
    }
    
    #------------------------------------------------------
    # E-Mail api
    #------------------------------------------------------
    
    def init(self, cr):
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    def copy(self, cr, uid, id, default=None, context=None):
        """Overridden to avoid duplicating fields that are unique to each email"""
        if default is None:
            default = {}
        default.update(message_id=False,original=False,headers=False)
        return super(mail_message,self).copy(cr, uid, id, default=default, context=context)

    def schedule_with_attach(self, cr, uid, email_from, email_to, subject, body, model=False, email_cc=None,
                             email_bcc=None, reply_to=False, attachments=None, message_id=False, references=False,
                             res_id=False, subtype='plain', headers=None, mail_server_id=False, auto_delete=False,
                             context=None):
        """Schedule sending a new email message, to be sent the next time the mail scheduler runs, or
           the next time :meth:`process_email_queue` is called explicitly.

           :param string email_from: sender email address
           :param list email_to: list of recipient addresses (to be joined with commas) 
           :param string subject: email subject (no pre-encoding/quoting necessary)
           :param string body: email body, according to the ``subtype`` (by default, plaintext).
                               If html subtype is used, the message will be automatically converted
                               to plaintext and wrapped in multipart/alternative.
           :param list email_cc: optional list of string values for CC header (to be joined with commas)
           :param list email_bcc: optional list of string values for BCC header (to be joined with commas)
           :param string model: optional model name of the document this mail is related to (this will also
                                be used to generate a tracking id, used to match any response related to the
                                same document)
           :param int res_id: optional resource identifier this mail is related to (this will also
                              be used to generate a tracking id, used to match any response related to the
                              same document)
           :param string reply_to: optional value of Reply-To header
           :param string subtype: optional mime subtype for the text body (usually 'plain' or 'html'),
                                  must match the format of the ``body`` parameter. Default is 'plain',
                                  making the content part of the mail "text/plain".
           :param dict attachments: map of filename to filecontents, where filecontents is a string
                                    containing the bytes of the attachment
           :param dict headers: optional map of headers to set on the outgoing mail (may override the
                                other headers, including Subject, Reply-To, Message-Id, etc.)
           :param int mail_server_id: optional id of the preferred outgoing mail server for this mail
           :param bool auto_delete: optional flag to turn on auto-deletion of the message after it has been
                                    successfully sent (default to False)

        """
        if context is None:
            context = {}
        if attachments is None:
            attachments = {}
        attachment_obj = self.pool.get('ir.attachment')
        for param in (email_to, email_cc, email_bcc):
            if param and not isinstance(param, list):
                param = [param]
        msg_vals = {
                'subject': subject,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': uid,
                'model': model,
                'res_id': res_id,
                'type': 'email',
                'body_text': body if subtype != 'html' else False,
                'body_html': body if subtype == 'html' else False,
                'email_from': email_from,
                'email_to': email_to and ','.join(email_to) or '',
                'email_cc': email_cc and ','.join(email_cc) or '',
                'email_bcc': email_bcc and ','.join(email_bcc) or '',
                'reply_to': reply_to,
                'message_id': message_id,
                'references': references,
                'subtype': subtype,
                'headers': headers, # serialize the dict on the fly
                'mail_server_id': mail_server_id,
                'state': 'outgoing',
                'auto_delete': auto_delete
            }
        email_msg_id = self.create(cr, uid, msg_vals, context)
        attachment_ids = []
        for fname, fcontent in attachments.iteritems():
            attachment_data = {
                    'name': fname,
                    'datas_fname': fname,
                    'datas': fcontent and fcontent.encode('base64'),
                    'res_model': self._name,
                    'res_id': email_msg_id,
            }
            if context.has_key('default_type'):
                del context['default_type']
            attachment_ids.append(attachment_obj.create(cr, uid, attachment_data, context))
        if attachment_ids:
            self.write(cr, uid, email_msg_id, { 'attachment_ids': [(6, 0, attachment_ids)]}, context=context)
        return email_msg_id

    def mark_outgoing(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'outgoing'}, context)

    def process_email_queue(self, cr, uid, ids=None, context=None):
        """Send immediately queued messages, committing after each
           message is sent - this is not transactional and should
           not be called during another transaction!

           :param list ids: optional list of emails ids to send. If passed
                            no search is performed, and these ids are used
                            instead.
           :param dict context: if a 'filters' key is present in context,
                                this value will be used as an additional
                                filter to further restrict the outgoing
                                messages to send (by default all 'outgoing'
                                messages are sent).
        """
        if context is None:
            context = {}
        if not ids:
            filters = [('state', '=', 'outgoing')]
            if 'filters' in context:
                filters.extend(context['filters'])
            ids = self.search(cr, uid, filters, context=context)
        res = None
        try:
            # Force auto-commit - this is meant to be called by
            # the scheduler, and we can't allow rolling back the status
            # of previously sent emails!
            res = self.send(cr, uid, ids, auto_commit=True, context=context)
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

    def parse_message(self, message, save_original=False):
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
                      'subtype': msg_mime_subtype,
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

        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id

        if 'Subject' in fields:
            msg['subject'] = decode(msg_txt.get('Subject'))

        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in fields:
            msg['from'] = decode(msg_txt.get('From') or msg_txt.get_unixfrom())

        if 'To' in fields:
            msg['to'] = decode(msg_txt.get('To'))

        if 'Delivered-To' in fields:
            msg['to'] = decode(msg_txt.get('Delivered-To'))

        if 'CC' in fields:
            msg['cc'] = decode(msg_txt.get('CC'))

        if 'Cc' in fields:
            msg['cc'] = decode(msg_txt.get('Cc'))

        if 'Reply-To' in fields:
            msg['reply'] = decode(msg_txt.get('Reply-To'))

        if 'Date' in fields:
            date_hdr = decode(msg_txt.get('Date'))
            msg['date'] = dateutil.parser.parse(date_hdr).strftime("%Y-%m-%d %H:%M:%S")

        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'In-Reply-To' in fields:
            msg['in-reply-to'] = msg_txt.get('In-Reply-To')

        msg['headers'] = {}
        msg['subtype'] = 'plain'
        for item in msg_txt.items():
            if item[0].startswith('X-'):
                msg['headers'].update({item[0]: item[1]})
        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            body = msg_txt.get_payload(decode=True)
            if 'text/html' in msg.get('content-type', ''):
                msg['body_html'] =  body
                msg['subtype'] = 'html'
                if body:
                    body = tools.html2plaintext(body)
            msg['body_text'] = tools.ustr(body, encoding)

        attachments = []
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', ''):
            body = ""
            if 'multipart/alternative' in msg.get('content-type', ''):
                msg['subtype'] = 'alternative'
            else:
                msg['subtype'] = 'mixed'
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
                        msg['subtype'] = 'html' # html version prevails
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
        msg['sub_type'] = msg['subtype'] or 'plain'
        return msg

    def _postprocess_sent_message(self, cr, uid, message, context=None):
        """Perform any post-processing necessary after sending ``message``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the message was set.
        Overridden by subclasses for extra post-processing behaviors. 

        :param browse_record message: the message that was just sent
        :return: True
        """
        if context is None:
            context = {}
        if context.get('active_ids', False) and context.get('active_model', False):
            self.pool.get(context['active_model']).write(cr, uid, context['active_ids'], {'message_state':'read'}, context=context)
        if message.auto_delete:
            self.pool.get('ir.attachment').unlink(cr, uid,
                                                  [x.id for x in message.attachment_ids \
                                                        if x.res_model == self._name and \
                                                           x.res_id == message.id],
                                                  context=context)
            message.unlink()
        return True

    def send(self, cr, uid, ids, auto_commit=False, context=None):
        """Sends the selected emails immediately, ignoring their current
           state (mails that have already been sent should not be passed
           unless they should actually be re-sent).
           Emails successfully delivered are marked as 'sent', and those
           that fail to be deliver are marked as 'exception', and the
           corresponding error message is output in the server logs.

           :param bool auto_commit: whether to force a commit of the message
                                    status after sending each message (meant
                                    only for processing by the scheduler),
                                    should never be True during normal
                                    transactions (default: False)
           :return: True
        """
        if context is None:
            context = {}
        ir_mail_server = self.pool.get('ir.mail_server')
        self.write(cr, uid, ids, {'state': 'outgoing'}, context=context)
        for message in self.browse(cr, uid, ids, context=context):
            try:
                attachments = []
                for attach in message.attachment_ids:
                    attachments.append((attach.datas_fname, base64.b64decode(attach.datas)))

                body = message.body_html if message.subtype == 'html' else message.body_text
                body_alternative = None
                subtype_alternative = None
                if message.subtype == 'html' and message.body_text:
                    # we have a plain text alternative prepared, pass it to 
                    # build_message instead of letting it build one
                    body_alternative = message.body_text
                    subtype_alternative = 'plain'

                msg = ir_mail_server.build_email(
                    email_from=message.email_from,
                    email_to=to_email(message.email_to),
                    subject=message.subject,
                    body=body,
                    body_alternative=body_alternative,
                    email_cc=to_email(message.email_cc),
                    email_bcc=to_email(message.email_bcc),
                    reply_to=message.reply_to,
                    attachments=attachments, message_id=message.message_id,
                    references = message.references,
                    object_id=message.res_id and ('%s-%s' % (message.res_id,message.model)),
                    subtype=message.subtype,
                    subtype_alternative=subtype_alternative,
                    headers=message.headers and ast.literal_eval(message.headers))
                res = ir_mail_server.send_email(cr, uid, msg,
                                                mail_server_id=message.mail_server_id.id,
                                                context=context)
                if res:
                    message.write({'state':'sent', 'message_id': res})
                else:
                    message.write({'state':'exception'})
                message.refresh()
                if message.state == 'sent':
                    self._postprocess_sent_message(cr, uid, message, context=context)
            except Exception:
                _logger.exception('failed sending mail.message %s', message.id)
                message.write({'state':'exception'})

            if auto_commit == True:
                cr.commit()
        return True

    def cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
