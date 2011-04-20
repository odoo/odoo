# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>)
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
from tools.translate import _
import tools
import netsvc
import base64
import time
import logging
import re
import email
from email.header import decode_header
#import binascii
#import email
#from email.header import decode_header
#from email.utils import parsedate
#import base64
#import re
#import logging
#import xmlrpclib

#import re
#import smtplib
#import base64
#from email import Encoders
#from email.mime.base import MIMEBase
#from email.mime.multipart import MIMEMultipart
#from email.mime.text import MIMEText
#from email.header import decode_header, Header
#from email.utils import formatdate
#import netsvc
#import datetime
#import tools
#import logging
#email_content_types = [
#    'multipart/mixed',
#    'multipart/alternative',
#    'multipart/related',
#    'text/plain',
#    'text/html'
#]

LOGGER = netsvc.Logger()
_logger = logging.getLogger('mail')

def format_date_tz(date, tz=None):
    if not date:
        return 'n/a'
    format = tools.DEFAULT_SERVER_DATETIME_FORMAT
    return tools.server_to_local_timestamp(date, format, format, tz)

class email_message_common(osv.osv_memory):
    _name = 'email.message.common'
    _columns = {
        'subject':fields.text('Subject', translate=True),
        'model': fields.char('Object Name', size=128, select=1),
        'res_id': fields.integer('Resource ID', select=1),
        'date': fields.datetime('Date'),
        'user_id': fields.many2one('res.users', 'User Responsible'),
        'email_from': fields.char('From', size=128, help="Email From"),
        'email_to': fields.char('To', help="Email Recipients", size=256),
        'email_cc': fields.char('Cc', help="Carbon Copy Email Recipients", size=256),
        'email_bcc': fields.char('Bcc', help='Blind Carbon Copy Email Recipients', size=256),
        'message_id': fields.char('Message Id', size=1024, help="Message Id on Email.", select=1),
        'references': fields.text('References', help="References emails."),
        'reply_to':fields.char('Reply-To', size=250),
        'sub_type': fields.char('Sub Type', size=32),
        'headers': fields.text('x_headers'),
        'priority':fields.integer('Priority'),
        'body': fields.text('Description', translate=True),
        'body_html': fields.text('HTML', help="Contains HTML version of email"),
        'smtp_server_id':fields.many2one('ir.mail_server', 'SMTP Server'),
    }
    _rec_name = 'subject'

    _sql_constraints = []
email_message_common()

