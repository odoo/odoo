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
from mail_message import decode, to_email
import tools
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
            - mail_followers.res_model = 'crm.lead'
        """
        query = 'SELECT %(rel)s.%(id2)s, %(rel)s.%(id1)s \
                    FROM %(rel)s, %(from_c)s \
                    WHERE %(rel)s.%(id1)s IN %%s \
                    AND %(rel)s.%(id2)s = %(tbl)s.id \
                    AND %(rel)s.res_model = %%s \
                    %(where_c)s  \
                    %(order_by)s \
                    %(limit)s \
                    OFFSET %(offset)d' \
                % values
        where_params = [model._name] + where_params
        return query, where_params

    def set(self, cr, model, id, name, values, user=None, context=None):
        """ Override to add the res_model field in queries. """
        if not values: return
        rel, id1, id2 = self._sql_names(model)
        obj = model.pool.get(self._obj)
        for act in values:
            if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
                continue
            if act[0] == 0:
                idnew = obj.create(cr, user, act[2], context=context)
                cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+',res_model) VALUES (%s,%s,%s)', (id, idnew, model._name))
            elif act[0] == 3:
                cr.execute('DELETE FROM '+rel+' WHERE '+id1+'=%s AND '+id2+'=%s AND res_model=%s', (id, act[1], model._name))
            elif act[0] == 4:
                # following queries are in the same transaction - so should be relatively safe
                cr.execute('SELECT 1 FROM '+rel+' WHERE '+id1+'=%s AND '+id2+'=%s AND res_model=%s', (id, act[1], model._name))
                if not cr.fetchone():
                    cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+',res_model) VALUES (%s,%s,%s)', (id, act[1], model._name))
            elif act[0] == 6:
                d1, d2,tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
                if d1:
                    d1 = ' and ' + ' and '.join(d1)
                else:
                    d1 = ''
                cr.execute('DELETE FROM '+rel+' WHERE '+id1+'=%s AND res_model=%s AND '+id2+' IN (SELECT '+rel+'.'+id2+' FROM '+rel+', '+','.join(tables)+' WHERE '+rel+'.'+id1+'=%s AND '+rel+'.'+id2+' = '+obj._table+'.id '+ d1 +')', [id, model._name, id]+d2)
                for act_nbr in act[2]:
                    cr.execute('INSERT INTO '+rel+' ('+id1+','+id2+',res_model) VALUES (%s,%s,%s)', (id, act_nbr, model._name))
            else:
                return super(many2many_reference, self).set(cr, model, id, name, values, user, context)

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

    def _get_message_data(self, cr, uid, ids, field_names, args, context=None):
        res = dict.fromkeys(ids)
        for id in ids:
            res[id] = {'message_ids': self.message_search(cr, uid, [id], context=context)}
        for thread in self.browse(cr, uid, ids, context=context):
            message_follower_ids = [follower.id for follower in thread.message_follower_ids]
            res[thread.id].update({
                'message_is_follower': uid in message_follower_ids,
                'message_summary': "<span><span class='oe_e'>9</span> %d</span> <span><span class='oe_e'>+</span> %d</span>" % 
                    (len(res[thread.id]['message_ids']), len(thread.message_follower_ids))
                })
        return res

    def _search_message_ids(self, cr, uid, obj, name, args, context=None):
        msg_obj = self.pool.get('mail.message')
        msg_ids = msg_obj.search(cr, uid, ['&', ('res_id', 'in', args[0][2]), ('model', '=', self._name)], context=context)
        return [('id', 'in', msg_ids)]

    _columns = {
        'message_ids': fields.function(_get_message_data,
			fnct_search=_search_message_ids,
            type='one2many', obj='mail.message', _fields_id = 'res_id',
            string='Messages', multi="_get_message_data",
            help="Field holding discussion about the current document."),
        'message_follower_ids': many2many_reference('res.users',
            rel='mail_followers', id1='res_id', id2='user_id', string="Followers",
            help="Followers of the document. The followers have full access to " \
                 "the document details, as well as the conversation."),
        'message_is_follower': fields.function(_get_message_data, method=True,
            type='boolean', string='I am Follower', multi='_get_message_data',
            help='True if the current user is following the current document.'),
        'message_state': fields.boolean('Read',
            help="When checked, new messages require your attention."),
        'message_summary': fields.function(_get_message_data, method=True,
            type='text', string='Summary', multi='_get_message_data',
            help="Holds the Chatter summary (number of messages, ...). "\
                 "This summary is directly in html format in order to "\
                 "be inserted in kanban views."),
    }

    _defaults = {
        'message_state': True,
    }

    #------------------------------------------------------
    # Automatic subscription when creating/reading
    #------------------------------------------------------

    def create(self, cr, uid, vals, context=None):
        """ Override of create to subscribe :
            - the writer
            - followers given by the monitored fields
        """
        thread_id = super(mail_thread, self).create(cr, uid, vals, context=context)
        followers_command = self.message_get_automatic_followers(cr, uid, thread_id, vals, fetch_missing=False, context=context)
        if followers_command:
            self.write(cr, uid, [thread_id], {'message_follower_ids': followers_command}, context=context)
        return thread_id

    def write(self, cr, uid, ids, vals, context=None):
        """ Override of write to subscribe :
            - the writer
            - followers given by the monitored fields
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for id in ids:
            # copy original vals because we are going to modify it
            specific_vals = dict(vals)
            # we modify followers: do not subscribe the uid
            if specific_vals.get('message_follower_ids'):
                followers_command = self.message_get_automatic_followers(cr, uid, id, specific_vals, add_uid=False, context=context)
                specific_vals['message_follower_ids'] += followers_command
            else:
                followers_command = self.message_get_automatic_followers(cr, uid, id, specific_vals, context=context)
                specific_vals['message_follower_ids'] = followers_command
            write_res = super(mail_thread, self).write(cr, uid, ids, specific_vals, context=context)
        return True

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

    def message_get_automatic_followers(self, cr, uid, id, record_vals, add_uid=True, fetch_missing=False, context=None):
        """ Return the command for the many2many follower_ids field to manage
            subscribers. Behavior :
            - get the monitored fields (ex: ['user_id', 'responsible_id']); those
              fields should be relationships to res.users (#TODO: res.partner)
            - if this field is in the record_vals: it means it has been modified
              thus add its value to the followers
            - if this fields is not in record_vals, but fetch_missing paramter
              is set to True: fetch the value in the record (use: at creation
              for default values, not present in record_vals)
            - if add_uid: add the current user (for example: writer is subscriber)
            - generate the command and return it
            This method has to be used on 1 id, because otherwise it would imply
            to track which user.id is used for which record.id.

            :param record_vals: values given to the create method of the new
                record, or values updated in a write.
            :param monitored_fields: a list of fields that are monitored. Those
                fields must be many2one fields to the res.users model.
            :param fetch_missing: is set to True, the method will read the
                record to find values that are not present in record_vals.

            #TODO : UPDATE WHEN MERGING TO PARTNERS
        """
        # get monitored fields
        monitored_fields = self.message_get_monitored_follower_fields(cr, uid, [id], context=context)
        modified_fields = [field for field in monitored_fields if field in record_vals.iterkeys()]
        other_fields = [field for field in monitored_fields if field not in record_vals.iterkeys()] if fetch_missing else []
        # for each monitored field: if in record_vals, it has been modified/added
        follower_ids = []
        for field in modified_fields:
            # do not add 'False'
            if record_vals.get(fields):
                follower_ids.append(record_vals.get(field))
        # for other fields: read in record if fetch_missing (otherwise list is void)
        for field in other_fields:
            record = self.browse(cr, uid, id, context=context)
            value = getattr(record, field)
            if value:
                follower_ids.append(value)
        # add uid if asked and not already present
        if add_uid and uid not in follower_ids:
            follower_ids.append(uid)
        return self.message_subscribe_get_command(cr, uid, follower_ids, context=context)

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    def message_create(self, cr, uid, thread_id, vals, context = None):
        """ OpenChatter: wrapper of mail.message create method
           - creates the mail.message
           - automatically subscribe the message writer
           - push the message to followers
        """
        if context is None:
            context = {}
        
        notification_obj = self.pool.get('mail.notification')
        followers_obj = self.pool.get('mail.followers')
        subtype_obj = self.pool.get('mail.message.subtype')
        subtype_name = vals.get('subtype')
        subtype = False
        body = vals.get('body_html', '') if vals.get('content_subtype') == 'html' else vals.get('body_text', '')
        if subtype_name:
            subtypes = subtype_obj.name_search(cr, uid, subtype_name)
            if len(subtypes):
                subtype = subtype_obj.browse(cr, uid, subtypes[0][0])
                if self._name in [model.model for model in subtype.model_ids]:
                    vals['subtype_id']=subtype.id
        # create message
        msg_id = self.pool.get('mail.message').create(cr, uid, vals, context=context)

        # automatically subscribe the writer of the message
        if vals.get('user_id'):
            record = self.browse(cr, uid, thread_id, context=context)
            follower_ids = [follower.id for follower in record.message_follower_ids]
            if vals.get('user_id') not in follower_ids:
                self.message_subscribe(cr, uid, [thread_id], [vals.get('user_id')], context=context)

        # Set as unread if writer is not the document responsible
        self.message_create_set_unread(cr, uid, [thread_id], context = context)
        
        # special: if install mode, do not push demo data
        if context.get('install_mode', False):
            return msg_id
        
        # get users that will get a notification pushed
        subtype_id = subtype and subtype.id or False
        user_to_push_ids = self.message_get_user_ids_to_notify(cr, uid, [thread_id], vals, subtype_id, context = context)
        
        for user_id in user_to_push_ids:
            notification_obj.create(cr, uid, {'user_id': user_id, 'message_id': msg_id}, context = context)
        
        # create the email to send
        self.message_create_notify_by_email(cr, uid, vals, user_to_push_ids, context=context)
        
        return msg_id
    
    def message_get_user_ids_to_notify(self, cr, uid, thread_ids, new_msg_vals, subtype_id=None, context=None):
        # get body
        body = new_msg_vals.get('body_html', '') if new_msg_vals.get('content_subtype') == 'html' else new_msg_vals.get('body_text', '')
        
        # get subscribers
        subscr_obj = self.pool.get('mail.followers')
        subscr_ids = subscr_obj.search(cr, uid, ['&', ('res_model', '=', self._name), ('res_id', 'in', thread_ids)], context=context)
        notif_user_ids = []
        # check with subtype
        is_subtype = False
        for subscription in subscr_obj.browse(cr, uid, subscr_ids, context=context):
            if subtype_id:
                if subtype_id in [subtype.id for subtype in subscription.subtype_ids]:
                    is_subtype = True
                    notif_user_ids.append(subscription.user_id.id)
            else:
                notif_user_ids.append(subscription.user_id.id)
    
        # add users requested to perform an action (need_action mechanism)
        if hasattr(self, 'get_needaction_user_ids') and self._columns.get('user_id'):
            user_ids_dict = self.get_needaction_user_ids(cr, uid, thread_ids, context=context)
            for id, user_ids in user_ids_dict.iteritems():
                if is_subtype:
                    notif_user_ids += user_ids
        
        # add users notified of the parent messages (because: if parent message contains @login, login must receive the replies)
        if new_msg_vals.get('parent_id'):
            notif_obj = self.pool.get('mail.notification')
            parent_notif_ids = notif_obj.search(cr, uid, [('message_id', '=', new_msg_vals.get('parent_id'))], context=context)
            parent_notifs = notif_obj.read(cr, uid, parent_notif_ids, context=context)
            notif_user_ids += [parent_notif['user_id'][0] for parent_notif in parent_notifs]

        # remove duplicate entries
        notif_user_ids = list(set(notif_user_ids))
        return notif_user_ids

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

    def message_append(self, cr, uid, threads, subject, body_text=None, body_html=None,
                        type = 'email', email_date = None, parent_id = False,
                        content_subtype='plain', state=None,
                        partner_ids=None, email_from=False, email_to=False,
                        email_cc=None, email_bcc=None, reply_to=None,
                        headers=None, message_id=False, references=None,
                        attachments=None, original=None, subtype = "other", context=None):
        """ Creates a new mail.message through message_create. The new message
            is attached to the current mail.thread, containing all the details 
            passed as parameters. All attachments will be attached to the 
            thread record as well as to the actual message.
           
            This method calls message_create that will handle management of
            subscription and notifications, and effectively create the message.
           
            If ``email_from`` is not set or ``type`` not set as 'email',
            a note message is created (comment or system notification), 
            without the usual envelope attributes (sender, recipients, etc.).

            :param threads: list of thread ids, or list of browse_records
                representing threads to which a new message should be attached
            :param subject: subject of the message, or description of the event;
                this is totally optional as subjects are not important except
                for specific messages (blog post, job offers) or for emails
            :param body_text: plaintext contents of the mail or log message
            :param body_html: html contents of the mail or log message
            :param type: type of message: 'email', 'comment', 'notification';
                email by default
            :param email_date: email date string if different from now, in
                server timezone
            :param parent_id: id of the parent message (threaded messaging model)
            :param content_subtype: optional content_subtype of message: 'plain'
                or 'html', corresponding to the main body contents (body_text or
                body_html).
            :param state: state of message
            :param partner_ids: destination partners of the message, in addition
                to the now fully optional email_to; this method is supposed to
                received a list of ids is not None. The specific many2many
                instruction will be generated by this method.
            :param email_from: Email From / Sender address if any
            :param email_to: Email-To / Recipient address
            :param email_cc: Comma-Separated list of Carbon Copy Emails To
                addresses if any
            :param email_bcc: Comma-Separated list of Blind Carbon Copy Emails To
                addresses if any
            :param reply_to: reply_to header
            :param headers: mail headers to store
            :param message_id: optional email identifier
            :param references: optional email references
            :param dict attachments: map of attachment filenames to binary
                contents, if any.
            :param str original: optional full source of the RFC2822 email, for
                reference
            :param dict context: if a ``thread_model`` value is present in the
                context, its value will be used to determine the model of the
                thread to update (instead of the current model).
            :param subtype: subtype of message: 'email', 'comment', 'notification';
                other by default
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

        new_msg_ids = []
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
            # find related partner: partner_id column in thread object, or self is res.partner model
            partner_id = ('partner_id' in thread._columns.keys()) and (thread.partner_id and thread.partner_id.id or False) or False
            if not partner_id and thread._name == 'res.partner':
                partner_id = thread.id
            # destination partners
            if partner_ids is None:
                partner_ids = []
            mail_partner_ids = [(6, 0, partner_ids)]
            if type in ['email', 'comment']:
                subtype = type
            data = {
                'subject': subject,
                'subtype': subtype,
                'body_text': body_text or thread._model._columns.get('description') and thread.description or '',
                'body_html': body_html or '',
                'parent_id': parent_id,
                'date': email_date or fields.datetime.now(),
                'type': type,
                'content_subtype': content_subtype,
                'state': state,
                'message_id': message_id,
                'partner_ids': mail_partner_ids,
                'attachment_ids': [(6, 0, to_attach)],
                'user_id': uid,
                'model' : thread._name,
                'res_id': thread.id,
                'partner_id': partner_id,
            }

            if email_from or type == 'email':
                for param in (email_to, email_cc, email_bcc):
                    if isinstance(param, list):
                        param = ", ".join(param)
                data.update({
                    'email_to': email_to,
                    'email_from': email_from or \
                        thread._model._columns.get('user_id') and thread.user_id and thread.user_id.user_email,
                    'email_cc': email_cc,
                    'email_bcc': email_bcc,
                    'references': references,
                    'headers': headers,
                    'reply_to': reply_to,
                    'original': original,
                })

            new_msg_ids.append(self.message_create(cr, uid, thread.id, data, context=context))
        return new_msg_ids

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
        return self.message_append(cr, uid, ids,
                            subject = msg_dict.get('subject'),
                            body_text = msg_dict.get('body_text'),
                            body_html= msg_dict.get('body_html'),
                            parent_id = msg_dict.get('parent_id', False),
                            type = msg_dict.get('type', 'email'),
                            content_subtype = msg_dict.get('content_subtype'),
                            state = msg_dict.get('state'),
                            partner_ids = msg_dict.get('partner_ids'),
                            email_from = msg_dict.get('from', msg_dict.get('email_from')),
                            email_to = msg_dict.get('to', msg_dict.get('email_to')),
                            email_cc = msg_dict.get('cc', msg_dict.get('email_cc')),
                            email_bcc = msg_dict.get('bcc', msg_dict.get('email_bcc')),
                            reply_to = msg_dict.get('reply', msg_dict.get('reply_to')),
                            email_date = msg_dict.get('date'),
                            message_id = msg_dict.get('message-id', msg_dict.get('message_id')),
                            references = msg_dict.get('references')\
                                      or msg_dict.get('in-reply-to'),
                            attachments = msg_dict.get('attachments'),
                            headers = msg_dict.get('headers'),
                            original = msg_dict.get('original'),
                            subtype = msg_dict.get('subtype','other'),
                            context = context)

    #------------------------------------------------------
    # Message loading
    #------------------------------------------------------

    def _message_search_ancestor_ids(self, cr, uid, ids, child_ids, ancestor_ids, context=None):
        """ Given message child_ids ids, find their ancestors until ancestor_ids
            using their parent_id relationship.

            :param child_ids: the first nodes of the search
            :param ancestor_ids: list of ancestors. When the search reach an
                                 ancestor, it stops.
        """
        def _get_parent_ids(message_list, ancestor_ids, child_ids):
            """ Tool function: return the list of parent_ids of messages
                contained in message_list. Parents that are in ancestor_ids
                or in child_ids are not returned. """
            return [message['parent_id'][0] for message in message_list
                        if message['parent_id']
                        and message['parent_id'][0] not in ancestor_ids
                        and message['parent_id'][0] not in child_ids
                    ]

        message_obj = self.pool.get('mail.message')
        messages_temp = message_obj.read(cr, uid, child_ids, ['id', 'parent_id'], context=context)
        parent_ids = _get_parent_ids(messages_temp, ancestor_ids, child_ids)
        child_ids += parent_ids
        cur_iter = 0; max_iter = 100; # avoid infinite loop
        while (parent_ids and (cur_iter < max_iter)):
            cur_iter += 1
            messages_temp = message_obj.read(cr, uid, parent_ids, ['id', 'parent_id'], context=context)
            parent_ids = _get_parent_ids(messages_temp, ancestor_ids, child_ids)
            child_ids += parent_ids
        if (cur_iter > max_iter):
            _logger.warning("Possible infinite loop in _message_search_ancestor_ids. "\
                "Note that this algorithm is intended to check for cycle in "\
                "message graph, leading to a curious error. Have fun.")
        return child_ids

    def message_search_get_domain(self, cr, uid, ids, context=None):
        """ OpenChatter feature: get the domain to search the messages related
            to a document. mail.thread defines the default behavior as
            being messages with model = self._name, id in ids.
            This method should be overridden if a model has to implement a
            particular behavior.
        """
        return ['&', ('res_id', 'in', ids), ('model', '=', self._name)]

    def message_search(self, cr, uid, ids, fetch_ancestors=False, ancestor_ids=None, 
                        limit=100, offset=0, domain=None, count=False, context=None):
        """ OpenChatter feature: return thread messages ids according to the
            search domain given by ``message_search_get_domain``.
            
            It is possible to add in the search the parent of messages by
            setting the fetch_ancestors flag to True. In that case, using
            the parent_id relationship, the method returns the id list according
            to the search domain, but then calls ``_message_search_ancestor_ids``
            that will add to the list the ancestors ids. The search is limited
            to parent messages having an id in ancestor_ids or having
            parent_id set to False.
            
            If ``count==True``, the number of ids is returned instead of the
            id list. The count is done by hand instead of passing it as an 
            argument to the search call because we might want to perform
            a research including parent messages until some ancestor_ids.
            
            :param fetch_ancestors: performs an ascended search; will add 
                                    to fetched msgs all their parents until
                                    ancestor_ids
            :param ancestor_ids: used when fetching ancestors
            :param domain: domain to add to the search; especially child_of
                           is interesting when dealing with threaded display.
                           Note that the added domain is anded with the 
                           default domain.
            :param limit, offset, count, context: as usual
        """
        search_domain = self.message_search_get_domain(cr, uid, ids, context=context)
        if domain:
            search_domain += domain
        message_obj = self.pool.get('mail.message')
        message_res = message_obj.search(cr, uid, search_domain, limit=limit, offset=offset, count=count, context=context)
        if not count and fetch_ancestors:
            message_res += self._message_search_ancestor_ids(cr, uid, ids, message_res, ancestor_ids, context=context) 
        return message_res

    def message_read(self, cr, uid, ids, fetch_ancestors=False, ancestor_ids=None, 
                        limit=100, offset=0, domain=None, context=None):
        """ OpenChatter feature: read the messages related to some threads.
            This method is used mainly the Chatter widget, to directly have
            read result instead of searching then reading.

            Please see message_search for more information about the parameters.
        """
        message_ids = self.message_search(cr, uid, ids, fetch_ancestors, ancestor_ids,
            limit, offset, domain, context=context)
        messages = self.pool.get('mail.message').read(cr, uid, message_ids, context=context)

        """ Retrieve all attachments names """
        map_id_to_name = dict((attachment_id, '') for message in messages for attachment_id in message['attachment_ids'])

        ids = map_id_to_name.keys()
        names = self.pool.get('ir.attachment').name_get(cr, uid, ids, context=context)
        
        # convert the list of tuples into a dictionnary
        for name in names: 
            map_id_to_name[name[0]] = name[1]
        
        # give corresponding ids and names to each message
        for msg in messages:
            msg["attachments"] = []
            
            for attach_id in msg["attachment_ids"]:
                msg["attachments"].append({'id': attach_id, 'name': map_id_to_name[attach_id]})
        
        # Set the threads as read
        self.message_check_and_set_read(cr, uid, ids, context=context)
        # Sort and return the messages
        messages = sorted(messages, key=lambda d: (-d['id']))
        return messages

    def message_get_pushed_messages(self, cr, uid, ids, fetch_ancestors=False, ancestor_ids=None,
                            limit=100, offset=0, msg_search_domain=[], context=None):
        """ OpenChatter: wall: get the pushed notifications and used them
            to fetch messages to display on the wall.
            
            :param fetch_ancestors: performs an ascended search; will add
                                    to fetched msgs all their parents until
                                    ancestor_ids
            :param ancestor_ids: used when fetching ancestors
            :param domain: domain to add to the search; especially child_of
                           is interesting when dealing with threaded display
            :param ascent: performs an ascended search; will add to fetched msgs
                           all their parents until root_ids
            :param root_ids: for ascent search
            :return: list of mail.messages sorted by date
        """
        notification_obj = self.pool.get('mail.notification')
        msg_obj = self.pool.get('mail.message')
        # update message search
        for arg in msg_search_domain:
            if isinstance(arg, (tuple, list)):
                arg[0] = 'message_id.' + arg[0]
        # compose final domain
        domain = [('user_id', '=', uid)] + msg_search_domain
        # get notifications
        notification_ids = notification_obj.search(cr, uid, domain, limit=limit, offset=offset, context=context)
        notifications = notification_obj.browse(cr, uid, notification_ids, context=context)
        msg_ids = [notification.message_id.id for notification in notifications]
        # get messages
        msg_ids = msg_obj.search(cr, uid, [('id', 'in', msg_ids)], context=context)
        if (fetch_ancestors): msg_ids = self._message_search_ancestor_ids(cr, uid, ids, msg_ids, ancestor_ids, context=context)
        msgs = msg_obj.read(cr, uid, msg_ids, context=context)
        return msgs

    def _message_find_user_id(self, cr, uid, message, context=None):
        from_local_part = to_email(decode(message.get('From')))[0]
        user_ids = self.pool.get('res.users').search(cr, uid, [('login', '=', from_local_part)], context=context)
        return user_ids[0] if user_ids else uid

    #------------------------------------------------------
    # Mail gateway
    #------------------------------------------------------
    # message_process will call either message_new or message_update.

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
        local_parts = [e.split('@')[0] for e in to_email(rcpt_tos)]
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
            or its ``message_update`` method (if it did). Finally,
           ``message_forward`` is called to automatically notify other
           people that should receive this message.

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
    
            # Forward the email to other followers
            self.message_forward(cr, uid, model, [thread_id], msg_txt, context=context)
            model_pool.message_mark_as_unread(cr, uid, [thread_id], context=context)
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
        self.message_append_dict(cr, uid, [res_id], msg_dict, context=context)
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
        return self.message_append_dict(cr, uid, ids, msg_dict, context=context)

    def message_thread_followers(self, cr, uid, ids, context=None):
        """ Returns a list of email addresses of the people following
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
                if model_pool._columns.get('section_id'):
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
        partner_pool = self.pool.get('res.partner')
        res = {'partner_id': False}
        if email:
            email = to_email(email)[0]
            contact_ids = partner_pool.search(cr, uid, [('email', '=', email)])
            if contact_ids:
                contact = partner_pool.browse(cr, uid, contact_ids[0])
                res['partner_id'] = contact.id
        return res

    # for backwards-compatibility with old scripts
    process_email = message_process

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    def log(self, cr, uid, id, message, secondary=False, context=None):
        _logger.warning("log() is deprecated. As this module inherit from \
                        mail.thread, the message will be managed by this \
                        module instead of by the res.log mechanism. Please \
                        use the mail.thread OpenChatter API instead of the \
                        now deprecated res.log.")
        self.message_append_note(cr, uid, [id], 'res.log', message, context=context)

    def message_append_note(self, cr, uid, ids, subject=None, body=None, parent_id=False,
                            type='notification', content_subtype='html', subtype='other', context=None):
        if content_subtype == 'html':
            body_html = body
            body_text = body
        else:
            body_html = body
            body_text = body
        return self.message_append(cr, uid, ids, subject, body_text, body_html,
                                    type, parent_id = parent_id,
                                    content_subtype=content_subtype, subtype=subtype, context=context)

    #------------------------------------------------------
    # Subscription mechanism
    #------------------------------------------------------

    def message_get_monitored_follower_fields(self, cr, uid, ids, context=None):
        """ Returns a list of fields containing a res.user.id. Those fields
            will be checked to automatically subscribe those users.
        """
        return []

    def message_subscribe(self, cr, uid, ids, user_ids = None, subtype_ids = None, context = None):
        """ Subscribe the user (or user_ids) to the current document.
            
            :param user_ids: a list of user_ids; if not set, subscribe
                             uid instead
            :param return: new value of followers, for Chatter
        """
        to_subscribe_uids = [uid] if user_ids is None else user_ids
        write_res = self.write(cr, uid, ids, {'message_follower_ids': self.message_subscribe_get_command(cr, uid, to_subscribe_uids, context)}, context=context)
        follower_ids = [follower.id for thread in self.browse(cr, uid, ids, context=context) for follower in thread.message_follower_ids]
        if not subtype_ids:
            subtype_obj = self.pool.get('mail.message.subtype')
            subtype_ids = subtype_obj.search(cr, uid, [('default', '=', 'true'),('model_ids.model', '=', self._name)])
        if subtype_ids:
            self.message_subscribe_udpate_subtypes(cr, uid, ids, to_subscribe_uids, subtype_ids, context=context)
        return follower_ids

    def message_subscribe_get_command(self, cr, uid, follower_ids, context=None):
        """ Generate the many2many command to add followers. """
        return [(4, id) for id in follower_ids]

    def message_unsubscribe(self, cr, uid, ids, user_ids = None, context=None):
        """ Unsubscribe the user (or user_ids) from the current document.
            
            :param user_ids: a list of user_ids; if not set, subscribe
                             uid instead
            :param return: new value of followers, for Chatter
        """
        to_unsubscribe_uids = [uid] if user_ids is None else user_ids
        write_res = self.write(cr, uid, ids, {'message_follower_ids': self.message_unsubscribe_get_command(cr, uid, to_unsubscribe_uids, context)}, context=context)
        return [follower.id for thread in self.browse(cr, uid, ids, context=context) for follower in thread.message_follower_ids]

    def message_unsubscribe_get_command(self, cr, uid, follower_ids, context=None):
        """ Generate the many2many command to remove followers. """
        return [(3, id) for id in follower_ids]

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    def message_create_notify_by_email(self, cr, uid, new_msg_values, user_to_notify_ids, context=None):
        """ When creating a new message and pushing notifications, emails
            must be send if users have chosen to receive notifications
            by email via the notification_email_pref field.
            
            ``notification_email_pref`` can have 3 values :
            - all: receive all notification by email (for example for shared
              users)
            - to_me: messages send directly to me (@login, messages on res.users)
            - never: never receive notifications
            Note that an user should never receive notifications for messages
            he has created.
            
            :param new_msg_values: dictionary of message values, those that
                                   are given to the create method
            :param user_to_notify_ids: list of user_ids, user that will
                                       receive a notification on their Wall
        """
        message_obj = self.pool.get('mail.message')
        res_users_obj = self.pool.get('res.users')
        body = new_msg_values.get('body_html', '') if new_msg_values.get('content_subtype') == 'html' else new_msg_values.get('body_text', '')
        
        # remove message writer
        if user_to_notify_ids.count(new_msg_values.get('user_id')) > 0:
            user_to_notify_ids.remove(new_msg_values.get('user_id'))

        # try to find an email_to
        email_to = ''
        for user in res_users_obj.browse(cr, uid, user_to_notify_ids, context=context):
            # TO BE REFACTORED BY FP, JUSTE REMOVED TO_ME, NOT SURE WHAT S NEW BEHAVIOR
            if not user.notification_email_pref == 'all':
                continue
            if not user.email:
                continue
            email_to = '%s, %s' % (email_to, user.email)
            email_to = email_to.lstrip(', ')
        
        # did not find any email address: not necessary to create an email
        if not email_to:
            return
        
        # try to find an email_from
        current_user = res_users_obj.browse(cr, uid, [uid], context=context)[0]
        email_from = new_msg_values.get('email_from')
        if not email_from:
            email_from = current_user.email
        
        # get email content, create it (with mail_message.create)
        email_values = self.message_create_notify_get_email_dict(cr, uid, new_msg_values, email_from, email_to, context)
        email_id = message_obj.create(cr, uid, email_values, context=context)
        return email_id
    
    def message_create_notify_get_email_dict(self, cr, uid, new_msg_values, email_from, email_to, context=None):
        values = dict(new_msg_values)
        
        body_html = new_msg_values.get('body_html', '')
        if body_html:
            body_html += '\n\n----------\nThis email was send automatically by OpenERP, because you have subscribed to a document.'
        body_text = new_msg_values.get('body_text', '')
        if body_text:
            body_text += '\n\n----------\nThis email was send automatically by OpenERP, because you have subscribed to a document.'
        values.update({
            'type': 'email',
            'state': 'outgoing',
            'email_from': email_from,
            'email_to': email_to,
            'subject': 'New message',
            'content_subtype': new_msg_values.get('content_subtype', 'plain'),
            'body_html': body_html,
            'body_text': body_text,
            'auto_delete': True,
            'res_model': '',
            'res_id': False,
        })
        return values

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

    def message_create_set_unread(self, cr, uid, ids, context=None):
        """ When creating a new message, set as unread if uid is not the
            object responsible. """
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.message_state and ('user_id' in obj._columns.keys()) and (not obj.user_id or obj.user_id.id != uid) :
                self.message_mark_as_unread(cr, uid, [obj.id], context=context)

    def message_check_and_set_unread(self, cr, uid, ids, context=None):
        """ Set unread if uid is the object responsible or if the object has
            no responsible. """
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.message_state and self._columns.get('user_id') and (not obj.user_id or obj.user_id.id == uid):
                self.message_mark_as_unread(cr, uid, [obj.id], context=context)

    def message_mark_as_unread(self, cr, uid, ids, context=None):
        """ Set as unread. """
        return self.write(cr, uid, ids, {'message_state': False}, context=context)

    def message_check_and_set_read(self, cr, uid, ids, context=None):
        """ Set read if uid is the object responsible. """
        for obj in self.browse(cr, uid, ids, context=context):
            if not obj.message_state and self._columns.get('user_id') and obj.user_id and obj.user_id.id == uid:
                self.message_mark_as_read(cr, uid, [obj.id], context=context)

    def message_mark_as_read(self, cr, uid, ids, context=None):
        """ Set as read. """
        return self.write(cr, uid, ids, {'message_state': True}, context=context)

    def message_subscribe_udpate_subtypes(self, cr, uid, ids, user_id, subtype_ids,context=None):
        subscription_obj = self.pool.get('mail.followers')
        subscription_ids = subscription_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids),('user_id','in',user_id)])
        return subscription_obj.write(cr, uid, subscription_ids, {'subtype_ids': [(6, 0 , subtype_ids)]}, context = context) #overright or add new one
        
    def message_subscription_remove_subtype(self, cr, uid, ids, user_id, subtype_id):
        subscription_obj = self.pool.get('mail.followers')
        subscription_ids = subscription_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids)])
        return subscription_obj.write(cr, uid, subscription_ids, {'subtype_ids': [3, subtype_id]}, context = context) # remove link
        
    def message_subscription_remove_subtype_name(self, cr, uid, ids, user_id, subtype_name):
        subtype_obj = self.pool.get('mail.message.subtype')
        subtype_ids = subtype_obj.search(cr, uid, [('name', '=', subtype_name), ('model_ids', '=', self._name)])
        if not subtype_ids:
            return False
        self.message_subscription_remove_subtype(cr, uid, ids, user_id, subtype_ids)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
