# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>)
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

import time
import tools
import binascii
import email
from email.utils import parsedate

import logging
import xmlrpclib
from osv import osv, fields
from tools.translate import _
from mail_message import decode, to_email

_logger = logging.getLogger('mail')

class mail_thread(osv.osv):
    '''Mixin model, meant to be inherited by any model that needs to
       act as a discussion topic on which messages can be attached.

       mail.thread adds a one2many of mail.messages, acting as thread
       history, and a few methods that may be overridden to implement
       specific behavior.
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'

    _columns = {
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', readonly=True),
    }

    def thread_followers(self, cr, uid, ids, context=None):
        """Returns a list of email addresses of the people following
           this thread, including the sender of each mail, and the
           people who were in CC of the messages, if any.
        """
        res = {}
        if isinstance(ids, (str, int, long)):
            ids = [long(ids)]
        for thread in self.browse(cr, uid, ids, context=context):
            l = set()
            for message in thread.message_ids:
                l.add((message.user_id and message.user_id.email) or '')
                l.add(message.email_from or '')
                l.add(message.email_cc or '')
            res[thread.id] = filter(None, l)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """Overrides default copy method to empty the thread of
           messages attached to this record, as the copied object
           will have its own thread and does not have to share it.
        """
        if default is None:
            default = {}
        default.update({
            'message_ids': [],
        })
        return super(mail_thread, self).copy(cr, uid, id, default, context=context)

    def message_new(self, cr, uid, msg_dict, custom_values=None, context=None):
        """Called by ``process_email`` when a new message is received
           without referencing an existing thread. The default
           behavior is to create a new record of the corresponding
           model, then call ``append_mail()`` to attach a new
           mail.message to the newly created record.
           Additional behavior may be implemented by overriding this method.

           :param dict msg_dict: a map containing the email details and
                                 attachments. See ``process_email`` and
                                ``mail.message.parse()`` for details.
           :param dict custom_values: optional dictionary of additional
                                      field values to pass to create()
                                      when creating the new thread record.
                                      Be careful, these values may override
                                      any other values coming from the message.
           :param dict context: if a ``thread_model`` value is present
                                in the context, its value will be used
                                to determine the model of the record
                                to create (instead of the current model).
           :rtype: int
           :return: the id of the newly created thread object
        """
        if context is None:
            context = {}
        model = context.get('thread_model') or self._name
        model_pool = self.pool.get(model)
        fields = model_pool.fields_get(cr, uid, context=context)
        data = model_pool.default_get(cr, uid, fields, context=context)
        if 'name' in fields and not data.get('name'):
            data['name'] = msg_dict.get('from','')
        if custom_values and isinstance(custom_values, dict):
            data.update(custom_values)
        res_id = model_pool.create(cr, uid, data, context=context)
        self.append_mail(cr, uid, [res_id], msg_dict, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg_dict, vals={}, default_act=None, context=None):
        """Called by ``process_email`` when a new message is received
           for an existing thread. The default behavior is to create a
           new mail.message in the given thread by calling
           ``append_mail()``.
           Additional behavior may be implemented by overriding this
           method.

           :param dict msg_dict: a map containing the email details and
                                attachments. See ``process_email`` and
                                ``mail.message.parse()`` for details.
           :param dict context: if a ``thread_model`` value is present
                                in the context, its value will be used
                                to determine the model of the thread to
                                update (instead of the current model).
        """
        return self.append_mail(cr, uid, ids, msg_dict, context=context)

    def append_mail(self, cr, uid, ids, msg_dict, context=None):
        """Creates a new mail.message attached to the given threads,
           with the contents of msg_dict, by calling ``history`` with
           the mail details. All attachments in msg_dict will be
           attached to the thread record as well as to the actual
           message.

           :param dict msg_dict: a map containing the email details and
                                 attachments. See ``process_email`` and
                                ``mail.message.parse()`` for details.
           :param dict context: if a ``thread_model`` value is present
                                in the context, its value will be used
                                to determine the model of the thread to
                                update (instead of the current model).
        """
        return self.history(cr, uid, ids,
                            subject = msg_dict.get('subject'),
                            body_text = msg_dict.get('body_text'),
                            email_to = msg_dict.get('to'),
                            email_from = msg_dict.get('from'),
                            email_cc = msg_dict.get('cc'),
                            email_bcc = msg_dict.get('bcc'),
                            reply_to = msg_dict.get('reply'),
                            email_date = msg_dict.get('date'),
                            message_id = msg_dict.get('message-id'),
                            references = msg_dict.get('references')\
                                      or msg_dict.get('in-reply-to'),
                            attachments = msg_dict.get('attachments'),
                            body_html= msg_dict.get('body_html'),
                            subtype = msg_dict.get('subtype'),
                            headers = msg_dict.get('headers'),
                            original = msg_dict.get('original'),
                            context = context)

    def history(self, cr, uid, threads, subject, body_text=None, email_to=False,
                email_from=False, email_cc=None, email_bcc=None, reply_to=None,
                email_date=None, message_id=False, references=None,
                attachments=None, body_html=None, subtype=None, headers=None,
                original=None, context=None):
        """Creates a new mail.message attached to the current mail.thread,
           containing all the details passed as parameters.  All attachments
           will be attached to the thread record as well as to the actual
           message.

        :param threads: list of thread ids, or list of browse_records representing
                        threads to which a new message should be attached
        :param subject: Thread action keyword e.g.: If thread is closed "Close" keyword is used
        :param email_to: Email-To / Recipient address
        :param email_from: Email From / Sender address if any
        :param email_cc: Comma-Separated list of Carbon Copy Emails To addresse if any
        :param email_bcc: Comma-Separated list of Blind Carbon Copy Emails To addresses if any
        :param reply_to: reply_to header
        :param email_date: email date string if different from now, in server timezone
        :param message_id: optional email identifier
        :param references: optional email references
        :param body_text: plaintext contents of the mail or log message
        :param body_html: html contents of the mail or log message
        :param subtype: optional type of message: 'plain' or 'html', corresponding to the main
                        body contents (body_text or body_html).
        :param headers: mail headers to store
        :param dict attachments: map of attachment filenames to binary contents, if any.
        :param str original: optional full source of the RFC2822 email, for reference
        :param dict context: if a ``thread_model`` value is present
                             in the context, its value will be used
                             to determine the model of the thread to
                             update (instead of the current model).
        """
        if context is None:
            context = {}
        if attachments is None:
            attachments = {}

        if email_date:
            edate = parsedate(email_date)
            if edate is not None:
                email_date = time.strftime('%Y-%m-%d %H:%M:%S', edate)

        if all(isinstance(thread_id, (int, long)) for thread_id in threads):
            model = context.get('thread_model') or self._name
            model_pool = self.pool.get(model)
            threads = model_pool.browse(cr, uid, threads, context=context)

        ir_attachment = self.pool.get('ir.attachment')
        mail_message = self.pool.get('mail.message')

        for thread in threads:
            to_attach = []
            for fname, fcontent in attachments.items():
                if isinstance(fcontent, unicode):
                    fcontent = fcontent.encode('utf-8')
                data_attach = {
                    'name': fname,
                    'datas': binascii.b2a_base64(str(fcontent)),
                    'datas_fname': fname,
                    'description': _('Mail attachment'),
                    'res_model': thread._name,
                    'res_id': thread.id,
                }
                to_attach.append(ir_attachment.create(cr, uid, data_attach, context=context))

            partner_id = hasattr(thread, 'partner_id') and (thread.partner_id and thread.partner_id.id or False) or False
            if not partner_id and thread._name == 'res.partner':
                partner_id = thread.id
            data = {
                'subject': subject,
                'user_id': uid,
                'model' : thread._name,
                'partner_id': partner_id,
                'res_id': thread.id,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'message_id': message_id,
                'body_text': body_text or (hasattr(thread, 'description') and thread.description or False),
                'attachment_ids': [(6, 0, to_attach)]
            }

            if email_from:
                for param in (email_to, email_cc, email_bcc):
                    if isinstance(param, list):
                        param = ", ".join(param)
                data = {
                    'subject': subject or _('History'),
                    'user_id': uid,
                    'model' : thread._name,
                    'res_id': thread.id,
                    'date': email_date or time.strftime('%Y-%m-%d %H:%M:%S'),
                    'body_text': body_text,
                    'email_to': email_to,
                    'email_from': email_from or \
                        (hasattr(thread, 'user_id') and thread.user_id and thread.user_id.user_email),
                    'email_cc': email_cc,
                    'email_bcc': email_bcc,
                    'partner_id': partner_id,
                    'references': references,
                    'message_id': message_id,
                    'attachment_ids': [(6, 0, to_attach)],
                    'state' : 'received',
                    'body_html': body_html,
                    'subtype': subtype,
                    'headers': headers,
                    'reply_to': reply_to,
                    'original': original,
                }
            mail_message.create(cr, uid, data, context=context)
        return True

    def process_email(self, cr, uid, model, message, custom_values=None, context=None):
        """Process an incoming RFC2822 email message related to the
           given thread model, relying on ``mail.message.parse()``
           for the parsing operation, and then calling ``message_new``
           (if the thread record did not exist) or ``message_update``
           (if it did), then calling ``email_forward()`` to automatically
           notify other people that should receive this email.

           :param string model: the thread model for which a new message
                                must be processed
           :param message: source of the RFC2822 mail
           :type message: string or xmlrpclib.Binary
           :type dict custom_value: optional dictionary of field values
                                    to pass to ``message_new`` if a new
                                    record needs to be created. Ignored
                                    if the thread record already exists.
        """
        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)

        model_pool = self.pool.get(model)
        if self._name != model:
            if context is None: context = {}
            context.update({'thread_model':model})

        mail_message = self.pool.get('mail.message')
        res_id = False

        # Parse Message
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        msg = mail_message.parse_message(msg_txt)

        # Create New Record into particular model
        def create_record(msg):
            if hasattr(model_pool, 'message_new'):
                return model_pool.message_new(cr, uid, msg,
                                              custom_values,
                                              context=context)
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
                        if hasattr(model_pool, 'message_update'):
                            model_pool.message_update(cr, uid, [res_id], msg, {}, context=context)
        if not res_id:
            res_id = create_record(msg)
        #To forward the email to other followers
        self.email_forward(cr, uid, model, [res_id], msg_txt, context=context)
        return res_id

    def email_forward(self, cr, uid, model, thread_ids, msg, email_error=False, context=None):
        """Sends an email to all people following the given threads.
           The emails are forwarded immediately, not queued for sending,
           and not archived.

        :param str model: thread model
        :param list thread_ids: ids of the thread records
        :param msg: email.message.Message object to forward
        :param email_error: optional email address to notify in case
                            of any delivery error during the forward.
        :return: True
        """
        model_pool = self.pool.get(model)
        smtp_server_obj = self.pool.get('ir.mail_server')
        mail_message = self.pool.get('mail.message')
        for res in model_pool.browse(cr, uid, thread_ids, context=context):
            if hasattr(model_pool, 'thread_followers'):
                self.thread_followers = model_pool.thread_followers
            thread_followers = self.thread_followers(cr, uid, [res.id])[res.id]
            message_followers_emails = mail_message.to_email(','.join(filter(None, thread_followers)))
            message_recipients = mail_message.to_email(','.join(filter(None,
                                                                       [decode(msg['from']),
                                                                        decode(msg['to']),
                                                                        decode(msg['cc'])])))
            message_forward = [i for i in message_followers_emails if (i and (i not in message_recipients))]
            if message_forward:
                # TODO: we need an interface for this for all types of objects, not just leads
                if hasattr(res, 'section_id'):
                    del msg['reply-to']
                    msg['reply-to'] = res.section_id.reply_to

                smtp_from = mail_message.to_email(msg['from'])
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

    def get_partner(self, cr, uid, email, context=None):
        """Attempts to return the id of a partner address matching
           the given ``email``, and the corresponding partner.
           
           :param email: email address for which a partner
                         should be searched for.
           :rtype: dict
           :return: a map of the following form::

                      { 'partner_address_id': id or False,
                        'partner_id': pid or False }
        """
        address_pool = self.pool.get('res.partner.address')
        res = {
            'partner_address_id': False,
            'partner_id': False
        }
        email = to_email(email)[0]
        address_ids = address_pool.search(cr, uid, [('email', '=', email)])
        if address_ids:
            address = address_pool.browse(cr, uid, address_ids[0])
            res['partner_address_id'] = address_ids[0]
            res['partner_id'] = address.partner_id.id
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
