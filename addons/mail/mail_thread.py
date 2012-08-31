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
import dateutil
import email
import logging
import pytz
import re
import time
import tools
import xmlrpclib

from email.utils import parsedate
from email.message import Message
from mail_message import decode
from osv import osv, fields
from tools.translate import _
from tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

def decode_header(message, header, separator=' '):
    return separator.join(map(decode,message.get_all(header, [])))

class many2many_reference(fields.many2many):
    """ many2many_reference is an override of fields.many2many. It manages
        many2many-like table where one id is given by two fields, res_model
        and res_id.
    """
    
    def _get_query_and_where_params(self, cr, model, ids, values, where_params):
        """ Add in where:
            - ``mail_followers``.res_model = 'crm.lead'
        """
        # reference column name: given by attribute or res_model
        ref_col_name = self.ref_col_name if self.ref_col_name else 'res_model'
        values.update({'ref_col_name': ref_col_name, 'ref_col_value': model._name})

        query = 'SELECT %(rel)s.%(id2)s, %(rel)s.%(id1)s \
                    FROM %(rel)s, %(from_c)s \
                    WHERE %(rel)s.%(id1)s IN %%s \
                    AND %(rel)s.%(id2)s = %(tbl)s.id \
                    AND %(rel)s.%(ref_col_name)s = \'%(ref_col_value)s\' \
                    %(where_c)s  \
                    %(order_by)s \
                    %(limit)s \
                    OFFSET %(offset)d' \
                % values
        return query, where_params

    def set(self, cr, model, id, name, values, user=None, context=None):
        """ Override to add the res_model field in queries. """
        if not values: return
        rel, id1, id2 = self._sql_names(model)
        obj = model.pool.get(self._obj)
        # reference column name: given by attribute or res_model
        ref_col_name = self.ref_col_name if self.ref_col_name else 'res_model'
        for act in values:
            if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
                continue
            if act[0] == 0:
                idnew = obj.create(cr, user, act[2], context=context)
                cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+','+ref_col_name+') VALUES (%s,%s,%s)', (id, idnew, model._name))
            elif act[0] == 3:
                cr.execute('DELETE FROM '+rel+' WHERE '+id1+'=%s AND '+id2+'=%s AND '+ref_col_name+'=%s', (id, act[1], model._name))
            elif act[0] == 4:
                # following queries are in the same transaction - so should be relatively safe
                cr.execute('SELECT 1 FROM '+rel+' WHERE '+id1+'=%s AND '+id2+'=%s AND '+ref_col_name+'=%s', (id, act[1], model._name))
                if not cr.fetchone():
                    cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+','+ref_col_name+') VALUES (%s,%s,%s)', (id, act[1], model._name))
            elif act[0] == 5:
                cr.execute('delete from '+rel+' where '+id1+' = %s AND '+ref_col_name+'=%s', (id, model._name))
            elif act[0] == 6:
                d1, d2,tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
                if d1:
                    d1 = ' and ' + ' and '.join(d1)
                else:
                    d1 = ''
                cr.execute('DELETE FROM '+rel+' WHERE '+id1+'=%s AND '+ref_col_name+'=%s AND '+id2+' IN (SELECT '+rel+'.'+id2+' FROM '+rel+', '+','.join(tables)+' WHERE '+rel+'.'+id1+'=%s AND '+rel+'.'+id2+' = '+obj._table+'.id '+ d1 +')', [id, model._name, id]+d2)
                for act_nbr in act[2]:
                    cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+','+ref_col_name+') VALUES (%s,%s,%s)', (id, act_nbr, model._name))
            # cases 1, 2: performs write and unlink -> default implementation is ok
            else:
                return super(many2many_reference, self).set(cr, model, id, name, values, user, context)

