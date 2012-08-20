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

import base64
import email
import logging
import re
import time
import xmlrpclib
from email.utils import parsedate
from email.message import Message

from osv import osv, fields
from mail_message import decode
import tools
from tools.translate import _
from tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

def decode_header(message, header, separator=' '):
    return separator.join(map(decode,message.get_all(header, [])))

class mail_thread(osv.Model):
    '''Mixin model, meant to be inherited by any model that needs to
       act as a discussion topic on which messages can be attached.
       Public methods are prefixed with ``message_`` in order to avoid
       name collisions with methods of the models that will inherit
       from this mixin.

       ``mail.thread`` is designed to work without adding any field
       to the extended models. All functionalities and expected behavior
       are managed by mail.thread, using model name and record ids.
       A widget has been designed for the 6.1 and following version of OpenERP
       web-client. However, due to technical limitations, ``mail.thread``
       adds a simulated one2many field, to display the web widget by
       overriding the default field displayed. Using this field
       is not recommanded has it will disappeear in future version
       of OpenERP, leading to a pure mixin class.

       Inheriting classes are not required to implement any method, as the
       default implementation will work for any model. However it is common
       to override at least the ``message_new`` and ``message_update``
       methods (calling ``super``) to add model-specific behavior at
       creation and update of a thread.
       
       #TODO: UPDATE WITH SUBTYPE / NEW FOLLOW MECHANISM
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'
    # TODO: may be we should make it _inherit ir.needaction

    def _get_is_follower(self, cr, uid, ids, name, args, context=None):
        subobj = self.pool.get('mail.followers')
        subids = subobj.search(cr, uid, [
            ('res_model','=',self._name),
            ('res_id', 'in', ids),
            ('partner_id.user_ids','in',[uid])], context=context)
        result = dict.fromkeys(ids, False)
        for sub in subobj.browse(cr, uid, subids, context=context):
            result[sub.res_id] = True
        return result

    def _get_message_data(self, cr, uid, ids, name, args, context=None):
        res = {}
        for id in ids:
            res[id] = {
                'message_unread': False,
                'message_summary': ''
            }
        nobj = self.pool.get('mail.notification')
        nids = nobj.search(cr, uid, [
            ('partner_id.user_ids','in',[uid]),
            ('message_id.res_id','in', ids),
            ('message_id.model','=', self._name),
            ('read','=',False)
        ], context=context)
        for notif in nobj.browse(cr, uid, nids, context=context):
            res[notif.message_id.res_id]['message_unread'] = True

        for thread in self.browse(cr, uid, ids, context=context):
            message_ids = thread.message_ids
            follower_ids = thread.message_follower_ids
            res[id]['message_summary'] = "<span><span class='oe_e'>9</span> %d</span> <span><span class='oe_e'>+</span> %d</span>" % (len(message_ids), len(follower_ids)),
        return res

    # FP Note: todo
    def _search_unread(self, tobj, cr, uid, obj=None, name=None, domain=None, context=None):
        return []

    _columns = {
        'message_is_follower': fields.function(_get_is_follower,
            type='boolean', string='Is a Follower'),
        'message_follower_ids': fields.many2many('res.partner', 'mail_followers', 'res_id', 'partner_id',
            # FP Note: implement this domain=lambda self: [('res_model','=',self._name)],
            string='Followers'),
        'message_ids': fields.one2many('mail.message', 'res_id',
            domain=lambda self: [('model','=',self._name)],
            string='Related Messages', 
            help="All messages related to the current document."),
        'message_unread': fields.function(_get_message_data, fnct_search=_search_unread, 
            string='Has Unread Messages',
            help="When checked, new messages require your attention.",
            multi="_get_message_data"),
        'message_summary': fields.function(_get_message_data, method=True,
            type='text', string='Summary', multi="_get_message_data",
            help="Holds the Chatter summary (number of messages, ...). "\
                 "This summary is directly in html format in order to "\
                 "be inserted in kanban views."),
    }

    #------------------------------------------------------
    # Automatic subscription when creating/reading
    #------------------------------------------------------

    def create(self, cr, uid, vals, context=None):
        """ Override of create to subscribe the current user
        """
        thread_id = super(mail_thread, self).create(cr, uid, vals, context=context)
        self.message_subscribe_users(cr, uid, [thread_id], [uid], context=context)
        return thread_id

    def unlink(self, cr, uid, ids, context=None):
        """Override unlink, to automatically delete messages
           that are linked with res_model and res_id, not through
           a foreign key with a 'cascade' ondelete attribute.
           Notifications will be deleted with messages
        """
        msg_obj = self.pool.get('mail.message')
        # delete messages and notifications
        msg_to_del_ids = msg_obj.search(cr, uid, [('model', '=', self._name), ('res_id', 'in', ids)], context=context)
        msg_obj.unlink(cr, uid, msg_to_del_ids, context=context)
        return super(mail_thread, self).unlink(cr, uid, ids, context=context)

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context={}):
        if self._needaction:
            return [('message_unread','=',True)]
        return []

    #------------------------------------------------------
    # Mail gateway
    #------------------------------------------------------

    def _message_find_partners(self, cr, uid, message, headers=['From'], context=None):
        s = ', '.join([decode(message.get(h)) for h in headers])
        mails = tools.email_split(s)
        result = []
        for m in mails:
            result += self.pool.get('res.partner').search(cr, uid, [('email','ilike',m)], context=context)
        return result

    def _message_find_user_id(self, cr, uid, message, context=None):
        from_local_part = tools.email_split(decode(message.get('From')))[0]
        # FP Note: canonification required, the minimu: .lower()
        user_ids = self.pool.get('res.users').search(cr, uid, ['|', 
            ('login', '=', from_local_part),
            ('email', '=', from_local_part)], context=context)
        return user_ids[0] if user_ids else uid

    def message_route(self, cr, uid, message, model=None, thread_id=None,
                      custom_values=None, context=None):
        """Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:
             1. If the message replies to an existing thread_id, and
                properly contains the thread model in the 'In-Reply-To'
                header, use this model/thread_id pair, and ignore
                custom_value (not needed as no creation will take place)
             2. Look for a mail.alias entry matching the message
                recipient, and use the corresponding model, thread_id,
                custom_values and user_id.
             3. Fallback to the ``model``, ``thread_id`` and ``custom_values``
                provided.
             4. If all the above fails, raise an exception.

           :param string message: an email.message instance
           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :type dict custom_values: optional dictionary of default field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. Only used if the message
               does not reply to an existing thread and does not match any mail alias.
           :return: list of [model, thread_id, custom_values, user_id]
        """
        assert isinstance(message, Message), 'message must be an email.message.Message at this point'
        message_id = message.get('Message-Id')

        # 1. Verify if this is a reply to an existing thread
        references = decode_header(message, 'References') or decode_header(message, 'In-Reply-To')
        ref_match = references and tools.reference_re.search(references)
        if ref_match:
            thread_id = int(ref_match.group(1))
            model = ref_match.group(2) or model
            model_pool = self.pool.get(model)
            if thread_id and model and model_pool and model_pool.exists(cr, uid, thread_id) \
                and hasattr(model_pool, 'message_update'):
                _logger.debug('Routing mail with Message-Id %s: direct reply to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                              message_id, model, thread_id, custom_values, uid)
                return [(model, thread_id, custom_values, uid)]

        # 2. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = decode_header(message, 'Delivered-To') or \
             ','.join([decode_header(message, 'To'),
                       decode_header(message, 'Cc'),
                       decode_header(message, 'Resent-To'),
                       decode_header(message, 'Resent-Cc')])
        local_parts = [e.split('@')[0] for e in tools.email_split(rcpt_tos)]
        if local_parts:
            mail_alias = self.pool.get('mail.alias')
            alias_ids = mail_alias.search(cr, uid, [('alias_name', 'in', local_parts)])
            if alias_ids:
                routes = []
                for alias in mail_alias.browse(cr, uid, alias_ids, context=context):
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        user_id = self._message_find_user_id(cr, uid, message, context=context)
                    routes.append((alias.alias_model_id.model, alias.alias_force_thread_id, \
                                   eval(alias.alias_defaults), user_id))
                _logger.debug('Routing mail with Message-Id %s: direct alias match: %r', message_id, routes)
                return routes

        # 3. Fallback to the provided parameters, if they work
        model_pool = self.pool.get(model)
        if not thread_id:
            # Legacy: fallback to matching [ID] in the Subject
            match = tools.res_re.search(decode_header(message, 'Subject'))
            thread_id = match and match.group(1)
        assert thread_id and hasattr(model_pool, 'message_update') or hasattr(model_pool, 'message_new'), \
            "No possible route found for incoming message with Message-Id %s. " \
            "Create an appropriate mail.alias or force the destination model." % message_id
        if thread_id and not model_pool.exists(cr, uid, thread_id):
            _logger.warning('Received mail reply to missing document %s! Ignoring and creating new document instead for Message-Id %s',
                            thread_id, message_id)
            thread_id = None
        _logger.debug('Routing mail with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                      message_id, model, thread_id, custom_values, uid)
        return [(model, thread_id, custom_values, uid)]

    def message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, context=None):
        """Process an incoming RFC2822 email message, relying on
           ``mail.message.parse()`` for the parsing operation,
           and ``message_route()`` to figure out the target model.

           Once the target model is known, its ``message_new`` method
           is called with the new message (if the thread record did not exist)
            or its ``message_update`` method (if it did).

           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :param message: source of the RFC2822 message
           :type message: string or xmlrpclib.Binary
           :type dict custom_values: optional dictionary of field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param bool save_original: whether to keep a copy of the original
                email source attached to the message after it is imported.
           :param bool strip_attachments: whether to strip all attachments
                before processing the message, in order to save some space.
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. When provided, this
               overrides the automatic detection based on the message
               headers.
        """
        if context is None: context = {}

        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
        msg_txt = email.message_from_string(message)
        routes = self.message_route(cr, uid, msg_txt, model,
                                    thread_id, custom_values,
                                    context=context)
        msg = self.pool.get('mail.message').parse_message(msg_txt, save_original=save_original, context=context)
        msg['state'] = 'received'
        if strip_attachments and 'attachments' in msg:
            del msg['attachments']
        for model, thread_id, custom_values, user_id in routes:
            if self._name != model:
                context.update({'thread_model': model})
            model_pool = self.pool.get(model)
            assert thread_id and hasattr(model_pool, 'message_update') or hasattr(model_pool, 'message_new'), \
                "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" % \
                    (msg['message-id'], model)
            if thread_id and hasattr(model_pool, 'message_update'):
                model_pool.message_update(cr, user_id, [thread_id], msg, context=context)
            else:
                thread_id = model_pool.message_new(cr, user_id, msg, custom_values, context=context)
            self.message_post(cr, uid, thread_id, context=context, **msg)
        return True

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
            data['name'] = msg_dict.get('subject', '')
        if custom_values and isinstance(custom_values, dict):
            data.update(custom_values)
        res_id = model_pool.create(cr, uid, data, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg_dict, update_vals=None, context=None):
        """Called by ``message_process`` when a new message is received
           for an existing thread. The default behavior is to create a
           new mail.message in the given thread (by calling
           ``message_append_dict``)
           Additional behavior may be implemented by overriding this
           method.
           :param dict msg_dict: a map containing the email details and
                               attachments. See ``message_process`` and
                               ``mail.message.parse()`` for details.
           :param dict update_vals: a dict containing values to update records
                              given their ids; if the dict is None or is
                              void, no write operation is performed.
        """
        if update_vals:
            self.write(cr, uid, ids, update_vals, context=context)
        return True

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
                      'from': from,          --> author_id
                      'to': to,              --> partner_ids
                      'cc': cc,              --> partner_ids
                      'headers' : { 'X-Mailer': mailer,  --> to remove
                                    #.. all X- headers...
                                  },
                      'content_subtype': msg_mime_subtype,  --> to remove
                      'body': plaintext_body           --> keep body
                      'body_html': html_body,               --> to remove
                      'attachments': [('file1', 'bytes'),
                                       ('file2', 'bytes') }
                       # ...
                       'original': source_of_email,         --> attachment document
                    }
        """
        msg_txt = message
        attachments = []
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
            msg_original = message.as_string() if isinstance(message, Message) \
                                                  else message
            attachments.append(('email.eml', msg_original))

        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['message-id'] = message_id
            _logger.info('Parsing Message without message-id, generating a random one: %s', message_id)

        msg_fields = msg_txt.keys()

        msg['message_id'] = message_id

        if 'Subject' in msg_fields:
            msg['subject'] = decode(msg_txt.get('Subject'))

        #if 'Content-Type' in msg_fields:
        #    msg['content-type'] = msg_txt.get('Content-Type')

        # find author_id

        if 'From' in msg_fields:
            author_ids = self._message_find_partners(cr, uid, msg_text, ['From'], context=context)
            #decode(msg_txt.get('From') or msg_txt.get_unixfrom()) )
            if author_ids:
                msg['author_id'] = author_ids[0]

        partner_ids = self._message_find_partners(cr, uid, msg_text, ['From','To','Delivered-To','CC','Cc'], context=context)
        msg['partner_ids'] = partner_ids

        #if 'To' in msg_fields:
        #    msg['to'] = decode(msg_txt.get('To'))

        #if 'Delivered-To' in msg_fields:
        #    msg['to'] = decode(msg_txt.get('Delivered-To'))

        #if 'CC' in msg_fields:
        #    msg['cc'] = decode(msg_txt.get('CC'))

        #if 'Cc' in msg_fields:
        #    msg['cc'] = decode(msg_txt.get('Cc'))

        #if 'Reply-To' in msg_fields:
        #    msg['reply'] = decode(msg_txt.get('Reply-To'))

        # FP Note: I propose to store the current datetime rather than the email date
        #if 'Date' in msg_fields:
        #    date_hdr = decode(msg_txt.get('Date'))
        #    # convert from email timezone to server timezone
        #    date_server_datetime = dateutil.parser.parse(date_hdr).astimezone(pytz.timezone(tools.get_server_timezone()))
        #    date_server_datetime_str = date_server_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        #    msg['date'] = date_server_datetime_str

        #if 'Content-Transfer-Encoding' in msg_fields:
        #    msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')

        #if 'References' in msg_fields:
        #    msg['references'] = msg_txt.get('References')

        # FP Note: todo - find parent_id
        if 'In-Reply-To' in msg_fields:
            pass

        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            body = msg_txt.get_payload(decode=True)
            if 'text/html' in msg.get('content-type', ''):
                msg['body'] =  body

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
                        attachments.append(( filename, msg_original))
                    content = tools.ustr(content, encoding)
                    msg['body'] = content
                elif part.get_content_maintype() in ('application', 'image'):
                    if filename:
                        attachments.append(( filename, part.get_payload(decode=True)))
                    else:
                        res = part.get_payload(decode=True)
                        msg['body'] += tools.ustr(res, encoding)

        msg['attachments'] = attachments
        return msg

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    def log(self, cr, uid, id, message, secondary=False, context=None):
        _logger.warning("log() is deprecated. As this module inherit from \
                        mail.thread, the message will be managed by this \
                        module instead of by the res.log mechanism. Please \
                        use the mail.thread OpenChatter API instead of the \
                        now deprecated res.log.")
        self.message_post(cr, uid, id, message, context=context)

    def message_post(self, cr, uid, res_id, body, subject=False,
            mtype='notification', attachments=None, context=None, **kwargs):

        context = context or {}
        attachments = attachments or {}
        if type(res_id) in (list, tuple):
            res_id = res_id and res_id[0] or False

        to_attach = []
        for fname, fcontent in attachments:
            if isinstance(fcontent, unicode):
                fcontent = fcontent.encode('utf-8')
            data_attach = {
                'name': fname,
                'datas': fcontent,
                'datas_fname': fname,
                'description': _('email attachment'),
            }
            to_attach.append((0,0, data_attach))

        value = kwargs
        value.update( {
            'model': res_id and self._name or False,
            'res_id': res_id,
            'body': body,
            'subject': subject,
            'type': mtype,
            'attachment_ids': to_attach
        })
        return self.pool.get('mail.message').create(cr, uid, value, context=context)


    #------------------------------------------------------
    # Subscription mechanism
    #------------------------------------------------------

    def message_subscribe_users(self, cr, uid, ids, user_ids=None, context=None):
        if not user_ids: user_ids = [uid]
        partners = {}
        for user in self.pool.get('res.users').browse(cr, uid, user_ids, context=context):
            partners[user.partner_id.id] = True
        return self.message_subscribe(cr, uid, ids, partners.keys(), context=context)

    def message_subscribe(self, cr, uid, ids, partner_ids, context=None):
        """
            :param partner_ids: a list of user_ids; if not set, subscribe
                             uid instead
            :param return: new value of followers, for Chatter
        """
        obj = self.pool.get('mail.followers')
        objids = obj.search(cr, uid, [
            ('res_id', 'in', ids),
            ('res_model', '=', self._name),
            ('partner_id', 'in', partner_ids),
            ], context=context)
        followers = {}
        for follow in obj.browse(cr, uid, objids, context=context):
            followers.setdefault(follow.partner_id.id, {})[follow.res_id] = True
        create_ids = []
        for res_id in ids:
            for partner_id in partner_ids:
                if followers.get(partner_id, {}).get(res_id, False):
                    continue
                create_ids.append(obj.create(cr, uid, {
                    'res_model': self._name,
                    'res_id': res_id, 'partner_id': partner_id
                }, context=context))
        return create_ids

    def message_unsubscribe(self, cr, uid, ids, user_ids = None, context=None):
        """ Unsubscribe the user (or user_ids) from the current document.

            :param user_ids: a list of user_ids; if not set, subscribe
                             uid instead
            :param return: new value of followers, for Chatter
        """
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        self.write(cr, uid, ids, [(3, partner_id)], context=context)

        # FP Note: do we need this ?
        return [follower.id for thread in self.browse(cr, uid, ids, context=context) for follower in thread.message_follower_ids]

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    def message_remove_pushed_notifications(self, cr, uid, ids, msg_ids, remove_childs=True, context=None):
        notif_obj = self.pool.get('mail.notification')
        msg_obj = self.pool.get('mail.message')
        if remove_childs:
            notif_msg_ids = msg_obj.search(cr, uid, [('id', 'child_of', msg_ids)], context=context)
        else:
            notif_msg_ids = msg_ids
        to_del_notif_ids = notif_obj.search(cr, uid, ['&', ('user_id', '=', uid), ('message_id', 'in', notif_msg_ids)], context=context)
        return notif_obj.unlink(cr, uid, to_del_notif_ids, context=context)

    #------------------------------------------------------
    # Thread_state
    #------------------------------------------------------

    # FP Note: this should be a invert function on message_unread field
    # not sure because if not readonly, it may often write to this field?
    def message_mark_as_unread(self, cr, uid, ids, context=None):
        """ Set as read. """
        notobj = self.pool.get('mail.notification')
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        cr.execute('''
            UPDATE mail_notification SET 
                read=false
            WHERE
                message_id IN (SELECT id from mail_message where res_id=any(%s) and model=%s limit 1) and
                partner_id = %s
        ''', (ids, self._name, partner_id))
        return True

    def message_mark_as_read(self, cr, uid, ids, context=None):
        """ Set as read. """
        notobj = self.pool.get('mail.notification')
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        cr.execute('''
            UPDATE mail_notification SET 
                read=true
            WHERE
                message_id IN (SELECT id FROM mail_message WHERE res_id=ANY(%s) AND model=%s) AND
                partner_id = %s
        ''', (ids, self._name, partner_id))
        return True

