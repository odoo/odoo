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
import base64
import email
from email.utils import parsedate

import logging
import xmlrpclib
from osv import osv, fields
from tools.translate import _
from mail_message import decode, to_email

_logger = logging.getLogger(__name__)

class mail_thread(osv.osv):
    '''Mixin model, meant to be inherited by any model that needs to
       act as a discussion topic on which messages can be attached.
       Public methods are prefixed with ``message_`` in order to avoid
       name collisions with methods of the models that will inherit
       from this mixin.

       ``mail.thread`` adds a one2many of mail.messages, acting as the
       thread's history, and a few methods that may be overridden to
       implement model-specific behavior upon arrival of new messages.

       Inheriting classes are not required to implement any method, as the
       default implementation will work for any model. However it is common
       to override at least the ``message_new`` and ``message_update``
       methods (calling ``super``) to add model-specific behavior at
       creation and update of a thread.

    '''
    _name = 'mail.thread'
    _description = 'Email Thread'
    
    def _get_message_ids(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for thread in self.browse(cr, uid, ids, context=context):
            records = self.message_load(cr, uid, [thread.id], context=context)
            res[thread.id] = [obj['id'] for obj in records]
        return res
    
    # OpenSocial: removed message_ids and copy method, this will be replaced by message_load
    _columns = {
        'message_ids_social': fields.function(_get_message_ids, method=True,
                        type='one2many', obj='mail.message', string='Temp messages',
                        ),
                        #widget='mail.ThreadView'),
    }
    
    #------------------------------------------------------
    # Generic message api
    #------------------------------------------------------
    def message_capable_models(self, cr, uid, context=None):
        ret_dict = {}
        for model_name in self.pool.obj_list():
            model = self.pool.get(model_name)
            if 'mail.thread' in getattr(model, '_inherit', []):
                ret_dict[model_name] = model._description        
        return ret_dict

    def message_append(self, cr, uid, threads, subject, body_text=None,
                        type='email', need_action_user_id=False,
                        email_to=False, email_from=False, email_cc=None, email_bcc=None,
                        reply_to=None, email_date=None, message_id=False, references=None,
                        attachments=None, body_html=None, subtype=None, headers=None,
                        original=None, context=None):
        """Creates a new mail.message attached to the current mail.thread,
           containing all the details passed as parameters.  All attachments
           will be attached to the thread record as well as to the actual
           message.
           If only the ``threads`` and ``subject`` parameters are provided,
           a *event log* message is created, without the usual envelope
           attributes (sender, recipients, etc.). 

        :param threads: list of thread ids, or list of browse_records representing
                        threads to which a new message should be attached
        :param subject: subject of the message, or description of the event if this
                        is an *event log* entry.
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
            for attachment in attachments:
                fname, fcontent = attachment
                if isinstance(fcontent, unicode):
                    fcontent = fcontent.encode('utf-8')
                data_attach = {
                    'name': fname,
                    'datas': base64.b64encode(str(fcontent)),
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
                'attachment_ids': [(6, 0, to_attach)],
                'state': 'received',
                'type': type,
                'need_action_user_id': need_action_user_id,
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

    def message_append_dict(self, cr, uid, ids, msg_dict, context=None):
        """Creates a new mail.message attached to the given threads (``ids``),
           with the contents of ``msg_dict``, by calling ``message_append``
           with the mail details. All attachments in msg_dict will be
           attached to the object record as well as to the actual
           mail message.

           :param dict msg_dict: a map containing the email details and
                                 attachments. See ``message_process()`` and
                                ``mail.message.parse()`` for details on
                                the dict structure.
           :param dict context: if a ``thread_model`` value is present
                                in the context, its value will be used
                                to determine the model of the thread to
                                update (instead of the current model).
        """
        # 6.2 OpenSocial feature: add default email type for old API
        if not 'type' in msg_dict: msg_dict['type'] = 'email'
        return self.message_append(cr, uid, ids,
                            subject = msg_dict.get('subject'),
                            body_text = msg_dict.get('body_text'),
                            type = msg_dict.get('type'),
                            need_action_user_id = msg_dict.get('need_action_user_id'),
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

    # Message loading
    def message_load_ids(self, cr, uid, ids, context=None):
        """ OpenSocial feature: return thread messages ids (for web compatibility)
        loading messages: search in mail.messages where res_id = ids, (res_)model = current model
        """
        msg_obj = self.pool.get('mail.message')
        msg_ids = msg_obj.search(cr, uid, ['&', ('res_id', 'in', ids), ('model', '=', self._name)], context=context)
        return msg_ids
        
    def message_load(self, cr, uid, ids, context=None):
        """ OpenSocial feature: return thread messages
        loading messages: search in mail.messages where res_id = ids, (res_)model = current model
        """
        msg_ids = self.message_load_ids(cr, uid, ids, context=context)
        return self.pool.get('mail.message').read(cr, uid, msg_ids, context=context)

    #------------------------------------------------------
    # Email specific
    #------------------------------------------------------
    # message_process will call either message_new or message_update.

    def message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        context=None):
        """Process an incoming RFC2822 email message related to the
           given thread model, relying on ``mail.message.parse()``
           for the parsing operation, and then calling ``message_new``
           (if the thread record did not exist) or ``message_update``
           (if it did), then calling ``message_forward`` to automatically
           notify other people that should receive this message.

           :param string model: the thread model for which a new message
                                must be processed
           :param message: source of the RFC2822 mail
           :type message: string or xmlrpclib.Binary
           :type dict custom_values: optional dictionary of field values
                                    to pass to ``message_new`` if a new
                                    record needs to be created. Ignored
                                    if the thread record already exists.
           :param bool save_original: whether to keep a copy of the original
               email source attached to the message after it is imported.
           :param bool strip_attachments: whether to strip all attachments
               before processing the message, in order to save some space.
        """
        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)

        model_pool = self.pool.get(model)
        if self._name != model:
            if context is None: context = {}
            context.update({'thread_model': model})

        mail_message = self.pool.get('mail.message')
        res_id = False

        # Parse Message
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        msg = mail_message.parse_message(msg_txt, save_original=save_original)

        if strip_attachments and 'attachments' in msg:
            del msg['attachments']

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
                    else:
                        # referenced thread was not found, we'll have to create a new one
                        res_id = False
        if not res_id:
            res_id = create_record(msg)
        #To forward the email to other followers
        self.message_forward(cr, uid, model, [res_id], msg_txt, context=context)
        return res_id

    def message_new(self, cr, uid, msg_dict, custom_values=None, context=None):
        """Called by ``message_process`` when a new message is received
           for a given thread model, if the message did not belong to 
           an existing thread.
           The default behavior is to create a new record of the corresponding
           model (based on some very basic info extracted from the message),
           then attach the message to the newly created record
           (by calling ``message_append_dict``).
           Additional behavior may be implemented by overriding this method.

           :param dict msg_dict: a map containing the email details and
                                 attachments. See ``message_process`` and
                                ``mail.message.parse`` for details.
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
        self.message_append_dict(cr, uid, [res_id], msg_dict, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg_dict, vals={}, default_act=None, context=None):
        """Called by ``message_process`` when a new message is received
           for an existing thread. The default behavior is to create a
           new mail.message in the given thread (by calling
           ``message_append_dict``)
           Additional behavior may be implemented by overriding this
           method.

           :param dict msg_dict: a map containing the email details and
                                attachments. See ``message_process`` and
                                ``mail.message.parse()`` for details.
           :param dict context: if a ``thread_model`` value is present
                                in the context, its value will be used
                                to determine the model of the thread to
                                update (instead of the current model).
        """
        return self.message_append_dict(cr, uid, ids, msg_dict, context=context)

    def message_thread_followers(self, cr, uid, ids, context=None):
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
                l.add((message.user_id and message.user_id.user_email) or '')
                l.add(message.email_from or '')
                l.add(message.email_cc or '')
            res[thread.id] = filter(None, l)
        return res

    def message_forward(self, cr, uid, model, thread_ids, msg, email_error=False, context=None):
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
            if hasattr(model_pool, 'message_thread_followers'):
                followers = model_pool.message_thread_followers(cr, uid, [res.id])[res.id]
            else:
                followers = self.message_thread_followers(cr, uid, [res.id])[res.id]
            message_followers_emails = to_email(','.join(filter(None, followers)))
            message_recipients = to_email(','.join(filter(None,
                                                                       [decode(msg['from']),
                                                                        decode(msg['to']),
                                                                        decode(msg['cc'])])))
            forward_to = [i for i in message_followers_emails if (i and (i not in message_recipients))]
            if forward_to:
                # TODO: we need an interface for this for all types of objects, not just leads
                if hasattr(res, 'section_id'):
                    del msg['reply-to']
                    msg['reply-to'] = res.section_id.reply_to

                smtp_from, = to_email(msg['from'])
                msg['from'] = smtp_from
                msg['to'] =  ", ".join(forward_to)
                msg['message-id'] = tools.generate_tracking_message_id(res.id)
                if not smtp_server_obj.send_email(cr, uid, msg) and email_error:
                    subj = msg['subject']
                    del msg['subject'], msg['to'], msg['cc'], msg['bcc']
                    msg['subject'] = _('[OpenERP-Forward-Failed] %s') % subj
                    msg['to'] = email_error
                    smtp_server_obj.send_email(cr, uid, msg)
        return True

    def message_partner_by_email(self, cr, uid, email, context=None):
        """Attempts to return the id of a partner address matching
           the given ``email``, and the corresponding partner id.
           Can be used by classes using the ``mail.thread`` mixin
           to lookup the partner and use it in their implementation
           of ``message_new`` to link the new record with a
           corresponding partner.
           The keys used in the returned dict are meant to map
           to usual names for relationships towards a partner
           and one of its addresses.
           
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
        if email:
            email = to_email(email)[0]
            address_ids = address_pool.search(cr, uid, [('email', '=', email)])
            if address_ids:
                address = address_pool.browse(cr, uid, address_ids[0])
                res['partner_address_id'] = address_ids[0]
                res['partner_id'] = address.partner_id.id
        return res

    # for backwards-compatibility with old scripts
    process_email = message_process

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------
    
    def message_append_note(self, cr, uid, ids, subject, body, type='notification', need_action_user_id=False, context=None):
        return self.message_append(cr, uid, ids, subject, body_text=body, type=type, need_action_user_id=need_action_user_id, context=context)
    
    # old log overrided method: now calls message_append_note
    def log(self, cr, uid, id, message, secondary=False, context=None):
        """ OpenSocial add: new res_log implementation
        A res.log is now a mail.message, as all messages in OpenERP
        It has a notification type.
        It can have a need_action flag attached if an user
        has to perform a given action.
        See mail.message, mail.subscription and mail.notification for more details.
        """
        if context and context.get('disable_log'):
            #return True # old behavior
            print 'Log diabled, but we do not care currently about that. We want you to have our logs !'
        #return self.message_append_note(cr, uid, [id], 'System notification', message, context=context)
    
    def message_mark_done(self, cr, uid, ids, context=None):
        """ OpenSocial add: mark a need_action message sa done
        Find by: res_id (thread id), model (self._name), need_action_user_id != false
        """
        msg_obj = self.pool.get('mail.message')
        msg_ids = msg_obj.search(cr, uid,
                        ['&', '&', ('res_id', 'in', ids), ('model', '=', self._name), ('need_action_user_id', '!=', False)], context=context)
        msg_obj.write(cr, uid, msg_ids, {'need_action_user_id': False}, context=context)
        return True
            
    #------------------------------------------------------
    # Subscription mechanism
    #------------------------------------------------------
    
    def message_get_subscribers_ids(self, cr, uid, ids, context=None):
        subscription_obj = self.pool.get('mail.subscription')
        sub_ids = subscription_obj.search(cr, uid, ['&', ('res_model', '=', self._name), ('res_id', 'in', ids)], context=context)
        subs = subscription_obj.read(cr, uid, sub_ids, context=context)
        return [sub['user_id'][0] for sub in subs]
    
    def message_get_subscribers(self, cr, uid, ids, context=None):
        user_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context)
        users = self.pool.get('res.users').read(cr, uid, user_ids, context=context)
        return users
    
    def message_is_subscriber(self, cr, uid, ids, context=None):
        subscription_obj = self.pool.get('mail.subscription')
        sub_ids = subscription_obj.search(cr, uid,
                        ['&', '&',  ('res_model', '=', self._name), ('res_id', 'in', ids), ('user_id', '=', uid)], context=context)
        if len(sub_ids) > 1:
            print 'cacaprout error !'
        return True if sub_ids else False
    
    def message_subscribe(self, cr, uid, ids, user_ids = None, context=None):
        subscription_obj = self.pool.get('mail.subscription')
        sub_user_ids = [uid] if user_ids is None else user_ids
        for id in ids:
            create_ids = [subscription_obj.create(cr, uid, {'res_model': self._name, 'res_id': id, 'user_id': user_id}, context=context)
                            for user_id in sub_user_ids]
        return create_ids

    def message_unsubscribe(self, cr, uid, ids, context=None):
        subscription_obj = self.pool.get('mail.subscription')
        subscriber_id = uid # TODO
        sub_ids = subscription_obj.search(cr, uid,
                        ['&', '&', ('res_model', '=', self._name), ('res_id', 'in', ids), ('user_id', '=', subscriber_id)], context=context)
        subscription_obj.unlink(cr, uid, sub_ids, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