class mail_thread(osv.Model):
    ''' mail_thread model is meant to be inherited by any model that needs to
        act as a discussion topic on which messages can be attached. Public
        methods are prefixed with ``message_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.

        ``mail.thread`` defines fields used to handle and display the
        communication history. ``mail.thread`` also manages followers of
        inheriting classes. All features and expected behavior are managed
        by mail.thread. Widgets has been designed for the 7.0 and following
        versions of OpenERP.

        Inheriting classes are not required to implement any method, as the
        default implementation will work for any model. However it is common
        to override at least the ``message_new`` and ``message_update``
        methods (calling ``super``) to add model-specific behavior at
        creation and update of a thread when processing incoming emails.
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'

    def _get_message_data(self, cr, uid, ids, name, args, context=None):
        res = dict( (id, dict(message_unread=False, message_summary='')) for id in ids)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id.user_ids', 'in', [uid]),
            ('message_id.res_id', 'in', ids),
            ('message_id.model', '=', self._name),
            ('read', '=', False)
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.res_id]['message_unread'] = True

        for thread in self.browse(cr, uid, ids, context=context):
            cls = res[thread.id]['message_unread'] and ' class="oe_kanban_mail_new"' or ''
            res[thread.id]['message_summary'] = "<span%s><span class='oe_e'>9</span> %d</span> <span><span class='oe_e'>+</span> %d</span>" % (cls, len(thread.message_comment_ids), len(thread.message_follower_ids))
            res[thread.id]['message_is_follower'] = user.partner_id.id in [follower.id for follower in thread.message_follower_ids]
        return res

    def _search_unread(self, cr, uid, obj=None, name=None, domain=None, context=None):
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        res = {}
        notif_obj = self.pool.get('mail.notification')
        notif_ids = notif_obj.search(cr, uid, [
            ('partner_id', '=', partner_id),
            ('message_id.model', '=', self._name),
            ('read', '=', False)
        ], context=context)
        for notif in notif_obj.browse(cr, uid, notif_ids, context=context):
            res[notif.message_id.res_id] = True
        return [('id','in',res.keys())]

    _columns = {
        'message_is_follower': fields.function(_get_message_data,
            type='boolean', string='Is a Follower', multi='_get_message_data'),
        'message_follower_ids': many2many_reference('res.partner',
            'mail_followers', 'res_id', 'partner_id',
            ref_col_name='res_model', string='Followers'),
        'message_comment_ids': fields.one2many('mail.message', 'res_id',
            domain=lambda self: [('model','=',self._name),('type','in',('comment','email'))],
            string='Related Messages', 
            help="All messages related to the current document."),
        'message_ids': fields.one2many('mail.message', 'res_id',
            domain=lambda self: [('model','=',self._name)],
            string='Related Messages', 
            help="All messages related to the current document."),
        'message_unread': fields.function(_get_message_data, fnct_search=_search_unread, 
            string='Has Unread Messages', type='boolean',
            help="When checked, new messages require your attention.",
            multi="_get_message_data"),
        'message_summary': fields.function(_get_message_data, method=True,
            type='text', string='Summary', multi="_get_message_data",
            help="Holds the Chatter summary (number of messages, ...). "\
                 "This summary is directly in html format in order to "\
                 "be inserted in kanban views."),
    }

    #------------------------------------------------------
    # Automatic subscription when creating
    #------------------------------------------------------

    def create(self, cr, uid, vals, context=None):
        """ Override of create to subscribe the current user. """
        thread_id = super(mail_thread, self).create(cr, uid, vals, context=context)
        self.message_subscribe_users(cr, uid, [thread_id], [uid], context=context)
        return thread_id

    def unlink(self, cr, uid, ids, context=None):
        """ Override unlink to delete messages and followers. This cannot be
            cascaded, because link is done through (res_model, res_id). """
        msg_obj = self.pool.get('mail.message')
        fol_obj = self.pool.get('mail.followers')
        # delete messages and notifications
        msg_ids = msg_obj.search(cr, uid, [('model', '=', self._name), ('res_id', 'in', ids)], context=context)
        msg_obj.unlink(cr, uid, msg_ids, context=context)
        # delete followers
        fol_ids = fol_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids)], context=context)
        fol_obj.unlink(cr, uid, fol_ids, context=context)
        return super(mail_thread, self).unlink(cr, uid, ids, context=context)

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context={}):
        if self._needaction:
            return [('message_unread', '=', True)]
        return []
    #------------------------------------------------------
    # Mail gateway
    #------------------------------------------------------

    def _message_find_partners(self, cr, uid, message, header_fields=['From'], context=None):
        """ Find partners related to some header fields of the message. """
        s = ', '.join([decode(message.get(h)) for h in header_fields if message.get(h)])
        mails = tools.email_split(s)
        result = []
        for email in mails:
            result += self.pool.get('res.partner').search(cr, uid, [('email', 'ilike', email)], context=context)
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
        msg = self.message_parse(cr, uid, msg_txt, save_original=save_original, context=context)
        if strip_attachments: msg.pop('attachments', None)
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
            self.message_post(cr, uid, [thread_id], context=context, **msg)
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

    def _message_extract_payload(self, message, save_original=False):
        """Extract body as HTML and attachments from the mail message"""
        attachments = []
        body = u''
        if save_original:
            attachments.append(('original_email.eml', message.as_string()))
        if not message.is_multipart() or 'text/' in message.get('content-type', ''):
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools.ustr(body, encoding, errors='replace')
        else:
            alternative = (message.get_content_type() == 'multipart/alternative')
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue # skip container
                filename = part.get_filename() # None if normal part
                encoding = part.get_content_charset() # None if attachment
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition','').strip().startswith('attachment'):
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    insertion_point = body.find('</html>')
                    # plain text is wrapped in <pre/> to preserve formatting
                    text = u'<pre>%s</pre>' % tools.ustr(part.get_payload(decode=True),
                                                         encoding, errors='replace')
                    if insertion_point != -1:
                        body = body[:insertion_point] + text + body[insertion_point:]
                    else:
                        body += text
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if alternative:
                        body = html
                        # force </html> tag to lowercase, for easier matching
                        body = re.sub(r'(?i)</html>', r'</html>', body)
                    else:
                        # strip enclosing html/body tags and append to existing body
                        html = re.sub(r'(?i)(</?html>|</?body>)', '', html)
                        insertion_point = body.find('</html>')
                        if insertion_point != -1:
                            body = body[:insertion_point] + html + body[insertion_point:]
                        else:
                            body += html
                # 4) Anything else -> attachment
                else:
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
        return body, attachments

    def message_parse(self, cr, uid, message, save_original=False, context=None):
        """Parses a string or email.message.Message representing an
           RFC-2822 email, and returns a generic dict holding the
           message details.

           :param message: the message to parse
           :type message: email.message.Message | string | unicode
           :param bool save_original: whether the returned dict
               should include an ``original`` attachment containing
               the source of the message
           :rtype: dict
           :return: A dict with the following structure, where each
                    field may not be present if missing in original
                    message::

                    { 'message-id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'body': unified_body,
                      'attachments': [('file1', 'bytes'),
                                      ('file2', 'bytes')}
                    }
        """
        msg_dict = {}
        if not isinstance(message, Message):
            if isinstance(message, unicode):
                # Warning: message_from_string doesn't always work correctly on unicode,
                # we must use utf-8 strings here :-(
                message = message.encode('utf-8')
            message = email.message_from_string(message)

        message_id = message['message-id']
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id

        if 'Subject' in message:
            msg_dict['subject'] = decode(message.get('Subject'))

        # Envelope fields not stored in  mail.message but made available for message_new() 
        msg_dict['from'] = decode(message.get('from'))
        msg_dict['to'] = decode(message.get('to'))
        msg_dict['cc'] = decode(message.get('cc'))

        if 'From' in message:
            author_ids = self._message_find_partners(cr, uid, message, ['From'], context=context)
            if author_ids:
                msg_dict['author_id'] = author_ids[0]
        partner_ids = self._message_find_partners(cr, uid, message, ['From','To','Cc'], context=context)
        msg_dict['partner_ids'] = partner_ids

        if 'Date' in message:
            date_hdr = decode(message.get('Date'))
            # convert from email timezone to server timezone
            date_server_datetime = dateutil.parser.parse(date_hdr).astimezone(pytz.timezone(tools.get_server_timezone()))
            date_server_datetime_str = date_server_datetime.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            msg_dict['date'] = date_server_datetime_str

        if 'In-Reply-To' in message:
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id','=',decode(message['In-Reply-To']))])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]

        if 'References' in message and 'parent_id' not in msg_dict:
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id','in',
                                                                         [x.strip() for x in decode(message['References']).split()])])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]
        
        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message)
        return msg_dict

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    def log(self, cr, uid, id, message, secondary=False, context=None):
        _logger.warning("log() is deprecated. As this module inherit from \
                        mail.thread, the message will be managed by this \
                        module instead of by the res.log mechanism. Please \
                        use the mail.thread OpenChatter API instead of the \
                        now deprecated res.log.")
        self.message_post(cr, uid, [id], message, context=context)

    def message_post(self, cr, uid, thread_id, body='', subject=False,
            msg_type='notification', parent_id=False, attachments=None, context=None, **kwargs):
        """ Post a new message in an existing message thread, returning the new
            mail.message ID. Extra keyword arguments will be used as default
            column values for the new mail.message record.
            :param int thread_id: thread ID to post into, or list with one ID
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str subject: optional subject
            :param str msg_type: mail_message.type
            :param int parent_id: optional ID of parent message in this thread
            :param tuple(str,str) attachments: list of attachment tuples in the form
                ``(name,content)``, where content is NOT base64 encoded
            :return: ID of newly created mail.message 
        """
        context = context or {}
        attachments = attachments or []
        assert (not thread_id) or isinstance(thread_id, (int,long)) or \
            (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), "Invalid thread_id" 
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id and thread_id[0]

        attachment_ids = []
        for name, content in attachments:
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            data_attach = {
                'name': name,
                'datas': base64.b64encode(str(content)),
                'datas_fname': name,
                'description': name,
                'res_model': context.get('thread_model') or self._name,
                'res_id': thread_id,
            }
            attachment_ids.append((0,0, data_attach))

        values = kwargs
        subtype_obj = self.pool.get('mail.message.subtype')
        if subtype:
            subtypes = subtype_obj.name_search(cr, uid, subtype)
            if len(subtypes):
                subtype_browse = subtype_obj.browse(cr, uid, subtypes[0][0])
                if self._name in [model.model for model in subtype_browse.model_ids]:
                    values['subtype_id']=subtype_browse.id
        values.update( {
            'model': thread_id and context.get('thread_model', self._name) or False,
            'res_id': thread_id or False,
            'body': body,
            'subject': subject,
            'type': msg_type,
            'parent_id': parent_id,
            'attachment_ids': attachment_ids,
        })
        for x in ('from','to','cc'): values.pop(x, None) # Avoid warnings 
        return self.pool.get('mail.message').create(cr, uid, values, context=context)

    #------------------------------------------------------
    # Followers API
    #------------------------------------------------------

    def message_subscribe_users(self, cr, uid, ids, user_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, subscribe uid instead. """
        # isinstance: because using message_subscribe_users called in a view set the context as user_ids
        if not user_ids or isinstance(user_ids, dict): user_ids = [uid]
        partner_ids = [user.partner_id.id for user in self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        return self.message_subscribe(cr, uid, ids, partner_ids, context=context)

    def message_subscribe(self, cr, uid, ids, partner_ids,subtype_ids = None, context=None):
        """ Add partners to the records followers.

            :param partner_ids: a list of partner_ids to subscribe
            :param return: new value of followers, for Chatter
        """
        self.write(cr, uid, ids, {'message_follower_ids': [(4, pid) for pid in partner_ids]}, context=context)
        if not subtype_ids:
            subtype_obj = self.pool.get('mail.message.subtype')
            subtype_ids = subtype_obj.search(cr, uid, [('default', '=', 'true'),('model_ids.model', '=', self._name)])
        if subtype_ids:
            self.message_subscribe_udpate_subtypes(cr, uid, ids, partner_ids, subtype_ids, context=context)

        # TDE: temp, must check followers widget
        return []
        # return [follower.id for thread in self.browse(cr, uid, ids, context=context) for follower in thread.message_follower_ids]

    def message_unsubscribe_users(self, cr, uid, ids, user_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, unsubscribe uid instead. """
        # isinstance: because using message_subscribe_users called in a view set the context as user_ids
        if not user_ids or isinstance(user_ids, dict): user_ids = [uid]
        partner_ids = [user.partner_id.id for user in self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        return self.message_unsubscribe(cr, uid, ids, partner_ids, context=context)

    def message_unsubscribe(self, cr, uid, ids, partner_ids, context=None):
        """ Remove partners from the records followers.

            :param partner_ids: a list of partner_ids to unsubscribe
            :param return: new value of followers, for Chatter
        """
        self.write(cr, uid, ids, {'message_follower_ids': [(3, pid) for pid in partner_ids]}, context=context)
        # TDE: temp, must check followers widget
        return []
        # return [follower.id for thread in self.browse(cr, uid, ids, context=context) for follower in thread.message_follower_ids]

    #------------------------------------------------------
    # Thread state
    #------------------------------------------------------

    def message_mark_as_unread(self, cr, uid, ids, context=None):
        """ Set as unread. """
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

    def message_subscribe_udpate_subtypes(self, cr, uid, ids, user_id, subtype_ids,context=None):
        subscription_obj = self.pool.get('mail.followers')
        subscription_ids = subscription_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids)])
        return subscription_obj.write(cr, uid, subscription_ids, {'subtype_ids': [(6, 0 , subtype_ids)]}, context = context) #overright or add new one
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