class email_message(osv.osv):
    '''
    Email Message
    '''
    _inherit = 'email.message.common'
    _name = 'email.message'
    _description = 'Email Message'
    _order = 'date desc'

    def open_document(self, cr, uid, ids, context=None):
        """ To Open Document
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID of messages
        @param context: A standard dictionary
        """
        action_data = False
        if ids:
            message_id = ids[0]
            mailgate_data = self.browse(cr, uid, message_id, context=context)
            model = mailgate_data.model
            res_id = mailgate_data.res_id

            action_pool = self.pool.get('ir.actions.act_window')
            action_ids = action_pool.search(cr, uid, [('res_model', '=', model)])
            if action_ids:
                action_data = action_pool.read(cr, uid, action_ids[0], context=context)
                action_data.update({
                    'domain' : "[('id','=',%d)]"%(res_id),
                    'nodestroy': True,
                    'context': {}
                    })
        return action_data

    def open_attachment(self, cr, uid, ids, context=None):
        """ To Open attachments
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID of messages
        @param context: A standard dictionary
        """
        action_data = False
        action_pool = self.pool.get('ir.actions.act_window')
        message_pool = self.browse(cr ,uid, ids, context=context)[0]
        att_ids = [x.id for x in message_pool.attachment_ids]
        action_ids = action_pool.search(cr, uid, [('res_model', '=', 'ir.attachment')])
        if action_ids:
            action_data = action_pool.read(cr, uid, action_ids[0], context=context)
            action_data.update({
                'domain': [('id','in',att_ids)],
                'nodestroy': True
                })
        return action_data

    def truncate_data(self, cr, uid, data, context=None):
        data_list = data and data.split('\n') or []
        if len(data_list) > 3:
            res = '\n\t'.join(data_list[:3]) + '...'
        else:
            res = '\n\t'.join(data_list)
        return res

    def _get_display_text(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        tz = context.get('tz')
        result = {}
        for message in self.browse(cr, uid, ids, context=context):
            msg_txt = ''
            if message.history:
                msg_txt += (message.email_from or '/') + _(' wrote on ') + format_date_tz(message.date, tz) + ':\n\t'
                if message.body:
                    msg_txt += self.truncate_data(cr, uid, message.body, context=context)
            else:
                msg_txt = (message.user_id.name or '/') + _(' on ') + format_date_tz(message.date, tz) + ':\n\t'
                msg_txt += message.subject
            result[message.id] = msg_txt
        return result

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'),
        'display_text': fields.function(_get_display_text, method=True, type='text', size="512", string='Display Text'),
        'debug':fields.boolean('Debug', readonly=True),
        'history': fields.boolean('History', readonly=True),
        'state':fields.selection([
                        ('outgoing', 'Outgoing'),
                        ('sent', 'Sent'),
                        ('received', 'Received'),
                        ('exception', 'Exception'),
                        ('cancel', 'Cancelled'),
                        ], 'State', readonly=True),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete emails after sending"),
    }

    _defaults = {
    }

    def init(self, cr):
        cr.execute("""SELECT indexname
                      FROM pg_indexes
                      WHERE indexname = 'email_message_res_id_model_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX email_message_res_id_model_idx
                          ON email_message (model, res_id)""")

    def schedule_with_attach(self, cr, uid, email_from, email_to, subject, body, model=False, email_cc=None, email_bcc=None, reply_to=False, attach=None,
            message_id=False, references=False, openobject_id=False, debug=False, subtype='plain', x_headers={}, priority='3', smtp_server_id=False, context=None, auto_delete=False):
        if context is None:
            context = {}
        attachment_obj = self.pool.get('ir.attachment')
        if email_to and type(email_to) != list:
            email_to = [email_to]
        if email_cc and type(email_cc) != list:
            email_cc = [email_cc]
        if email_bcc and type(email_bcc) != list:
            email_bcc = [email_bcc]

        msg_vals = {
                'subject': subject,
                'model': model or '',
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': uid,
                'body': body,
                'email_from': email_from,
                'email_to': email_to and ','.join(email_to) or '',
                'email_cc': email_cc and ','.join(email_cc) or '',
                'email_bcc': email_bcc and ','.join(email_bcc) or '',
                'reply_to': reply_to,
                'res_id': openobject_id,
                'message_id': message_id,
                'references': references or '',
                'sub_type': subtype or '',
                'headers': x_headers or False,
                'priority': priority,
                'debug': debug,
                'history': True,
                'smtp_server_id': smtp_server_id,
                'state': 'outgoing',
                'auto_delete': auto_delete
            }
        email_msg_id = self.create(cr, uid, msg_vals, context)
        if attach:
            attachment_ids = []
            for attachment in attach:
                attachment_data = {
                        'name': attachment[0],
                        'subject':  (subject or '') + _(' (Email Attachment)'),
                        'datas': attachment[1],
                        'datas_fname': attachment[0],
                        'body': subject or _('No Description'),
                        'res_model':'email.message',
                        'res_id': email_msg_id,
                    }
                if context.has_key('default_type'):
                    del context['default_type']
                attachment_ids.append(attachment_obj.create(cr, uid, attachment_data, context))
            self.write(cr, uid, email_msg_id,
                              { 'attachment_ids': [[6, 0, attachment_ids]] }, context)
        return email_msg_id

    def process_retry(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'outgoing'}, context)

    def process_email_queue(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        if not ids:
            filters = [('state', '=', 'outgoing')]
            if 'filters' in context:
                filters.extend(context['filters'])
            ids = self.search(cr, uid, filters, context=context)
        try:
            res = self.send_email(cr, uid, ids, auto_commit=True, context=context)
        except Exception, error:
            logger = netsvc.Logger()
            msg = _("Sending of Mail failed. Error: %s") % (error)
            logger.notifyChannel("email", netsvc.LOG_ERROR, msg)
            return False
        return res

    def _decode_header(self, text):
        """Returns unicode() string conversion of the the given encoded smtp header"""
        if text:
            text = decode_header(text.replace('\r', ''))
            return ''.join([tools.ustr(x[0], x[1]) for x in text])

    def to_email(self,text):
        return re.findall(r'([^ ,<@]+@[^> ,]+)',text)

    def parse_message(self, message):
        """Return Dictionary Object after parse EML Message String
        @param message: email.message.Message object or string or unicode object
        """
        if isinstance(message, str):
            msg_txt = email.message_from_string(message)

        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            msg_txt = email.message_from_string(message)

        msg_txt = message
        message_id = msg_txt.get('message-id', False)
        msg = {}

        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['message-id'] = message_id
            _logger.info('Parsing Message without message-id, generating a random one: %s', message_id)


        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id

        if 'Subject' in fields:
            msg['subject'] = self._decode_header(msg_txt.get('Subject'))

        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in fields:
            msg['from'] = self._decode_header(msg_txt.get('From') or msg_txt.get_unixfrom())

        if 'Delivered-To' in fields:
            msg['to'] = self._decode_header(msg_txt.get('Delivered-To'))

        if 'CC' in fields:
            msg['cc'] = self._decode_header(msg_txt.get('CC'))

        if 'Reply-to' in fields:
            msg['reply'] = self._decode_header(msg_txt.get('Reply-To'))

        if 'Date' in fields:
            msg['date'] = self._decode_header(msg_txt.get('Date'))

        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'In-Reply-To' in fields:
            msg['in-reply-to'] = msg_txt.get('In-Reply-To')

        if 'X-Priority' in fields:
            msg['priority'] = msg_txt.get('X-Priority', '3 (Normal)').split(' ')[0] #TOFIX:

        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            body = msg_txt.get_payload(decode=True)
            if 'text/html' in msg.get('content-type', ''):
                body = tools.html2plaintext(body)
            msg['body'] = tools.ustr(body, encoding)

        attachments = {}
        has_plain_text = False
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', ''):
            body = ""
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                encoding = part.get_content_charset()
                filename = part.get_filename()
                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    if filename:
                        attachments[filename] = content
                    elif not has_plain_text:
                        # main content parts should have 'text' maintype
                        # and no filename. we ignore the html part if
                        # there is already a plaintext part without filename,
                        # because presumably these are alternatives.
                        content = tools.ustr(content, encoding)
                        if part.get_content_subtype() == 'html':
                            body = tools.ustr(tools.html2plaintext(content))
                        elif part.get_content_subtype() == 'plain':
                            body = content
                            has_plain_text = True
                elif part.get_content_maintype() in ('application', 'image'):
                    if filename :
                        attachments[filename] = part.get_payload(decode=True)
                    else:
                        res = part.get_payload(decode=True)
                        body += tools.ustr(res, encoding)

            msg['body'] = body
            msg['attachments'] = attachments
        return msg

    def send_email(self, cr, uid, ids, auto_commit=False, context=None):
        """
        send email message
        """
        if context is None:
            context = {}
        smtp_server_obj = self.pool.get('ir.mail_server')
        attachment_pool = self.pool.get('ir.attachment')
        self.write(cr, uid, ids, {'state':'outgoing'}, context)
        for message in self.browse(cr, uid, ids, context):
            try:
                smtp_server = message.smtp_server_id
                if not smtp_server:
                    smtp_ids = smtp_server_obj.search(cr, uid, [])
                    if smtp_ids:
                        smtp_server = smtp_server_obj.browse(cr, uid, smtp_ids, context)[0]
                attachments = []
                for attach in message.attachment_ids:
                    attachments.append((attach.datas_fname, base64.b64decode(attach.datas)))
                if message.state in ['outgoing', 'exception']:
                    msg = smtp_server_obj.pack_message(cr, uid, message.email_from,
                        message.email_to and message.email_to.split(',') or [], message.subject, message.body,
                        email_cc=message.email_cc and message.email_cc.split(',') or [],
                        email_bcc=message.email_bcc and message.email_bcc.split(',') or [],
                        reply_to=message.reply_to,
                        attach=attachments, message_id=message.message_id, references = message.references,
                        openobject_id=message.res_id,
                        subtype=message.sub_type,
                        x_headers=message.headers and eval(message.headers) or {},
                        priority=message.priority)
                    res = smtp_server_obj.send_email(cr, uid,
                        msg,
                        mail_server_id = message.smtp_server_id.id or None,
                        smtp_server=smtp_server and smtp_server.smtp_host or None,
                        smtp_port=smtp_server and smtp_server.smtp_port or None,
                        smtp_user=smtp_server and smtp_server.smtp_user or None,
                        smtp_password=smtp_server and smtp_server.smtp_pass or None,
                        ssl=smtp_server and smtp_server.smtp_ssl or False,
                        tls=smtp_server and smtp_server.smtp_tls,
                        debug=message.debug)
                    if res:
                        self.write(cr, uid, [message.id], {'state':'sent', 'message_id': res}, context)
                    else:
                        self.write(cr, uid, [message.id], {'state':'exception'}, context)
                else:
                    raise osv.except_osv(_('Error !'), _('No messages in outgoing or exception state!'))

                #if auto_delete=True then delete that sent messages as well as attachments
                message_data = self.read(cr, uid, message.id, ['state', 'auto_delete', 'attachment_ids'])
                if message_data['state'] == 'sent' and message_data['auto_delete'] == True:
                    self.unlink(cr, uid, [message.id], context=context)
                    if message_data['attachment_ids']:
                        attachment_pool.unlink(cr, uid, message_data['attachment_ids'], context=context)

                if auto_commit == True:
                    cr.commit()

            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (message.id, error))
                self.write(cr, uid, [message.id], {'state':'exception'}, context)
                return False
        return True

    def do_cancel(self, cr, uid, ids, context=None):
        '''
        Cancel the email to be send
        '''
        self.write(cr, uid, ids, {'state':'cancel'}, context)
        return True
