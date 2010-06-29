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
import base64
import re
from tools.translate import _
import logging

_logger = logging.getLogger('mailgate')

class mailgate_thread(osv.osv):
    '''
    Mailgateway Thread
    '''
    _name = 'mailgate.thread'
    _description = 'Mailgateway Thread'

    _columns = {
        'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', domain=[('history', '=', True)]),
        'log_ids': fields.one2many('mailgate.message', 'res_id', 'Logs', domain=[('history', '=', False)]),
    }

    def message_new(self, cr, uid, msg, context):
        raise Exception, _('Method is not implemented')

    def message_update(self, cr, uid, ids, vals={}, msg="", default_act='pending', context={}):
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

    def _history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, \
                    email_from=False, message_id=False, references=None, attach=None, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param cases: a browse record list
        @param keyword: Case action keyword e.g.: If case is closed "Close" keyword is used
        @param history: Value True/False, If True it makes entry in case History otherwise in Case Log
        @param email: Email address if any
        @param details: Details of case history if any 
        @param atach: Attachment sent in email
        @param context: A standard dictionary for contextual values"""
        if context is None:
            context = {}
        if attach is None:
            attach = []

        # The mailgate sends the ids of the cases and not the object list

        if all(isinstance(case_id, (int, long)) for case_id in cases):
            cases = self.browse(cr, uid, cases, context=context)

        att_obj = self.pool.get('ir.attachment')
        obj = self.pool.get('mailgate.message')

        for case in cases:
            data = {
                'name': keyword, 
                'user_id': uid, 
                'model' : case._name, 
                'res_id': case.id, 
                'date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                'message_id': message_id, 
            }
            attachments = []
            if history:
                for att in attach:
                    attachments.append(att_obj.create(cr, uid, {'name': att[0], 'datas': base64.encodestring(att[1])}))

                data = {
                    'name': subject or 'History', 
                    'history': True, 
                    'user_id': uid, 
                    'model' : case._name, 
                    'res_id': case.id,
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                    'description': details or (hasattr(case, 'description') and case.description or False), 
                    'email_to': email or \
                        (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                         case.user_id.address_id.email) or tools.config.get('email_from', False), 
                    'email_from': email_from or \
                        (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                         case.user_id.address_id.email) or tools.config.get('email_from', False), 
                    'partner_id': hasattr(case, 'partner_id') and (case.partner_id and case.partner_id.id or False) or False, 
                    'references': references, 
                    'message_id': message_id, 
                    'attachment_ids': [(6, 0, attachments)]
                }
            res = obj.create(cr, uid, data, context)
        return True
mailgate_thread()

class mailgate_message(osv.osv):
    '''
    Mailgateway Message
    '''
    _name = 'mailgate.message'
    _description = 'Mailgateway Message'
    _order = 'id desc'
    _columns = {
        'name':fields.char('Subject', size=128), 
        'model': fields.char('Object Name', size=128), 
        'res_id': fields.integer('Resource ID'),
        'ref_id': fields.char('Reference Id', size=256, readonly=True, help="Message Id in Email Server.", select=True),
        'date': fields.datetime('Date'), 
        'history': fields.boolean('Is History?'),
        'user_id': fields.many2one('res.users', 'User Responsible', readonly=True), 
        'message': fields.text('Description'), 
        'email_from': fields.char('Email From', size=84), 
        'email_to': fields.char('Email To', size=84), 
        'email_cc': fields.char('Email CC', size=84), 
        'email_bcc': fields.char('Email BCC', size=84), 
        'message_id': fields.char('Message Id', size=1024, readonly=True, help="Message Id on Email.", select=True),
        'references': fields.text('References', readonly=True, help="Referencess emails."),
        'description': fields.text('Description'), 
        'partner_id': fields.many2one('res.partner', 'Partner', required=False), 
        'attachment_ids': fields.many2many('ir.attachment', 'message_attachment_rel', 'message_id', 'attachment_id', 'Attachments'), 
    }

mailgate_message()

class mailgate_tool(osv.osv_memory):

    _name = 'email.server.tools'
    _description = "Email Server Tools"

    def _to_decode(self, s, charsets):
        if not s:
            return s
        for charset in charsets:
            if charset:
                try:
                    return s.decode(charset)
                except UnicodeError:
                    pass
        return s.decode('latin1')

    def _decode_header(self, text):
        if text:
            text = decode_header(text.replace('\r', '')) 
        return ''.join(map(lambda x:self._to_decode(x[0], [x[1]]), text or []))

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
            msg_data = {
                        'name': msg.get('subject', 'No subject'), 
                        'date': msg.get('date') , 
                        'description': msg.get('body', msg.get('from')), 
                        'history': True,
                        'res_model': model, 
                        'email_cc': msg.get('cc'), 
                        'email_from': msg.get('from'), 
                        'email_to': msg.get('to'), 
                        'message_id': msg.get('message-id'), 
                        'references': msg.get('references'), 
                        'res_id': res_id,
                        'user_id': uid, 
                        'attachment_ids': [(6, 0, attach)]
            }
            msg_id = msg_pool.create(cr, uid, msg_data, context=context)
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
            message_followers_emails = self.to_email(','.join(message_followers))
            message_recipients = self.to_email(','.join([self._decode_header(msg['from']),
                                                         self._decode_header(msg['to']),
                                                         self._decode_header(msg['cc'])]))
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

    def process_email(self, cr, uid, model, message, attach=True, context=None):
        """This function Processes email and create record for given OpenERP model
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param model: OpenObject Model
        @param message: Email details
        @param attach: Email attachments
        @param context: A standard dictionary for contextual values"""
        model_pool = self.pool.get(model)
        if not context:
            context = {}
        res_id = False
        # Create New Record into particular model
        def create_record(msg):
            if hasattr(model_pool, 'message_new'):
                res_id = model_pool.message_new(cr, uid, msg, context)
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

                att_ids = []
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

            return res_id

        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        msg_txt = email.message_from_string(tools.ustr(message).encode('utf-8'))
        message_id = msg_txt.get('Message-ID', False)
        msg = {}

        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['Message-ID'] = message_id
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

        if 'Cc' in fields:
            msg['cc'] = self._decode_header(msg_txt.get('Cc'))

        if 'Reply-To' in fields:
            msg['reply'] = self._decode_header(msg_txt.get('Reply-To'))

        if 'Date' in fields:
            msg['date'] = msg_txt.get('Date')

        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        if 'References' in fields:
            msg['references'] = msg_txt.get('References')

        if 'X-Priority' in fields:
            msg['priority'] = msg_txt.get('X-priority', '3 (Normal)').split(' ')[0]

        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            msg['body'] = msg_txt.get_payload(decode=True)
            if encoding:
                msg['body'] = tools.ustr(msg['body'])

        attachments = {}
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', ''):
            body = ""
            counter = 1
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                encoding = part.get_content_charset()

                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    filename = part.get_filename()
                    if filename :
                        attachments[filename] = content
                    else:
                        if encoding:
                            content = unicode(content, encoding)
                        if part.get_content_subtype() == 'html':
                            body = tools.html2plaintext(content)
                        elif part.get_content_subtype() == 'plain':
                            body = content
                elif part.get_content_maintype()=='application' or part.get_content_maintype()=='image' or part.get_content_maintype()=='text':
                    filename = part.get_filename();
                    if filename :
                        attachments[filename] = part.get_payload(decode=True)
                    else:
                        res = part.get_payload(decode=True)
                        if encoding:
                            res = tools.ustr(res)
                        body += res

            msg['body'] = body
            msg['attachments'] = attachments
        res_ids = []
        new_res_id = False
        if msg.get('references'):
            references = msg.get('references')
            if '\r\n' in references:
                references = msg.get('references').split('\r\n')
            else:
                references = msg.get('references').split(' ')
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
                    res_ids.append(res_id)
                    model_pool = self.pool.get(model)

                    vals = {}
                    if hasattr(model_pool, 'message_update'):
                        model_pool.message_update(cr, uid, [res_id], vals, msg, context=context)

        if not len(res_ids):
            new_res_id = create_record(msg)
            res_ids = [new_res_id]
        # Store messages
        context.update({'model' : model})
        if hasattr(model_pool, '_history'):
            model_pool._history(cr, uid, res_ids, _('Receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False),
                            attach = msg.get('attachments', {}).items(),
                            context = context)
        else:
            self.history(cr, uid, model, res_ids, msg, att_ids, context=context)
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
        address_ids = address_pool.search(cr, uid, [('email', '=', from_email)])
        if address_ids:
            address = address_pool.browse(cr, uid, address_ids[0])
            res['partner_address_id'] = address_ids[0]
            res['partner_id'] = address.partner_id.id

        return res

mailgate_tool()
