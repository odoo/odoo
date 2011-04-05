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

from email.utils import parsedate
import base64

from tools.translate import _
import logging
import xmlrpclib

_logger = logging.getLogger('mail')

class email_thread(osv.osv):
    '''
    Email Thread
    '''
    _name = 'email.thread'
    _description = 'Email Thread'

    _columns = {
        'message_ids': fields.one2many('email.message', 'res_id', 'Messages', readonly=True),
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
        })
        return super(email_thread, self).copy(cr, uid, id, default, context=context)

    def message_new(self, cr, uid, msg, context):
        """
        Called by process_email() to create a new record 
        corresponding to an incoming message for a new thread.
        @param msg: Dictionary Object to contain email message data
        """
        model_pool = self.pool.get(self._name)
        fields = model_pool.fields_get(cr, uid, context=context)
        data = model_pool.default_get(cr, uid, fields, context=context)
        res_id = model_pool.create(cr, uid, data, context=context)

        for attachment in msg.get('attachments', []):
            data_attach = {
                'name': attachment,
                'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                'datas_fname': attachment,
                'description': _('Mail attachment'),
                'res_model': self._name,
                'res_id': res_id,
            }
            att_ids.append(self.pool.get('ir.attachment').create(cr, uid, data_attach))

        model_pool.history(cr, uid, res_id, _('receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            email_cc = msg.get('cc'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False) or msg.get('in-reply-to', False),
                            attach = att_ids.items(),
                            email_date = msg.get('date'),
                            context = context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals={}, default_act='pending', context=None):
        """ 
        Called by process_email() to add a new incoming message for an existing thread
        @param msg: Dictionary Object to contain email message data
        """
        model_pool = self.pool.get(self._name)
        for res_id in ids:
            for attachment in msg.get('attachments', []):
                data_attach = {
                    'name': attachment,
                    'datas': binascii.b2a_base64(str(attachments.get(attachment))),
                    'datas_fname': attachment,
                    'description': _('Mail attachment'),
                    'res_model': self._name,
                    'res_id': res_id,
                }
                att_ids.append(self.pool.get('ir.attachment').create(cr, uid, data_attach))

            model_pool.history(cr, uid, res_id, _('receive'), history=True,
                                subject = msg.get('subject'),
                                email = msg.get('to'),
                                details = msg.get('body'),
                                email_from = msg.get('from'),
                                email_cc = msg.get('cc'),
                                message_id = msg.get('message-id'),
                                references = msg.get('references', False) or msg.get('in-reply-to', False),
                                attach = att_ids.items(),
                                email_date = msg.get('date'),
                                context = context)
        return True

    def thread_followers(self, cr, uid, ids, context=None):
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

    def history(self, cr, uid, cases, keyword, history=False, subject=None, email=False, details=None, \
                    email_from=False, message_id=False, references=None, attach=None, email_cc=None, \
                    email_bcc=None, email_date=None, context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param cases: a browse record list
        @param keyword: Case action keyword e.g.: If case is closed "Close" keyword is used
        @param history: Value True/False, If True it makes entry as a Emails Messages otherwise Log Messages
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
        obj = self.pool.get('email.message')

        for case in cases:
            attachments = []
            for att in attach:
                    attachments.append(att_obj.create(cr, uid, {'res_model':case._name,'res_id':case.id, 'name': att[0], 'datas': base64.encodestring(att[1])}))

            partner_id = hasattr(case, 'partner_id') and (case.partner_id and case.partner_id.id or False) or False
            if not partner_id and case._name == 'res.partner':
                partner_id = case.id
            data = {
                'subject': keyword,
                'user_id': uid,
                'model' : case._name,
                'partner_id': partner_id,
                'res_id': case.id,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'message_id': message_id,
                'body': details or (hasattr(case, 'description') and case.description or False),
                'attachment_ids': [(6, 0, attachments)]
            }

            if history:
                for param in (email, email_cc, email_bcc):
                    if isinstance(param, list):
                        param = ", ".join(param)

                data = {
                    'subject': subject or _('History'),
                    'history': True,
                    'user_id': uid,
                    'model' : case._name,
                    'res_id': case.id,
                    'date': email_date or time.strftime('%Y-%m-%d %H:%M:%S'),
                    'body': details,
                    'email_to': email,
                    'email_from': email_from or \
                        (hasattr(case, 'user_id') and case.user_id and case.user_id.address_id and \
                         case.user_id.address_id.email),
                    'email_cc': email_cc,
                    'email_bcc': email_bcc,
                    'partner_id': partner_id,
                    'references': references,
                    'message_id': message_id,
                    'attachment_ids': [(6, 0, attachments)],
                    'state' : 'received',
                }
            obj.create(cr, uid, data, context=context)
        return True

    

    def email_forward(self, cr, uid, model, res_ids, msg, email_error=False, context=None):
        """Sends an email to all people following the thread
        @param res_id: Id of the record of OpenObject model created from the email message
        @param msg: email.message.Message object to forward
        @param email_error: Default Email address in case of any Problem
        """
        model_pool = self.pool.get(model)
        smtp_server_obj = self.pool.get('ir.mail_server')
        email_message_obj = self.pool.get('email.message')
        _decode_header = email_message_obj._decode_header
        for res in model_pool.browse(cr, uid, res_ids, context=context):
            thread_followers = model_pool.thread_followers(cr, uid, [res.id])[res.id]
            message_followers_emails = email_message_obj.to_email(','.join(filter(None, thread_followers)))
            message_recipients = email_message_obj.to_email(','.join(filter(None,
                                                         [_decode_header(msg['from']),
                                                         _decode_header(msg['to']),
                                                         _decode_header(msg['cc'])])))
            message_forward = [i for i in message_followers_emails if (i and (i not in message_recipients))]

            if message_forward:
                # TODO: we need an interface for this for all types of objects, not just leads
                if hasattr(res, 'section_id'):
                    del msg['reply-to']
                    msg['reply-to'] = res.section_id.reply_to

                smtp_from = self.to_email(msg['from'])
                msg['from'] = smtp_from
                msg['to'] =  message_forward
                msg['message-id'] = tools.generate_tracking_message_id(res.id)
                if not smtp_server_obj.send_email(cr, uid, msg) and email_error:
                    subj = msg['subject']
                    del msg['subject'], msg['to'], msg['cc'], msg['bcc']
                    msg['subject'] = _('[OpenERP-Forward-Failed] %s') % subj
                    msg['to'] = email_error
                    smtp_server_obj.send_email(cr, uid, msg)
        return True

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
        email_message_pool = self.pool.get('email.message')
        res_id = False


        # Parse Message
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        msg = email_message_pool.parse_message(msg_txt)

        # Create New Record into particular model
        def create_record(msg):
            new_res_id = model_pool.message_new(cr, uid, msg, context=context)
            if custom_values:
                model_pool.write(cr, uid, [res_id], custom_values, context=context)
            return new_res_id

        res_id = False
        if msg.get('references') or msg.get('in-reply-to'):
            references = msg.get('references') or msg.get('in-reply-to')
            if '\r\n' in references:
                references = references.split('\r\n')
            else:
                references = references.split(' ')
            for ref in references:
                ref = ref.strip()
                res_id = tools.reference_re.search(ref)
                if res_id:
                    res_id = res_id.group(1)
                else:
                    res_id = tools.res_re.search(msg['subject'])
                    if res_id:
                        res_id = res_id.group(1)
                if res_id:
                    res_id = int(res_id)
                    if model_pool.exists(cr, uid, res_id):
                        model_pool.message_update(cr, uid, [res_id], {}, msg, context=context)
                        

        if not res_id:
            res_id = create_record(msg)

        #To forward the email to other followers
        self.email_forward(cr, uid, model, [res_id], msg_txt)
        return res_id

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


email_thread()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