# OLD Code.
#    def send_all_mail(self, cr, uid, ids=None, context=None):
#        if ids is None:
#            ids = []
#        if context is None:
#            context = {}
#        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
#        if 'filters' in context.keys():
#            for each_filter in context['filters']:
#                filters.append(each_filter)
#        ids = self.search(cr, uid, filters, context=context)
#        self.write(cr, uid, ids, {'state':'sending'}, context)
#        self.send_this_mail(cr, uid, ids, context)
#        return True
#
#    def send_this_mail(self, cr, uid, ids=None, context=None):
#        #previous method to send email (link with email account can be found at the revision 4172 and below
#        result = True
#        attachment_pool = self.pool.get('ir.attachment')
#        for id in (ids or []):
#            try:
#                account_obj = self.pool.get('email.smtp_server')
#                values = self.read(cr, uid, id, [], context)
#                payload = {}
#                if values['attachments_ids']:
#                    for attid in values['attachments_ids']:
#                        attachment = attachment_pool.browse(cr, uid, attid, context)#,['datas_fname','datas'])
#                        payload[attachment.datas_fname] = attachment.datas
#                result = account_obj.send_email(cr, uid,
#                              [values['account_id'][0]],
#                              {'To':values.get('email_to') or u'',
#                               'CC':values.get('email_cc') or u'',
#                               'BCC':values.get('email_bcc') or u'',
#                               'Reply-To':values.get('reply_to') or u''},
#                              values['subject'] or u'',
#                              {'text':values.get('body_text') or u'', 'html':values.get('body_html') or u''},
#                              payload=payload,
#                              message_id=values['message_id'],
#                              context=context)
#                if result == True:
#                    account = account_obj.browse(cr, uid, values['account_id'][0], context=context)
#                    if account.auto_delete:
#                        self.write(cr, uid, id, {'folder': 'trash'}, context=context)
#                        self.unlink(cr, uid, [id], context=context)
#                        # Remove attachments for this mail
#                        attachment_pool.unlink(cr, uid, values['attachments_ids'], context=context)
#                    else:
#                        self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
#                else:
#                    error = result['error_msg']
#
#            except Exception, error:
#                logger = netsvc.Logger()
#                logger.notifyChannel("email-template", netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason:Could not login to server\nError: %s") % (id, error))
#            self.write(cr, uid, id, {'state':'na'}, context)
#        return result

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
