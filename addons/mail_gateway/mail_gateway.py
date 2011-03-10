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

from osv import osv, fields
import time
import tools
import binascii
import email
from email.header import decode_header
from email.utils import parsedate
import base64
import re
from tools.translate import _
import logging
import xmlrpclib

_logger = logging.getLogger('mailgate')

class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'

    _columns = {
        'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', readonly=True),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """
        Overrides orm copy method.
        @param self: the object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param id: Id of mailgate thread
        @param default: Dictionary of default values for copy.
        @param context: A standard dictionary for contextual values
        """
        if default is None:
            default = {}

        default.update({
            'message_ids': [],
            'date_closed': False,
            'date_open': False
        })
        return super(mailgate_thread, self).copy(cr, uid, id, default, context=context)

    def message_new(self, cr, uid, msg, context):
        raise Exception, _('Method is not implemented')

    def message_update(self, cr, uid, ids, vals={}, msg="", default_act='pending', context=None):
        raise Exception, _('Method is not implemented')

    def message_followers(self, cr, uid, ids, context=None):
        """ Get a list of emails of the people following this thread
        """
        res = {}
        if isinstance(ids, (str, int, long)):
            ids = [long(ids)]
        for thread in self.browse(cr, uid, ids, context=context):
            l=[]
            for message in thread.message_ids:
                l.append((message.user_id and message.user_id.email) or '')
                l.append(message.email_from or '')
                l.append(message.email_cc or '')
            res[thread.id] = l
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        raise Exception, _('Method is not implemented')

    def history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, \
                    email_from=False, message_id=False, references=None, attach=None, email_cc=None, \
                    email_bcc=None, email_date=None, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param cases: a browse record list
        @param keyword: Subject of the history item
        @param history: Value True/False, If True it makes entry in case History otherwise in Case Log
        @param email: Email-To / Recipient address
        @param email_from: Email From / Sender address if any
        @param email_cc: Comma-Separated list of Carbon Copy Emails To addresse if any
        @param email_bcc: Comma-Separated list of Blind Carbon Copy Emails To addresses if any
        @param email_date: Email Date string if different from now, in server Timezone
        @param details: Description, Details of case history if any
        @param atach: Attachment sent in email
        @param context: A standard dictionary for contextual values"""
        if context is None:
            context = {}
        if attach is None:
            attach = []

        if email_date:
            edate = parsedate(email_date)
            if edate is not None:
                email_date = time.strftime('%Y-%m-%d %H:%M:%S', edate)

        # The mailgate sends the ids of the cases and not the object list

        if all(isinstance(case_id, (int, long)) for case_id in cases):
            cases = self.browse(cr, uid, cases, context=context)

        att_obj = self.pool.get('ir.attachment')
        obj = self.pool.get('mailgate.message')

        for case in cases:
            attachments = []
            for att in attach:
                att_ids = att_obj.search(cr, uid, [('name','=',att[0]), ('res_id', '=', case.id)])
                if att_ids:
                    attachments.append(att_ids[0])
                else:
                    attachments.append(att_obj.create(cr, uid, {'res_model':case._name,'res_id':case.id, 'name': att[0], 'datas': base64.encodestring(att[1])}))

            partner_id = hasattr(case, 'partner_id') and (case.partner_id and case.partner_id.id or False) or False
            if not partner_id and case._name == 'res.partner':
                partner_id = case.id
            data = {
                'name': keyword,
                'user_id': uid,
                'model' : case._name,
                'partner_id': partner_id,
                'res_id': case.id,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'message_id': message_id,
                'description': details,
                'attachment_ids': [(6, 0, attachments)]
            }

            if history:
                for param in (email, email_cc, email_bcc):
                    if isinstance(param, list):
                        param = ", ".join(param)

                data = {
                    'name': subject or _('History'),
                    'history': True,
                    'user_id': uid,
                    'model' : case._name,
                    'res_id': case.id,
                    'date': email_date or time.strftime('%Y-%m-%d %H:%M:%S'),
                    'description': details or (hasattr(case, 'description') and case.description or False),
                    'email_to': email,
                    'email_from': email_from or \
                        (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                         case.user_id.address_id.email),
                    'email_cc': email_cc,
                    'email_bcc': email_bcc,
                    'partner_id': partner_id,
                    'references': references,
                    'message_id': message_id,
                    'attachment_ids': [(6, 0, attachments)]
                }

            obj.create(cr, uid, data, context=context)
        return True
mailgate_thread()

def format_date_tz(date, tz=None):
    if not date:
        return 'n/a'
    format = tools.DEFAULT_SERVER_DATETIME_FORMAT
    return tools.server_to_local_timestamp(date, format, format, tz)

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
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
                if message.description:
                    msg_txt += self.truncate_data(cr, uid, message.description, context=context)
            else:
                msg_txt = (message.user_id.name or '/') + _(' on ') + format_date_tz(message.date, tz) + ':\n\t'
                msg_txt += message.name
            result[message.id] = msg_txt
        return result

    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    _order = 'date desc'
    _columns = {
        'name':fields.text('Subject', readonly=True),
        'model': fields.char('Object Name', size=128, select=1, readonly=True),
        'res_id': fields.integer('Resource ID', select=1, readonly=True),
        'ref_id': fields.char('Reference Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'date': fields.datetime('Date', readonly=True),
        'history': fields.boolean('Is History?', readonly=True),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
        'message': fields.text('Description', readonly=True),
        'email_from': fields.char('From', size=128, help="Email From", readonly=True),
        'email_to': fields.char('To', help="Email Recipients", size=256, readonly=True),
        'email_cc': fields.char('Cc', help="Carbon Copy Email Recipients", size=256, readonly=True),
        'email_bcc': fields.char('Bcc', help='Blind Carbon Copy Email Recipients', size=256, readonly=True),
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email.", select=True),
        'references': fields.text('References', readonly=True, help="References emails."),
        'description': fields.text('Description', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments', readonly=True),
        'display_text': fields.function(_get_display_text, method=True, type='text', size="512", string='Display Text'),
    }

    def init(self, cr):
        cr.execute("""SELECT indexname
                      FROM pg_indexes
                      WHERE indexname = 'mailgate_message_res_id_model_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE INDEX mailgate_message_res_id_model_idx
                          ON mailgate_message (model, res_id)""")

mailgate_message()

class mailgate_tool(osv.osv_memory):

    _name = 'email.server.tools'
    _description = "Email Server Tools"

    def _decode_header(self, text):
        """Returns unicode() string conversion of the the given encoded smtp header"""
        if text:
            text = decode_header(text.replace('\r', ''))
            return ''.join([tools.ustr(x[0], x[1]) for x in text])

    def to_email(self,text):
        return re.findall(r'([^ ,<@]+@[^> ,]+)',text)

    def history(self, cr, uid, model, res_ids, msg, attach, context=None):
        """This function creates history for mails fetched
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: OpenObject Model
        @param res_ids: Ids of the record of OpenObject model created
        @param msg: Email details
        @param attach: Email attachments
        """
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]

        msg_pool = self.pool.get('mailgate.message')
        for res_id in res_ids:
            case = self.pool.get(model).browse(cr, uid, res_id, context=context)
            partner_id = hasattr(case, 'partner_id') and (case.partner_id and case.partner_id.id or False) or False
            if not partner_id and model == 'res.partner':
                partner_id = res_id
            msg_data = {
                'name': msg.get('subject', 'No subject'),
                'date': msg.get('date'),
                'description': msg.get('body', msg.get('from')),
                'history': True,
                'partner_id': partner_id,
                'model': model,
                'email_cc': msg.get('cc'),
                'email_from': msg.get('from'),
                'email_to': msg.get('to'),
                'message_id': msg.get('message-id'),
                'references': msg.get('references') or msg.get('in-reply-to'),
                'res_id': res_id,
                'user_id': uid,
                'attachment_ids': [(6, 0, attach)]
            }
            msg_pool.create(cr, uid, msg_data, context=context)
        return True

    def email_forward(self, cr, uid, model, res_ids, msg, email_error=False, context=None):
        """Sends an email to all people following the thread
        @param res_id: Id of the record of OpenObject model created from the email message
        @param msg: email.message.Message to forward
        @param email_error: Default Email address in case of any Problem
        """
        model_pool = self.pool.get(model)

        for res in model_pool.browse(cr, uid, res_ids, context=context):
            message_followers = model_pool.message_followers(cr, uid, [res.id])[res.id]
            message_followers_emails = self.to_email(','.join(filter(None, message_followers)))
            message_recipients = self.to_email(','.join(filter(None,
                                                         [self._decode_header(msg['from']),
                                                         self._decode_header(msg['to']),
                                                         self._decode_header(msg['cc'])])))
            message_forward = [i for i in message_followers_emails if (i and (i not in message_recipients))]

            if message_forward:
                # TODO: we need an interface for this for all types of objects, not just leads
                if hasattr(res, 'section_id'):
                    del msg['reply-to']
                    msg['reply-to'] = res.section_id.reply_to

                smtp_from = self.to_email(msg['from'])
                if not tools.misc._email_send(smtp_from, message_forward, msg, openobject_id=res.id) and email_error:
                    subj = msg['subject']
                    del msg['subject'], msg['to'], msg['cc'], msg['bcc']
                    msg['subject'] = '[OpenERP-Forward-Failed] %s' % subj
                    msg['to'] = email_error
                    tools.misc._email_send(smtp_from, self.to_email(email_error), msg, openobject_id=res.id)

    def process_email(self, cr, uid, model, message, custom_values=None, attach=True, context=None):
        """This function Processes email and create record for given OpenERP model
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: OpenObject Model
        @param message: Email details, passed as a string or an xmlrpclib.Binary
        @param attach: Email attachments
        @param context: A standard dictionary for contextual values"""

        # extract message bytes, we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)

        if context is None:
            context = {}

        if custom_values is None or not isinstance(custom_values, dict):
            custom_values = {}

        model_pool = self.pool.get(model)
        res_id = False

        # Create New Record into particular model
        def create_record(msg):
            att_ids = []
            if hasattr(model_pool, 'message_new'):
                res_id = model_pool.message_new(cr, uid, msg, context=context)
                if custom_values:
                    model_pool.write(cr, uid, [res_id], custom_values, context=context)
            else:
                data = {
                    'name': msg.get('subject'),
                    'email_from': msg.get('from'),
                    'email_cc': msg.get('cc'),
                    'user_id': False,
                    'description': msg.get('body'),
                    'state' : 'draft',
                }
                data.update(self.get_partner(cr, uid, msg.get('from'), context=context))
                res_id = model_pool.create(cr, uid, data, context=context)

                if attach:
                    for attachment in msg.get('attachments', []):
                        data_attach = {
                            'name': attachment,
                            'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                            'datas_fname': attachment,
                            'description': 'Mail attachment',
                            'res_model': model,
                            'res_id': res_id,
                        }
                        att_ids.append(self.pool.get('ir.attachment').create(cr, uid, data_attach))

            return res_id, att_ids

        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        message_id = msg_txt.get('message-id', False)
        msg = {}

        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['message-id'] = message_id
            _logger.info('Message without message-id, generating a random one: %s', message_id)

        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id

        if 'Subject' in fields:
            msg['subject'] = self._decode_header(msg_txt.get('Subject'))

        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')

        if 'From' in fields:
            msg['from'] = self._decode_header(msg_txt.get('From'))

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
            msg['priority'] = msg_txt.get('X-Priority', '3 (Normal)').split(' ')[0]

        if not msg_txt.is_multipart() or 'text/plain' in msg.get('Content-Type', ''):
            encoding = msg_txt.get_content_charset()
            body = msg_txt.get_payload(decode=True)
            if 'text/html' in msg_txt.get('Content-Type', ''):
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
        res_ids = []
        attachment_ids = []
        new_res_id = False
        if msg.get('references') or msg.get('in-reply-to'):
            references = msg.get('references') or msg.get('in-reply-to')
            if '\r\n' in references:
                references = references.split('\r\n')
            else:
                references = references.split(' ')
            for ref in references:
                ref = ref.strip()
                res_id = tools.misc.reference_re.search(ref)
                if res_id:
                    res_id = res_id.group(1)
                else:
                    res_id = tools.misc.res_re.search(msg['subject'])
                    if res_id:
                        res_id = res_id.group(1)
                if res_id:
                    res_id = int(res_id)
                    model_pool = self.pool.get(model)
                    if model_pool.exists(cr, uid, res_id):
                        res_ids.append(res_id)
                        if hasattr(model_pool, 'message_update'):
                            model_pool.message_update(cr, uid, [res_id], {}, msg, context=context)
                        else:
                            raise NotImplementedError('model %s does not support updating records, mailgate API method message_update() is missing'%model)

        if not len(res_ids):
            new_res_id, attachment_ids = create_record(msg)
            res_ids = [new_res_id]

        # Store messages
        context.update({'model' : model})
        if hasattr(model_pool, 'history'):
            model_pool.history(cr, uid, res_ids, _('receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            email_cc = msg.get('cc'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False) or msg.get('in-reply-to', False),
                            attach = attachments.items(),
                            email_date = msg.get('date'),
                            context = context)
        else:
            self.history(cr, uid, model, res_ids, msg, attachment_ids, context=context)
        self.email_forward(cr, uid, model, res_ids, msg_txt)
        return new_res_id

    def get_partner(self, cr, uid, from_email, context=None):
        """This function returns partner Id based on email passed
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        @param from_email: email address based on that function will search for the correct
        """
        address_pool = self.pool.get('res.partner.address')
        res = {
            'partner_address_id': False,
            'partner_id': False
        }
        from_email = self.to_email(from_email)[0]
        address_ids = address_pool.search(cr, uid, [('email', 'like', from_email)])
        if address_ids:
            address = address_pool.browse(cr, uid, address_ids[0])
            res['partner_address_id'] = address_ids[0]
            res['partner_id'] = address.partner_id.id

        return res

mailgate_tool()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
