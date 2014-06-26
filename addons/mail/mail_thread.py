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
from collections import OrderedDict
import datetime
import dateutil
import email
try:
    import simplejson as json
except ImportError:
    import json
from lxml import etree
import logging
import pytz
import re
import socket
import time
import xmlrpclib
import re
from email.message import Message
from urllib import urlencode

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.mail.mail_message import decode
from openerp.osv import fields, osv, orm
from openerp.osv.orm import browse_record, browse_null
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


mail_header_msgid_re = re.compile('<[^<>]+>')

def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class mail_thread(osv.AbstractModel):
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

        Options:
            - _mail_flat_thread: if set to True, all messages without parent_id
                are automatically attached to the first message posted on the
                ressource. If set to False, the display of Chatter is done using
                threads, and no parent_id is automatically set.
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'
    _mail_flat_thread = True
    _mail_post_access = 'write'

    # Automatic logging system if mail installed
    # _track = {
    #   'field': {
    #       'module.subtype_xml': lambda self, cr, uid, obj, context=None: obj[state] == done,
    #       'module.subtype_xml2': lambda self, cr, uid, obj, context=None: obj[state] != done,
    #   },
    #   'field2': {
    #       ...
    #   },
    # }
    # where
    #   :param string field: field name
    #   :param module.subtype_xml: xml_id of a mail.message.subtype (i.e. mail.mt_comment)
    #   :param obj: is a browse_record
    #   :param function lambda: returns whether the tracking should record using this subtype
    _track = {}

    # Mass mailing feature
    _mail_mass_mailing = False

    def get_empty_list_help(self, cr, uid, help, context=None):
        """ Override of BaseModel.get_empty_list_help() to generate an help message
            that adds alias information. """
        model = context.get('empty_list_help_model')
        res_id = context.get('empty_list_help_id')
        ir_config_parameter = self.pool.get("ir.config_parameter")
        catchall_domain = ir_config_parameter.get_param(cr, uid, "mail.catchall.domain", context=context)
        document_name = context.get('empty_list_help_document_name', _('document'))
        alias = None

        if catchall_domain and model and res_id:  # specific res_id -> find its alias (i.e. section_id specified)
            object_id = self.pool.get(model).browse(cr, uid, res_id, context=context)
            # check that the alias effectively creates new records
            if object_id.alias_id and object_id.alias_id.alias_name and \
                    object_id.alias_id.alias_model_id and \
                    object_id.alias_id.alias_model_id.model == self._name and \
                    object_id.alias_id.alias_force_thread_id == 0:
                alias = object_id.alias_id
        if not alias and catchall_domain and model:  # no res_id or res_id not linked to an alias -> generic help message, take a generic alias of the model
            alias_obj = self.pool.get('mail.alias')
            alias_ids = alias_obj.search(cr, uid, [("alias_parent_model_id.model", "=", model), ("alias_name", "!=", False), ('alias_force_thread_id', '=', False), ('alias_parent_thread_id', '=', False)], context=context, order='id ASC')
            if alias_ids and len(alias_ids) == 1:
                alias = alias_obj.browse(cr, uid, alias_ids[0], context=context)

        if alias:
            alias_email = alias.name_get()[0][1]
            return _("""<p class='oe_view_nocontent_create'>
                            Click here to add new %(document)s or send an email to: <a href='mailto:%(email)s'>%(email)s</a>
                        </p>
                        %(static_help)s"""
                    ) % {
                        'document': document_name,
                        'email': alias_email,
                        'static_help': help or ''
                    }

        if document_name != 'document' and help and help.find("oe_view_nocontent_create") == -1:
            return _("<p class='oe_view_nocontent_create'>Click here to add new %(document)s</p>%(static_help)s") % {
                        'document': document_name,
                        'static_help': help or '',
                    }

        return help

    def _get_message_data(self, cr, uid, ids, name, args, context=None):
        """ Computes:
            - message_unread: has uid unread message for the document
            - message_summary: html snippet summarizing the Chatter for kanban views """
        res = dict((id, dict(message_unread=False, message_unread_count=0, message_summary=' ')) for id in ids)
        user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]

        # search for unread messages, directly in SQL to improve performances
        cr.execute("""  SELECT m.res_id FROM mail_message m
                        RIGHT JOIN mail_notification n
                        ON (n.message_id = m.id AND n.partner_id = %s AND (n.read = False or n.read IS NULL))
                        WHERE m.model = %s AND m.res_id in %s""",
                    (user_pid, self._name, tuple(ids),))
        for result in cr.fetchall():
            res[result[0]]['message_unread'] = True
            res[result[0]]['message_unread_count'] += 1

        for id in ids:
            if res[id]['message_unread_count']:
                title = res[id]['message_unread_count'] > 1 and _("You have %d unread messages") % res[id]['message_unread_count'] or _("You have one unread message")
                res[id]['message_summary'] = "<span class='oe_kanban_mail_new' title='%s'><span class='oe_e'>9</span> %d %s</span>" % (title, res[id].pop('message_unread_count'), _("New"))
            res[id].pop('message_unread_count', None)
        return res

    def read_followers_data(self, cr, uid, follower_ids, context=None):
        result = []
        technical_group = self.pool.get('ir.model.data').get_object(cr, uid, 'base', 'group_no_one', context=context)
        for follower in self.pool.get('res.partner').browse(cr, uid, follower_ids, context=context):
            is_editable = uid in map(lambda x: x.id, technical_group.users)
            is_uid = uid in map(lambda x: x.id, follower.user_ids)
            data = (follower.id,
                    follower.name,
                    {'is_editable': is_editable, 'is_uid': is_uid},
                    )
            result.append(data)
        return result

    def _get_subscription_data(self, cr, uid, ids, name, args, user_pid=None, context=None):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        res = dict((id, dict(message_subtype_data='')) for id in ids)
        if user_pid is None:
            user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]

        # find current model subtypes, add them to a dictionary
        subtype_obj = self.pool.get('mail.message.subtype')
        subtype_ids = subtype_obj.search(
            cr, uid, [
                '&', ('hidden', '=', False), '|', ('res_model', '=', self._name), ('res_model', '=', False)
            ], context=context)
        subtype_dict = OrderedDict(
            (subtype.name, {
                'default': subtype.default,
                'followed': False,
                'parent_model': subtype.parent_id and subtype.parent_id.res_model or self._name,
                'id': subtype.id}
            ) for subtype in subtype_obj.browse(cr, uid, subtype_ids, context=context))
        for id in ids:
            res[id]['message_subtype_data'] = subtype_dict.copy()

        # find the document followers, update the data
        fol_obj = self.pool.get('mail.followers')
        fol_ids = fol_obj.search(cr, uid, [
            ('partner_id', '=', user_pid),
            ('res_id', 'in', ids),
            ('res_model', '=', self._name),
        ], context=context)
        for fol in fol_obj.browse(cr, uid, fol_ids, context=context):
            thread_subtype_dict = res[fol.res_id]['message_subtype_data']
            for subtype in [st for st in fol.subtype_ids if st.name in thread_subtype_dict]:
                thread_subtype_dict[subtype.name]['followed'] = True
            res[fol.res_id]['message_subtype_data'] = thread_subtype_dict

        return res

    def _search_message_unread(self, cr, uid, obj=None, name=None, domain=None, context=None):
        return [('message_ids.to_read', '=', True)]

    def _get_followers(self, cr, uid, ids, name, arg, context=None):
        fol_obj = self.pool.get('mail.followers')
        fol_ids = fol_obj.search(cr, SUPERUSER_ID, [('res_model', '=', self._name), ('res_id', 'in', ids)])
        res = dict((id, dict(message_follower_ids=[], message_is_follower=False)) for id in ids)
        user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        for fol in fol_obj.browse(cr, SUPERUSER_ID, fol_ids):
            res[fol.res_id]['message_follower_ids'].append(fol.partner_id.id)
            if fol.partner_id.id == user_pid:
                res[fol.res_id]['message_is_follower'] = True
        return res

    def _set_followers(self, cr, uid, id, name, value, arg, context=None):
        if not value:
            return
        partner_obj = self.pool.get('res.partner')
        fol_obj = self.pool.get('mail.followers')

        # read the old set of followers, and determine the new set of followers
        fol_ids = fol_obj.search(cr, SUPERUSER_ID, [('res_model', '=', self._name), ('res_id', '=', id)])
        old = set(fol.partner_id.id for fol in fol_obj.browse(cr, SUPERUSER_ID, fol_ids))
        new = set(old)

        for command in value or []:
            if isinstance(command, (int, long)):
                new.add(command)
            elif command[0] == 0:
                new.add(partner_obj.create(cr, uid, command[2], context=context))
            elif command[0] == 1:
                partner_obj.write(cr, uid, [command[1]], command[2], context=context)
                new.add(command[1])
            elif command[0] == 2:
                partner_obj.unlink(cr, uid, [command[1]], context=context)
                new.discard(command[1])
            elif command[0] == 3:
                new.discard(command[1])
            elif command[0] == 4:
                new.add(command[1])
            elif command[0] == 5:
                new.clear()
            elif command[0] == 6:
                new = set(command[2])

        # remove partners that are no longer followers
        self.message_unsubscribe(cr, uid, [id], list(old-new), context=context)
        # add new followers
        self.message_subscribe(cr, uid, [id], list(new-old), context=context)

    def _search_followers(self, cr, uid, obj, name, args, context):
        """Search function for message_follower_ids

        Do not use with operator 'not in'. Use instead message_is_followers
        """
        fol_obj = self.pool.get('mail.followers')
        res = []
        for field, operator, value in args:
            assert field == name
            # TOFIX make it work with not in
            assert operator != "not in", "Do not search message_follower_ids with 'not in'"
            fol_ids = fol_obj.search(cr, SUPERUSER_ID, [('res_model', '=', self._name), ('partner_id', operator, value)])
            res_ids = [fol.res_id for fol in fol_obj.browse(cr, SUPERUSER_ID, fol_ids)]
            res.append(('id', 'in', res_ids))
        return res

    def _search_is_follower(self, cr, uid, obj, name, args, context):
        """Search function for message_is_follower"""
        res = []
        for field, operator, value in args:
            assert field == name
            partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
            if (operator == '=' and value) or (operator == '!=' and not value):  # is a follower
                res_ids = self.search(cr, uid, [('message_follower_ids', 'in', [partner_id])], context=context)
            else:  # is not a follower or unknown domain
                mail_ids = self.search(cr, uid, [('message_follower_ids', 'in', [partner_id])], context=context)
                res_ids = self.search(cr, uid, [('id', 'not in', mail_ids)], context=context)
            res.append(('id', 'in', res_ids))
        return res

    _columns = {
        'message_is_follower': fields.function(_get_followers, type='boolean',
            fnct_search=_search_is_follower, string='Is a Follower', multi='_get_followers,'),
        'message_follower_ids': fields.function(_get_followers, fnct_inv=_set_followers,
            fnct_search=_search_followers, type='many2many', priority=-10,
            obj='res.partner', string='Followers', multi='_get_followers'),
        'message_ids': fields.one2many('mail.message', 'res_id',
            domain=lambda self: [('model', '=', self._name)],
            auto_join=True,
            string='Messages',
            help="Messages and communication history"),
        'message_last_post': fields.datetime('Last Message Date',
            help='Date of the last message posted on the record.'),
        'message_unread': fields.function(_get_message_data,
            fnct_search=_search_message_unread, multi="_get_message_data",
            type='boolean', string='Unread Messages',
            help="If checked new messages require your attention."),
        'message_summary': fields.function(_get_message_data, method=True,
            type='text', string='Summary', multi="_get_message_data",
            help="Holds the Chatter summary (number of messages, ...). "\
                 "This summary is directly in html format in order to "\
                 "be inserted in kanban views."),
    }

    def _get_user_chatter_options(self, cr, uid, context=None):
        options = {
            'display_log_button': False
        }
        group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
        group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_user')[1]
        is_employee = group_user_id in [group.id for group in group_ids]
        if is_employee:
            options['display_log_button'] = True
        return options

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(mail_thread, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']"):
                options = json.loads(node.get('options', '{}'))
                options.update(self._get_user_chatter_options(cr, uid, context=context))
                node.set('options', json.dumps(options))
            res['arch'] = etree.tostring(doc)
        return res

    #------------------------------------------------------
    # CRUD overrides for automatic subscription and logging
    #------------------------------------------------------

    def create(self, cr, uid, values, context=None):
        """ Chatter override :
            - subscribe uid
            - subscribe followers of parent
            - log a creation message
        """
        if context is None:
            context = {}

        if context.get('tracking_disable'):
            return super(mail_thread, self).create(
                cr, uid, values, context=context)

        # subscribe uid unless asked not to
        if not context.get('mail_create_nosubscribe'):
            pid = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid).partner_id.id
            message_follower_ids = values.get('message_follower_ids') or []  # webclient can send None or False
            message_follower_ids.append([4, pid])
            values['message_follower_ids'] = message_follower_ids
        thread_id = super(mail_thread, self).create(cr, uid, values, context=context)

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not context.get('mail_create_nolog'):
            self.message_post(cr, uid, thread_id, body=_('%s created') % (self._description), context=context)

        # auto_subscribe: take values and defaults into account
        create_values = dict(values)
        for key, val in context.iteritems():
            if key.startswith('default_'):
                create_values[key[8:]] = val
        self.message_auto_subscribe(cr, uid, [thread_id], create_values.keys(), context=context, values=create_values)

        # track values
        track_ctx = dict(context)
        if 'lang' not in track_ctx:
            track_ctx['lang'] = self.pool.get('res.users').browse(cr, uid, uid, context=context).lang
        if not context.get('mail_notrack'):
            tracked_fields = self._get_tracked_fields(cr, uid, values.keys(), context=track_ctx)
            if tracked_fields:
                initial_values = {thread_id: dict.fromkeys(tracked_fields, False)}
                self.message_track(cr, uid, [thread_id], tracked_fields, initial_values, context=track_ctx)
        return thread_id

    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context.get('tracking_disable'):
            return super(mail_thread, self).write(
                cr, uid, ids, values, context=context)
        # Track initial values of tracked fields
        track_ctx = dict(context)
        if 'lang' not in track_ctx:
            track_ctx['lang'] = self.pool.get('res.users').browse(cr, uid, uid, context=context).lang

        tracked_fields = None
        if not context.get('mail_notrack'):
            tracked_fields = self._get_tracked_fields(cr, uid, values.keys(), context=track_ctx)

        if tracked_fields:
            records = self.browse(cr, uid, ids, context=track_ctx)
            initial_values = dict((record.id, dict((key, getattr(record, key)) for key in tracked_fields))
                                  for record in records)

        # Perform write, update followers
        result = super(mail_thread, self).write(cr, uid, ids, values, context=context)
        self.message_auto_subscribe(cr, uid, ids, values.keys(), context=context, values=values)

        # Perform the tracking
        if tracked_fields:
            self.message_track(cr, uid, ids, tracked_fields, initial_values, context=track_ctx)

        return result

    def unlink(self, cr, uid, ids, context=None):
        """ Override unlink to delete messages and followers. This cannot be
            cascaded, because link is done through (res_model, res_id). """
        msg_obj = self.pool.get('mail.message')
        fol_obj = self.pool.get('mail.followers')
        # delete messages and notifications
        msg_ids = msg_obj.search(cr, uid, [('model', '=', self._name), ('res_id', 'in', ids)], context=context)
        msg_obj.unlink(cr, uid, msg_ids, context=context)
        # delete
        res = super(mail_thread, self).unlink(cr, uid, ids, context=context)
        # delete followers
        fol_ids = fol_obj.search(cr, SUPERUSER_ID, [('res_model', '=', self._name), ('res_id', 'in', ids)], context=context)
        fol_obj.unlink(cr, SUPERUSER_ID, fol_ids, context=context)
        return res

    def copy_data(self, cr, uid, id, default=None, context=None):
        # avoid tracking multiple temporary changes during copy
        context = dict(context or {}, mail_notrack=True)

        default = default or {}
        default['message_ids'] = []
        default['message_follower_ids'] = []
        return super(mail_thread, self).copy_data(cr, uid, id, default=default, context=context)

    #------------------------------------------------------
    # Automatically log tracked fields
    #------------------------------------------------------

    def _get_tracked_fields(self, cr, uid, updated_fields, context=None):
        """ Return a structure of tracked fields for the current model.
            :param list updated_fields: modified field names
            :return list: a list of (field_name, column_info obj), containing
                always tracked fields and modified on_change fields
        """
        tracked_fields = []
        for name, column_info in self._all_columns.items():
            visibility = getattr(column_info.column, 'track_visibility', False)
            if visibility == 'always' or (visibility == 'onchange' and name in updated_fields) or name in self._track:
                tracked_fields.append(name)

        if tracked_fields:
            return self.fields_get(cr, uid, tracked_fields, context=context)
        return {}

    def message_track(self, cr, uid, ids, tracked_fields, initial_values, context=None):

        def convert_for_display(value, col_info):
            if not value and col_info['type'] == 'boolean':
                return 'False'
            if not value:
                return ''
            if col_info['type'] == 'many2one':
                return value.name_get()[0][1]
            if col_info['type'] == 'selection':
                return dict(col_info['selection'])[value]
            return value

        def format_message(message_description, tracked_values):
            message = ''
            if message_description:
                message = '<span>%s</span>' % message_description
            for name, change in tracked_values.items():
                message += '<div> &nbsp; &nbsp; &bull; <b>%s</b>: ' % change.get('col_info')
                if change.get('old_value'):
                    message += '%s &rarr; ' % change.get('old_value')
                message += '%s</div>' % change.get('new_value')
            return message

        if not tracked_fields:
            return True

        for browse_record in self.browse(cr, uid, ids, context=context):
            initial = initial_values[browse_record.id]
            changes = set()
            tracked_values = {}

            # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
            for col_name, col_info in tracked_fields.items():
                initial_value = initial[col_name]
                record_value = getattr(browse_record, col_name)

                if record_value == initial_value and getattr(self._all_columns[col_name].column, 'track_visibility', None) == 'always':
                    tracked_values[col_name] = dict(col_info=col_info['string'],
                                                        new_value=convert_for_display(record_value, col_info))
                elif record_value != initial_value and (record_value or initial_value):  # because browse null != False
                    if getattr(self._all_columns[col_name].column, 'track_visibility', None) in ['always', 'onchange']:
                        tracked_values[col_name] = dict(col_info=col_info['string'],
                                                            old_value=convert_for_display(initial_value, col_info),
                                                            new_value=convert_for_display(record_value, col_info))
                    if col_name in tracked_fields:
                        changes.add(col_name)
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtypes = []
            for field, track_info in self._track.items():
                if field not in changes:
                    continue
                for subtype, method in track_info.items():
                    if method(self, cr, uid, browse_record, context):
                        subtypes.append(subtype)

            posted = False
            for subtype in subtypes:
                subtype_rec = self.pool.get('ir.model.data').xmlid_to_object(cr, uid, subtype, context=context)
                if not (subtype_rec and subtype_rec.exists()):
                    _logger.debug('subtype %s not found' % subtype)
                    continue
                message = format_message(subtype_rec.description if subtype_rec.description else subtype_rec.name, tracked_values)
                self.message_post(cr, uid, browse_record.id, body=message, subtype=subtype, context=context)
                posted = True
            if not posted:
                message = format_message('', tracked_values)
                self.message_post(cr, uid, browse_record.id, body=message, context=context)
        return True

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        if self._needaction:
            return [('message_unread', '=', True)]
        return []

    def _garbage_collect_attachments(self, cr, uid, context=None):
        """ Garbage collect lost mail attachments. Those are attachments
            - linked to res_model 'mail.compose.message', the composer wizard
            - with res_id 0, because they were created outside of an existing
                wizard (typically user input through Chatter or reports
                created on-the-fly by the templates)
            - unused since at least one day (create_date and write_date)
        """
        limit_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        limit_date_str = datetime.datetime.strftime(limit_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        ir_attachment_obj = self.pool.get('ir.attachment')
        attach_ids = ir_attachment_obj.search(cr, uid, [
                            ('res_model', '=', 'mail.compose.message'),
                            ('res_id', '=', 0),
                            ('create_date', '<', limit_date_str),
                            ('write_date', '<', limit_date_str),
                            ], context=context)
        ir_attachment_obj.unlink(cr, uid, attach_ids, context=context)
        return True

    def check_mail_message_access(self, cr, uid, mids, operation, model_obj=None, context=None):
        """ mail.message check permission rules for related document. This method is
            meant to be inherited in order to implement addons-specific behavior.
            A common behavior would be to allow creating messages when having read
            access rule on the document, for portal document such as issues. """
        if not model_obj:
            model_obj = self
        if hasattr(self, '_mail_post_access'):
            create_allow = self._mail_post_access
        else:
            create_allow = 'write'

        if operation in ['write', 'unlink']:
            check_operation = 'write'
        elif operation == 'create' and create_allow in ['create', 'read', 'write', 'unlink']:
            check_operation = create_allow
        elif operation == 'create':
            check_operation = 'write'
        else:
            check_operation = operation

        model_obj.check_access_rights(cr, uid, check_operation)
        model_obj.check_access_rule(cr, uid, mids, check_operation, context=context)

    def _get_inbox_action_xml_id(self, cr, uid, context=None):
        """ When redirecting towards the Inbox, choose which action xml_id has
            to be fetched. This method is meant to be inherited, at least in portal
            because portal users have a different Inbox action than classic users. """
        return ('mail', 'action_mail_inbox_feeds')

    def message_redirect_action(self, cr, uid, context=None):
        """ For a given message, return an action that either
            - opens the form view of the related document if model, res_id, and
              read access to the document
            - opens the Inbox with a default search on the conversation if model,
              res_id
            - opens the Inbox with context propagated

        """
        if context is None:
            context = {}

        # default action is the Inbox action
        self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        act_model, act_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, *self._get_inbox_action_xml_id(cr, uid, context=context))
        action = self.pool.get(act_model).read(cr, uid, act_id, [])
        params = context.get('params')
        msg_id = model = res_id = None

        if params:
            msg_id = params.get('message_id')
            model = params.get('model')
            res_id = params.get('res_id')
        if not msg_id and not (model and res_id):
            return action
        if msg_id and not (model and res_id):
            msg = self.pool.get('mail.message').browse(cr, uid, msg_id, context=context)
            if msg.exists():
                model, res_id = msg.model, msg.res_id

        # if model + res_id found: try to redirect to the document or fallback on the Inbox
        if model and res_id:
            model_obj = self.pool.get(model)
            if model_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
                try:
                    model_obj.check_access_rule(cr, uid, [res_id], 'read', context=context)
                    action = model_obj.get_formview_action(cr, uid, res_id, context=context)
                except (osv.except_osv, orm.except_orm):
                    pass
            action.update({
                'context': {
                    'search_default_model': model,
                    'search_default_res_id': res_id,
                }
            })
        return action

    def _get_access_link(self, cr, uid, mail, partner, context=None):
        # the parameters to encode for the query and fragment part of url
        query = {'db': cr.dbname}
        fragment = {
            'login': partner.user_ids[0].login,
            'action': 'mail.action_mail_redirect',
        }
        if mail.notification:
            fragment['message_id'] = mail.mail_message_id.id
        elif mail.model and mail.res_id:
            fragment.update(model=mail.model, res_id=mail.res_id)

        return "/web?%s#%s" % (urlencode(query), urlencode(fragment))

    #------------------------------------------------------
    # Email specific
    #------------------------------------------------------

    def message_get_default_recipients(self, cr, uid, ids, context=None):
        if context and context.get('thread_model') and context['thread_model'] in self.pool and context['thread_model'] != self._name:
            if hasattr(self.pool[context['thread_model']], 'message_get_default_recipients'):
                sub_ctx = dict(context)
                sub_ctx.pop('thread_model')
                return self.pool[context['thread_model']].message_get_default_recipients(cr, uid, ids, context=sub_ctx)
        res = {}
        for record in self.browse(cr, SUPERUSER_ID, ids, context=context):
            recipient_ids, email_to, email_cc = set(), False, False
            if 'partner_id' in self._all_columns and record.partner_id:
                recipient_ids.add(record.partner_id.id)
            elif 'email_from' in self._all_columns and record.email_from:
                email_to = record.email_from
            elif 'email' in self._all_columns:
                email_to = record.email
            res[record.id] = {'partner_ids': list(recipient_ids), 'email_to': email_to, 'email_cc': email_cc}
        return res

    def message_get_reply_to(self, cr, uid, ids, default=None, context=None):
        """ Returns the preferred reply-to email address that is basically
            the alias of the document, if it exists. """
        if context is None:
            context = {}
        model_name = context.get('thread_model') or self._name
        alias_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
        res = dict.fromkeys(ids, False)

        # alias domain: check for aliases and catchall
        aliases = {}
        doc_names = {}
        if alias_domain:
            if model_name and model_name != 'mail.thread':
                alias_ids = self.pool['mail.alias'].search(
                    cr, SUPERUSER_ID, [
                        ('alias_parent_model_id.model', '=', model_name),
                        ('alias_parent_thread_id', 'in', ids),
                        ('alias_name', '!=', False)
                    ], context=context)
                aliases.update(
                    dict((alias.alias_parent_thread_id, '%s@%s' % (alias.alias_name, alias_domain))
                         for alias in self.pool['mail.alias'].browse(cr, SUPERUSER_ID, alias_ids, context=context)))
                doc_names.update(
                    dict((ng_res[0], ng_res[1])
                         for ng_res in self.pool[model_name].name_get(cr, SUPERUSER_ID, aliases.keys(), context=context)))
            # left ids: use catchall
            left_ids = set(ids).difference(set(aliases.keys()))
            if left_ids:
                catchall_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.alias", context=context)
                if catchall_alias:
                    aliases.update(dict((res_id, '%s@%s' % (catchall_alias, alias_domain)) for res_id in left_ids))
            # compute name of reply-to
            company_name = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).company_id.name
            res.update(
                dict((res_id, '"%(company_name)s%(document_name)s" <%(email)s>' %
                     {'company_name': company_name,
                      'document_name': doc_names.get(res_id) and ' ' + re.sub(r'[^\w+.]+', '-', doc_names[res_id]) or '',
                      'email': aliases[res_id]
                      } or False) for res_id in aliases.keys()))
        left_ids = set(ids).difference(set(aliases.keys()))
        if left_ids and default:
            res.update(dict((res_id, default) for res_id in left_ids))
        return res

    def message_get_email_values(self, cr, uid, id, notif_mail=None, context=None):
        """ Get specific notification email values to store on the notification
        mail_mail. Void method, inherit it to add custom values. """
        res = dict()
        return res

    #------------------------------------------------------
    # Mail gateway
    #------------------------------------------------------

    def message_capable_models(self, cr, uid, context=None):
        """ Used by the plugin addon, based for plugin_outlook and others. """
        ret_dict = {}
        for model_name in self.pool.obj_list():
            model = self.pool[model_name]
            if hasattr(model, "message_process") and hasattr(model, "message_post"):
                ret_dict[model_name] = model._description
        return ret_dict

    def _message_find_partners(self, cr, uid, message, header_fields=['From'], context=None):
        """ Find partners related to some header fields of the message.

            :param string message: an email.message instance """
        s = ', '.join([decode(message.get(h)) for h in header_fields if message.get(h)])
        return filter(lambda x: x, self._find_partner_from_emails(cr, uid, None, tools.email_split(s), context=context))

    def message_route_verify(self, cr, uid, message, message_dict, route, update_author=True, assert_model=True, create_fallback=True, allow_private=False, context=None):
        """ Verify route validity. Check and rules:
            1 - if thread_id -> check that document effectively exists; otherwise
                fallback on a message_new by resetting thread_id
            2 - check that message_update exists if thread_id is set; or at least
                that message_new exist
            [ - find author_id if udpate_author is set]
            3 - if there is an alias, check alias_contact:
                'followers' and thread_id:
                    check on target document that the author is in the followers
                'followers' and alias_parent_thread_id:
                    check on alias parent document that the author is in the
                    followers
                'partners': check that author_id id set
        """

        assert isinstance(route, (list, tuple)), 'A route should be a list or a tuple'
        assert len(route) == 5, 'A route should contain 5 elements: model, thread_id, custom_values, uid, alias record'

        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        author_id = message_dict.get('author_id')
        model, thread_id, alias = route[0], route[1], route[4]
        model_pool = None

        def _create_bounce_email():
            mail_mail = self.pool.get('mail.mail')
            mail_id = mail_mail.create(cr, uid, {
                            'body_html': '<div><p>Hello,</p>'
                                '<p>The following email sent to %s cannot be accepted because this is '
                                'a private email address. Only allowed people can contact us at this address.</p></div>'
                                '<blockquote>%s</blockquote>' % (message.get('to'), message_dict.get('body')),
                            'subject': 'Re: %s' % message.get('subject'),
                            'email_to': message.get('from'),
                            'auto_delete': True,
                        }, context=context)
            mail_mail.send(cr, uid, [mail_id], context=context)

        def _warn(message):
            _logger.warning('Routing mail with Message-Id %s: route %s: %s',
                                message_id, route, message)

        # Wrong model
        if model and not model in self.pool:
            if assert_model:
                assert model in self.pool, 'Routing: unknown target model %s' % model
            _warn('unknown target model %s' % model)
            return ()
        elif model:
            model_pool = self.pool[model]

        # Private message: should not contain any thread_id
        if not model and thread_id:
            if assert_model:
                if thread_id: 
                    raise ValueError('Routing: posting a message without model should be with a null res_id (private message), received %s.' % thread_id)
            _warn('posting a message without model should be with a null res_id (private message), received %s resetting thread_id' % thread_id)
            thread_id = 0
        # Private message: should have a parent_id (only answers)
        if not model and not message_dict.get('parent_id'):
            if assert_model:
                if not message_dict.get('parent_id'):
                    raise ValueError('Routing: posting a message without model should be with a parent_id (private mesage).')
            _warn('posting a message without model should be with a parent_id (private mesage), skipping')
            return ()

        # Existing Document: check if exists; if not, fallback on create if allowed
        if thread_id and not model_pool.exists(cr, uid, thread_id):
            if create_fallback:
                _warn('reply to missing document (%s,%s), fall back on new document creation' % (model, thread_id))
                thread_id = None
            elif assert_model:
                assert model_pool.exists(cr, uid, thread_id), 'Routing: reply to missing document (%s,%s)' % (model, thread_id)
            else:
                _warn('reply to missing document (%s,%s), skipping' % (model, thread_id))
                return ()

        # Existing Document: check model accepts the mailgateway
        if thread_id and model and not hasattr(model_pool, 'message_update'):
            if create_fallback:
                _warn('model %s does not accept document update, fall back on document creation' % model)
                thread_id = None
            elif assert_model:
                assert hasattr(model_pool, 'message_update'), 'Routing: model %s does not accept document update, crashing' % model
            else:
                _warn('model %s does not accept document update, skipping' % model)
                return ()

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(model_pool, 'message_new'):
            if assert_model:
                if not hasattr(model_pool, 'message_new'):
                    raise ValueError(
                        'Model %s does not accept document creation, crashing' % model
                    )
            _warn('model %s does not accept document creation, skipping' % model)
            return ()

        # Update message author if asked
        # We do it now because we need it for aliases (contact settings)
        if not author_id and update_author:
            author_ids = self._find_partner_from_emails(cr, uid, thread_id, [email_from], model=model, context=context)
            if author_ids:
                author_id = author_ids[0]
                message_dict['author_id'] = author_id

        # Alias: check alias_contact settings
        if alias and alias.alias_contact == 'followers' and (thread_id or alias.alias_parent_thread_id):
            if thread_id:
                obj = self.pool[model].browse(cr, uid, thread_id, context=context)
            else:
                obj = self.pool[alias.alias_parent_model_id.model].browse(cr, uid, alias.alias_parent_thread_id, context=context)
            if not author_id or not author_id in [fol.id for fol in obj.message_follower_ids]:
                _warn('alias %s restricted to internal followers, skipping' % alias.alias_name)
                _create_bounce_email()
                return ()
        elif alias and alias.alias_contact == 'partners' and not author_id:
            _warn('alias %s does not accept unknown author, skipping' % alias.alias_name)
            _create_bounce_email()
            return ()

        if not model and not thread_id and not alias and not allow_private:
            return ()

        return (model, thread_id, route[2], route[3], route[4])

    def message_route(self, cr, uid, message, message_dict, model=None, thread_id=None,
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
           :param dict message_dict: dictionary holding message variables
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
           :return: list of [model, thread_id, custom_values, user_id, alias]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        mail_msg_obj = self.pool['mail.message']
        fallback_model = model

        # Get email.message.Message variables for future processing
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')
        references = decode_header(message, 'References')
        in_reply_to = decode_header(message, 'In-Reply-To')
        thread_references = references or in_reply_to

        # 1. message is a reply to an existing message (exact match of message_id)
        ref_match = thread_references and tools.reference_re.search(thread_references)
        msg_references = thread_references.split()
        mail_message_ids = mail_msg_obj.search(cr, uid, [('message_id', 'in', msg_references)], context=context)
        if ref_match and mail_message_ids:
            original_msg = mail_msg_obj.browse(cr, SUPERUSER_ID, mail_message_ids[0], context=context)
            model, thread_id = original_msg.model, original_msg.res_id
            route = self.message_route_verify(
                cr, uid, message, message_dict,
                (model, thread_id, custom_values, uid, None),
                update_author=True, assert_model=False, create_fallback=True, context=context)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, uid)
                return [route]

        # 2. message is a reply to an existign thread (6.1 compatibility)
        if ref_match:
            reply_thread_id = int(ref_match.group(1))
            reply_model = ref_match.group(2) or fallback_model
            reply_hostname = ref_match.group(3)
            local_hostname = socket.gethostname()
            # do not match forwarded emails from another OpenERP system (thread_id collision!)
            if local_hostname == reply_hostname:
                thread_id, model = reply_thread_id, reply_model
                if thread_id and model in self.pool:
                    model_obj = self.pool[model]
                    compat_mail_msg_ids = mail_msg_obj.search(
                        cr, uid, [
                            ('message_id', '=', False),
                            ('model', '=', model),
                            ('res_id', '=', thread_id),
                        ], context=context)
                    if compat_mail_msg_ids and model_obj.exists(cr, uid, thread_id) and hasattr(model_obj, 'message_update'):
                        route = self.message_route_verify(
                            cr, uid, message, message_dict,
                            (model, thread_id, custom_values, uid, None),
                            update_author=True, assert_model=True, create_fallback=True, context=context)
                        if route:
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct thread reply (compat-mode) to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                                email_from, email_to, message_id, model, thread_id, custom_values, uid)
                            return [route]

        # 2. Reply to a private message
        if in_reply_to:
            mail_message_ids = mail_msg_obj.search(cr, uid, [
                                ('message_id', '=', in_reply_to),
                                '!', ('message_id', 'ilike', 'reply_to')
                            ], limit=1, context=context)
            if mail_message_ids:
                mail_message = mail_msg_obj.browse(cr, uid, mail_message_ids[0], context=context)
                route = self.message_route_verify(cr, uid, message, message_dict,
                                (mail_message.model, mail_message.res_id, custom_values, uid, None),
                                update_author=True, assert_model=True, create_fallback=True, allow_private=True, context=context)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct reply to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, mail_message.id, custom_values, uid)
                    return [route]

        # 3. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = \
             ','.join([decode_header(message, 'Delivered-To'),
                       decode_header(message, 'To'),
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
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(cr, uid, message, context=context)
                        user_id = uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, eval(alias.alias_defaults), user_id, alias)
                    route = self.message_route_verify(cr, uid, message, message_dict, route,
                                update_author=True, assert_model=True, create_fallback=True, context=context)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 4. Fallback to the provided parameters, if they work
        if not thread_id:
            # Legacy: fallback to matching [ID] in the Subject
            match = tools.res_re.search(decode_header(message, 'Subject'))
            thread_id = match and match.group(1)
            # Convert into int (bug spotted in 7.0 because of str)
            try:
                thread_id = int(thread_id)
            except:
                thread_id = False
        route = self.message_route_verify(cr, uid, message, message_dict,
                        (fallback_model, thread_id, custom_values, uid, None),
                        update_author=True, assert_model=True, context=context)
        if route:
            _logger.info(
                'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                email_from, email_to, message_id, fallback_model, thread_id, custom_values, uid)
            return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
                'No possible route found for incoming message from %s to %s (Message-Id %s:). '
                'Create an appropriate mail.alias or force the destination model.' %
                (email_from, email_to, message_id)
            )

    def message_route_process(self, cr, uid, message, message_dict, routes, context=None):
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes:
            if self._name == 'mail.thread':
                context.update({'thread_model': model})
            if model:
                model_pool = self.pool[model]
                if not (thread_id and hasattr(model_pool, 'message_update') or hasattr(model_pool, 'message_new')):
                    raise ValueError(
                        "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" %
                        (message_dict['message_id'], model)
                    )

                # disabled subscriptions during message_new/update to avoid having the system user running the
                # email gateway become a follower of all inbound messages
                nosub_ctx = dict(context, mail_create_nosubscribe=True, mail_create_nolog=True)
                if thread_id and hasattr(model_pool, 'message_update'):
                    model_pool.message_update(cr, user_id, [thread_id], message_dict, context=nosub_ctx)
                else:
                    thread_id = model_pool.message_new(cr, user_id, message_dict, custom_values, context=nosub_ctx)
            else:
                if thread_id:
                    raise ValueError("Posting a message without model should be with a null res_id, to create a private message.")
                model_pool = self.pool.get('mail.thread')
            if not hasattr(model_pool, 'message_post'):
                context['thread_model'] = model
                model_pool = self.pool['mail.thread']
            new_msg_id = model_pool.message_post(cr, uid, [thread_id], context=context, subtype='mail.mt_comment', **message_dict)

            if partner_ids:
                # postponed after message_post, because this is an external message and we don't want to create
                # duplicate emails due to notifications
                self.pool.get('mail.message').write(cr, uid, [new_msg_id], {'partner_ids': partner_ids}, context=context)
        return thread_id

    def message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, context=None):
        """ Process an incoming RFC2822 email message, relying on
            ``mail.message.parse()`` for the parsing operation,
            and ``message_route()`` to figure out the target model.

            Once the target model is known, its ``message_new`` method
            is called with the new message (if the thread record did not exist)
            or its ``message_update`` method (if it did).

            There is a special case where the target model is False: a reply
            to a private message. In this case, we skip the message_new /
            message_update step, to just post a new message using mail_thread
            message_post.

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
        if context is None:
            context = {}

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

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = self.message_parse(cr, uid, msg_txt, save_original=save_original, context=context)
        if strip_attachments:
            msg.pop('attachments', None)

        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.pool.get('mail.message').search(cr, SUPERUSER_ID, [
                                                                ('message_id', '=', msg.get('message_id')),
                                                                ], context=context)
            if existing_msg_ids:
                _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                                msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False

        # find possible routes for the message
        routes = self.message_route(cr, uid, msg_txt, msg, model, thread_id, custom_values, context=context)
        thread_id = self.message_route_process(cr, uid, msg_txt, msg, routes, context=context)
        return thread_id

    def message_new(self, cr, uid, msg_dict, custom_values=None, context=None):
        """Called by ``message_process`` when a new message is received
           for a given thread model, if the message did not belong to
           an existing thread.
           The default behavior is to create a new record of the corresponding
           model (based on some very basic info extracted from the message).
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
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        model = context.get('thread_model') or self._name
        model_pool = self.pool[model]
        fields = model_pool.fields_get(cr, uid, context=context)
        if 'name' in fields and not data.get('name'):
            data['name'] = msg_dict.get('subject', '')
        res_id = model_pool.create(cr, uid, data, context=context)
        return res_id

    def message_update(self, cr, uid, ids, msg_dict, update_vals=None, context=None):
        """Called by ``message_process`` when a new message is received
           for an existing thread. The default behavior is to update the record
           with update_vals taken from the incoming email.
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

        # Be careful, content-type may contain tricky content like in the
        # following example so test the MIME type with startswith()
        #
        # Content-Type: multipart/related;
        #   boundary="_004_3f1e4da175f349248b8d43cdeb9866f1AMSPR06MB343eurprd06pro_";
        #   type="text/html"
        if not message.is_multipart() or message.get('content-type', '').startswith("text/"):
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools.ustr(body, encoding, errors='replace')
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = tools.append_content_to_html(u'', body, preserve=True)
        else:
            alternative = False
            for part in message.walk():
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                # part.get_filename returns decoded value if able to decode, coded otherwise.
                # original get_filename is not able to decode iso-8859-1 (for instance).
                # therefore, iso encoded attachements are not able to be decoded properly with get_filename
                # code here partially copy the original get_filename method, but handle more encoding
                filename=part.get_param('filename', None, 'content-disposition')
                if not filename:
                    filename=part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        # RFC2231
                        filename=email.utils.collapse_rfc2231_value(filename).strip()
                    else:
                        filename=decode(filename)
                encoding = part.get_content_charset()  # None if attachment
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    body = tools.append_content_to_html(body, tools.ustr(part.get_payload(decode=True),
                                                                         encoding, errors='replace'), preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if alternative:
                        body = html
                    else:
                        body = tools.append_content_to_html(body, html, plaintext=False)
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

                    { 'message_id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'body': unified_body,
                      'attachments': [('file1', 'bytes'),
                                      ('file2', 'bytes')}
                    }
        """
        msg_dict = {
            'type': 'email',
        }
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

        if message.get('Subject'):
            msg_dict['subject'] = decode(message.get('Subject'))

        # Envelope fields not stored in mail.message but made available for message_new()
        msg_dict['from'] = decode(message.get('from'))
        msg_dict['to'] = decode(message.get('to'))
        msg_dict['cc'] = decode(message.get('cc'))
        msg_dict['email_from'] = decode(message.get('from'))
        partner_ids = self._message_find_partners(cr, uid, message, ['To', 'Cc'], context=context)
        msg_dict['partner_ids'] = [(4, partner_id) for partner_id in partner_ids]

        if message.get('Date'):
            try:
                date_hdr = decode(message.get('Date'))
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers.
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(tz=pytz.utc)
            except Exception:
                _logger.warning('Failed to parse Date header %r in incoming mail '
                                'with message-id %r, assuming current date/time.',
                                message.get('Date'), message_id)
                stored_date = datetime.datetime.now()
            msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        if message.get('In-Reply-To'):
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id', '=', decode(message['In-Reply-To'].strip()))])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list =  mail_header_msgid_re.findall(decode(message['References']))
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id', 'in', [x.strip() for x in msg_list])])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        return msg_dict

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    def _message_add_suggested_recipient(self, cr, uid, result, obj, partner=None, email=None, reason='', context=None):
        """ Called by message_get_suggested_recipients, to add a suggested
            recipient in the result dictionary. The form is :
                partner_id, partner_name<partner_email> or partner_name, reason """
        if email and not partner:
            # get partner info from email
            partner_info = self.message_partner_info_from_emails(cr, uid, obj.id, [email], context=context)[0]
            if partner_info.get('partner_id'):
                partner = self.pool.get('res.partner').browse(cr, SUPERUSER_ID, [partner_info['partner_id']], context=context)[0]
        if email and email in [val[1] for val in result[obj.id]]:  # already existing email -> skip
            return result
        if partner and partner in obj.message_follower_ids:  # recipient already in the followers -> skip
            return result
        if partner and partner in [val[0] for val in result[obj.id]]:  # already existing partner ID -> skip
            return result
        if partner and partner.email:  # complete profile: id, name <email>
            result[obj.id].append((partner.id, '%s<%s>' % (partner.name, partner.email), reason))
        elif partner:  # incomplete profile: id, name
            result[obj.id].append((partner.id, '%s' % (partner.name), reason))
        else:  # unknown partner, we are probably managing an email address
            result[obj.id].append((False, email, reason))
        return result

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        """ Returns suggested recipients for ids. Those are a list of
            tuple (partner_id, partner_name, reason), to be managed by Chatter. """
        result = dict.fromkeys(ids, list())
        if self._all_columns.get('user_id'):
            for obj in self.browse(cr, SUPERUSER_ID, ids, context=context):  # SUPERUSER because of a read on res.users that would crash otherwise
                if not obj.user_id or not obj.user_id.partner_id:
                    continue
                self._message_add_suggested_recipient(cr, uid, result, obj, partner=obj.user_id.partner_id, reason=self._all_columns['user_id'].column.string, context=context)
        return result

    def _find_partner_from_emails(self, cr, uid, id, emails, model=None, context=None, check_followers=True):
        """ Utility method to find partners from email addresses. The rules are :
            1 - check in document (model | self, id) followers
            2 - try to find a matching partner that is also an user
            3 - try to find a matching partner

            :param list emails: list of email addresses
            :param string model: model to fetch related record; by default self
                is used.
            :param boolean check_followers: check in document followers
        """
        partner_obj = self.pool['res.partner']
        partner_ids = []
        obj = None
        if id and (model or self._name != 'mail.thread') and check_followers:
            if model:
                obj = self.pool[model].browse(cr, uid, id, context=context)
            else:
                obj = self.browse(cr, uid, id, context=context)
        for contact in emails:
            partner_id = False
            email_address = tools.email_split(contact)
            if not email_address:
                partner_ids.append(partner_id)
                continue
            email_address = email_address[0]
            # first try: check in document's followers
            if obj:
                for follower in obj.message_follower_ids:
                    if follower.email == email_address:
                        partner_id = follower.id
            # second try: check in partners that are also users
            if not partner_id:
                ids = partner_obj.search(cr, SUPERUSER_ID, [
                                                ('email', 'ilike', email_address),
                                                ('user_ids', '!=', False)
                                            ], limit=1, context=context)
                if ids:
                    partner_id = ids[0]
            # third try: check in partners
            if not partner_id:
                ids = partner_obj.search(cr, SUPERUSER_ID, [
                                                ('email', 'ilike', email_address)
                                            ], limit=1, context=context)
                if ids:
                    partner_id = ids[0]
            partner_ids.append(partner_id)
        return partner_ids

    def message_partner_info_from_emails(self, cr, uid, id, emails, link_mail=False, context=None):
        """ Convert a list of emails into a list partner_ids and a list
            new_partner_ids. The return value is non conventional because
            it is meant to be used by the mail widget.

            :return dict: partner_ids and new_partner_ids """
        mail_message_obj = self.pool.get('mail.message')
        partner_ids = self._find_partner_from_emails(cr, uid, id, emails, context=context)
        result = list()
        for idx in range(len(emails)):
            email_address = emails[idx]
            partner_id = partner_ids[idx]
            partner_info = {'full_name': email_address, 'partner_id': partner_id}
            result.append(partner_info)

            # link mail with this from mail to the new partner id
            if link_mail and partner_info['partner_id']:
                message_ids = mail_message_obj.search(cr, SUPERUSER_ID, [
                                    '|',
                                    ('email_from', '=', email_address),
                                    ('email_from', 'ilike', '<%s>' % email_address),
                                    ('author_id', '=', False)
                                ], context=context)
                if message_ids:
                    mail_message_obj.write(cr, SUPERUSER_ID, message_ids, {'author_id': partner_info['partner_id']}, context=context)
        return result

    def _message_preprocess_attachments(self, cr, uid, attachments, attachment_ids, attach_model, attach_res_id, context=None):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``,
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param str attach_model: the model of the attachments parent record
        :param integer attach_res_id: the id of the attachments parent record
        """
        Attachment = self.pool['ir.attachment']
        m2m_attachment_ids = []
        if attachment_ids:
            filtered_attachment_ids = Attachment.search(cr, SUPERUSER_ID, [
                ('res_model', '=', 'mail.compose.message'),
                ('create_uid', '=', uid),
                ('id', 'in', attachment_ids)], context=context)
            if filtered_attachment_ids:
                Attachment.write(cr, SUPERUSER_ID, filtered_attachment_ids, {'res_model': attach_model, 'res_id': attach_res_id}, context=context)
            m2m_attachment_ids += [(4, id) for id in attachment_ids]
        # Handle attachments parameter, that is a dictionary of attachments
        for name, content in attachments:
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            data_attach = {
                'name': name,
                'datas': base64.b64encode(str(content)),
                'datas_fname': name,
                'description': name,
                'res_model': attach_model,
                'res_id': attach_res_id,
            }
            m2m_attachment_ids.append((0, 0, data_attach))
        return m2m_attachment_ids

    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID.

            :param int thread_id: thread ID to post into, or list with one ID;
                if False/0, mail.message model will also be set as False
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str type: see mail_message.type field
            :param str content_subtype:: if plaintext: convert body into html
            :param int parent_id: handle reply to a previous message by adding the
                parent partners to the message in case of private discussion
            :param tuple(str,str) attachments or list id: list of attachment tuples in the form
                ``(name,content)``, where content is NOT base64 encoded

            Extra keyword arguments will be used as default column values for the
            new mail.message record. Special cases:
                - attachment_ids: supposed not attached to any document; attach them
                    to the related document. Should only be set by Chatter.
            :return int: ID of newly created mail.message
        """
        if context is None:
            context = {}
        if attachments is None:
            attachments = {}
        mail_message = self.pool.get('mail.message')
        ir_attachment = self.pool.get('ir.attachment')

        assert (not thread_id) or \
                isinstance(thread_id, (int, long)) or \
                (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
                "Invalid thread_id; should be 0, False, an ID or a list with one ID"
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]

        # if we're processing a message directly coming from the gateway, the destination model was
        # set in the context.
        model = False
        if thread_id:
            model = context.get('thread_model', self._name) if self._name == 'mail.thread' else self._name
            if model != self._name and hasattr(self.pool[model], 'message_post'):
                del context['thread_model']
                return self.pool[model].message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)

        #0: Find the message's author, because we need it for private discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.pool.get('mail.message')._get_default_author(cr, uid, context=context)

        # 1: Handle content subtype: if plaintext, converto into HTML
        if content_subtype == 'plaintext':
            body = tools.plaintext2html(body)

        # 2: Private message: add recipients (recipients and author of parent message) - current author
        #   + legacy-code management (! we manage only 4 and 6 commands)
        partner_ids = set()
        kwargs_partner_ids = kwargs.pop('partner_ids', [])
        for partner_id in kwargs_partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                partner_ids.add(partner_id[1])
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                partner_ids |= set(partner_id[2])
            elif isinstance(partner_id, (int, long)):
                partner_ids.add(partner_id)
            else:
                pass  # we do not manage anything else
        if parent_id and not model:
            parent_message = mail_message.browse(cr, uid, parent_id, context=context)
            private_followers = set([partner.id for partner in parent_message.partner_ids])
            if parent_message.author_id:
                private_followers.add(parent_message.author_id.id)
            private_followers -= set([author_id])
            partner_ids |= private_followers

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_preprocess_attachments(cr, uid, attachments, kwargs.pop('attachment_ids', []), model, thread_id, context)

        # 4: mail.message.subtype
        subtype_id = False
        if subtype:
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, subtype)

        # automatically subscribe recipients if asked to
        if context.get('mail_post_autofollow') and thread_id and partner_ids:
            partner_to_subscribe = partner_ids
            if context.get('mail_post_autofollow_partner_ids'):
                partner_to_subscribe = filter(lambda item: item in context.get('mail_post_autofollow_partner_ids'), partner_ids)
            self.message_subscribe(cr, uid, [thread_id], list(partner_to_subscribe), context=context)

        # _mail_flat_thread: automatically set free messages to the first posted message
        if self._mail_flat_thread and not parent_id and thread_id:
            message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model)], context=context, order="id ASC", limit=1)
            parent_id = message_ids and message_ids[0] or False
        # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            message_ids = mail_message.search(cr, SUPERUSER_ID, [('id', '=', parent_id), ('parent_id', '!=', False)], context=context)
            # avoid loops when finding ancestors
            processed_list = []
            if message_ids:
                message = mail_message.browse(cr, SUPERUSER_ID, message_ids[0], context=context)
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id

        values = kwargs
        values.update({
            'author_id': author_id,
            'model': model,
            'res_id': thread_id or False,
            'body': body,
            'subject': subject or False,
            'type': type,
            'parent_id': parent_id,
            'attachment_ids': attachment_ids,
            'subtype_id': subtype_id,
            'partner_ids': [(4, pid) for pid in partner_ids],
        })

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        msg_id = mail_message.create(cr, uid, values, context=context)

        # Post-process: subscribe author, update message_last_post
        if model and model != 'mail.thread' and thread_id and subtype_id:
            # done with SUPERUSER_ID, because on some models users can post only with read access, not necessarily write access
            self.write(cr, SUPERUSER_ID, [thread_id], {'message_last_post': fields.datetime.now()}, context=context)
        message = mail_message.browse(cr, uid, msg_id, context=context)
        if message.author_id and thread_id and type != 'notification' and not context.get('mail_create_nosubscribe'):
            self.message_subscribe(cr, uid, [thread_id], [message.author_id.id], context=context)
        return msg_id

    #------------------------------------------------------
    # Followers API
    #------------------------------------------------------

    def message_get_subscription_data(self, cr, uid, ids, user_pid=None, context=None):
        """ Wrapper to get subtypes data. """
        return self._get_subscription_data(cr, uid, ids, None, None, user_pid=user_pid, context=context)

    def message_subscribe_users(self, cr, uid, ids, user_ids=None, subtype_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, subscribe uid instead. """
        if user_ids is None:
            user_ids = [uid]
        partner_ids = [user.partner_id.id for user in self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        return self.message_subscribe(cr, uid, ids, partner_ids, subtype_ids=subtype_ids, context=context)

    def message_subscribe(self, cr, uid, ids, partner_ids, subtype_ids=None, context=None):
        """ Add partners to the records followers. """
        if context is None:
            context = {}
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True

        mail_followers_obj = self.pool.get('mail.followers')
        subtype_obj = self.pool.get('mail.message.subtype')

        user_pid = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        if set(partner_ids) == set([user_pid]):
            try:
                self.check_access_rights(cr, uid, 'read')
                self.check_access_rule(cr, uid, ids, 'read')
            except (osv.except_osv, orm.except_orm):
                return False
        else:
            self.check_access_rights(cr, uid, 'write')
            self.check_access_rule(cr, uid, ids, 'write')

        existing_pids_dict = {}
        fol_ids = mail_followers_obj.search(cr, SUPERUSER_ID, ['&', '&', ('res_model', '=', self._name), ('res_id', 'in', ids), ('partner_id', 'in', partner_ids)])
        for fol in mail_followers_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context):
            existing_pids_dict.setdefault(fol.res_id, set()).add(fol.partner_id.id)

        # subtype_ids specified: update already subscribed partners
        if subtype_ids and fol_ids:
            mail_followers_obj.write(cr, SUPERUSER_ID, fol_ids, {'subtype_ids': [(6, 0, subtype_ids)]}, context=context)
        # subtype_ids not specified: do not update already subscribed partner, fetch default subtypes for new partners
        if subtype_ids is None:
            subtype_ids = subtype_obj.search(
                cr, uid, [
                    ('default', '=', True), '|', ('res_model', '=', self._name), ('res_model', '=', False)], context=context)

        for id in ids:
            existing_pids = existing_pids_dict.get(id, set())
            new_pids = set(partner_ids) - existing_pids

            # subscribe new followers
            for new_pid in new_pids:
                mail_followers_obj.create(
                    cr, SUPERUSER_ID, {
                        'res_model': self._name,
                        'res_id': id,
                        'partner_id': new_pid,
                        'subtype_ids': [(6, 0, subtype_ids)],
                    }, context=context)

        return True

    def message_unsubscribe_users(self, cr, uid, ids, user_ids=None, context=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, unsubscribe uid instead. """
        if user_ids is None:
            user_ids = [uid]
        partner_ids = [user.partner_id.id for user in self.pool.get('res.users').browse(cr, uid, user_ids, context=context)]
        return self.message_unsubscribe(cr, uid, ids, partner_ids, context=context)

    def message_unsubscribe(self, cr, uid, ids, partner_ids, context=None):
        """ Remove partners from the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True
        user_pid = self.pool.get('res.users').read(cr, uid, uid, ['partner_id'], context=context)['partner_id'][0]
        if set(partner_ids) == set([user_pid]):
            self.check_access_rights(cr, uid, 'read')
            self.check_access_rule(cr, uid, ids, 'read')
        else:
            self.check_access_rights(cr, uid, 'write')
            self.check_access_rule(cr, uid, ids, 'write')
        fol_obj = self.pool['mail.followers']
        fol_ids = fol_obj.search(
            cr, SUPERUSER_ID, [
                ('res_model', '=', self._name),
                ('res_id', 'in', ids),
                ('partner_id', 'in', partner_ids)
            ], context=context)
        return fol_obj.unlink(cr, SUPERUSER_ID, fol_ids, context=context)

    def _message_get_auto_subscribe_fields(self, cr, uid, updated_fields, auto_follow_fields=None, context=None):
        """ Returns the list of relational fields linking to res.users that should
            trigger an auto subscribe. The default list checks for the fields
            - called 'user_id'
            - linking to res.users
            - with track_visibility set
            In OpenERP V7, this is sufficent for all major addon such as opportunity,
            project, issue, recruitment, sale.
            Override this method if a custom behavior is needed about fields
            that automatically subscribe users.
        """
        if auto_follow_fields is None:
            auto_follow_fields = ['user_id']
        user_field_lst = []
        for name, column_info in self._all_columns.items():
            if name in auto_follow_fields and name in updated_fields and getattr(column_info.column, 'track_visibility', False) and column_info.column._obj == 'res.users':
                user_field_lst.append(name)
        return user_field_lst

    def message_auto_subscribe(self, cr, uid, ids, updated_fields, context=None, values=None):
        """ Handle auto subscription. Two methods for auto subscription exist:

         - tracked res.users relational fields, such as user_id fields. Those fields
           must be relation fields toward a res.users record, and must have the
           track_visilibity attribute set.
         - using subtypes parent relationship: check if the current model being
           modified has an header record (such as a project for tasks) whose followers
           can be added as followers of the current records. Example of structure
           with project and task:

          - st_project_1.parent_id = st_task_1
          - st_project_1.res_model = 'project.project'
          - st_project_1.relation_field = 'project_id'
          - st_task_1.model = 'project.task'

        :param list updated_fields: list of updated fields to track
        :param dict values: updated values; if None, the first record will be browsed
                            to get the values. Added after releasing 7.0, therefore
                            not merged with updated_fields argumment.
        """
        subtype_obj = self.pool.get('mail.message.subtype')
        follower_obj = self.pool.get('mail.followers')
        new_followers = dict()

        # fetch auto_follow_fields: res.users relation fields whose changes are tracked for subscription
        user_field_lst = self._message_get_auto_subscribe_fields(cr, uid, updated_fields, context=context)

        # fetch header subtypes
        header_subtype_ids = subtype_obj.search(cr, uid, ['|', ('res_model', '=', False), ('parent_id.res_model', '=', self._name)], context=context)
        subtypes = subtype_obj.browse(cr, uid, header_subtype_ids, context=context)

        # if no change in tracked field or no change in tracked relational field: quit
        relation_fields = set([subtype.relation_field for subtype in subtypes if subtype.relation_field is not False])
        if not any(relation in updated_fields for relation in relation_fields) and not user_field_lst:
            return True

        # legacy behavior: if values is not given, compute the values by browsing
        # @TDENOTE: remove me in 8.0
        if values is None:
            record = self.browse(cr, uid, ids[0], context=context)
            for updated_field in updated_fields:
                field_value = getattr(record, updated_field)
                if isinstance(field_value, browse_record):
                    field_value = field_value.id
                elif isinstance(field_value, browse_null):
                    field_value = False
                values[updated_field] = field_value

        # find followers of headers, update structure for new followers
        headers = set()
        for subtype in subtypes:
            if subtype.relation_field and values.get(subtype.relation_field):
                headers.add((subtype.res_model, values.get(subtype.relation_field)))
        if headers:
            header_domain = ['|'] * (len(headers) - 1)
            for header in headers:
                header_domain += ['&', ('res_model', '=', header[0]), ('res_id', '=', header[1])]
            header_follower_ids = follower_obj.search(
                cr, SUPERUSER_ID,
                header_domain,
                context=context
            )
            for header_follower in follower_obj.browse(cr, SUPERUSER_ID, header_follower_ids, context=context):
                for subtype in header_follower.subtype_ids:
                    if subtype.parent_id and subtype.parent_id.res_model == self._name:
                        new_followers.setdefault(header_follower.partner_id.id, set()).add(subtype.parent_id.id)
                    elif subtype.res_model is False:
                        new_followers.setdefault(header_follower.partner_id.id, set()).add(subtype.id)

        # add followers coming from res.users relational fields that are tracked
        user_ids = [values[name] for name in user_field_lst if values.get(name)]
        user_pids = [user.partner_id.id for user in self.pool.get('res.users').browse(cr, SUPERUSER_ID, user_ids, context=context)]
        for partner_id in user_pids:
            new_followers.setdefault(partner_id, None)

        for pid, subtypes in new_followers.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(cr, uid, ids, [pid], subtypes, context=context)

        # find first email message, set it as unread for auto_subscribe fields for them to have a notification
        if user_pids:
            for record_id in ids:
                message_obj = self.pool.get('mail.message')
                msg_ids = message_obj.search(cr, SUPERUSER_ID, [
                    ('model', '=', self._name),
                    ('res_id', '=', record_id),
                    ('type', '=', 'email')], limit=1, context=context)
                if not msg_ids:
                    msg_ids = message_obj.search(cr, SUPERUSER_ID, [
                        ('model', '=', self._name),
                        ('res_id', '=', record_id)], limit=1, context=context)
                if msg_ids:
                    self.pool.get('mail.notification')._notify(cr, uid, msg_ids[0], partners_to_notify=user_pids, context=context)

        return True

    #------------------------------------------------------
    # Thread state
    #------------------------------------------------------

    def message_mark_as_unread(self, cr, uid, ids, context=None):
        """ Set as unread. """
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
        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        cr.execute('''
            UPDATE mail_notification SET
                read=true
            WHERE
                message_id IN (SELECT id FROM mail_message WHERE res_id=ANY(%s) AND model=%s) AND
                partner_id = %s
        ''', (ids, self._name, partner_id))
        return True

    #------------------------------------------------------
    # Thread suggestion
    #------------------------------------------------------

    def get_suggested_thread(self, cr, uid, removed_suggested_threads=None, context=None):
        """Return a list of suggested threads, sorted by the numbers of followers"""
        if context is None:
            context = {}

        # TDE HACK: originally by MAT from portal/mail_mail.py but not working until the inheritance graph bug is not solved in trunk
        # TDE FIXME: relocate in portal when it won't be necessary to reload the hr.employee model in an additional bridge module
        if self.pool['res.groups']._all_columns.get('is_portal'):
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
            if any(group.is_portal for group in user.groups_id):
                return []

        threads = []
        if removed_suggested_threads is None:
            removed_suggested_threads = []

        thread_ids = self.search(cr, uid, [('id', 'not in', removed_suggested_threads), ('message_is_follower', '=', False)], context=context)
        for thread in self.browse(cr, uid, thread_ids, context=context):
            data = {
                'id': thread.id,
                'popularity': len(thread.message_follower_ids),
                'name': thread.name,
                'image_small': thread.image_small
            }
            threads.append(data)
        return sorted(threads, key=lambda x: (x['popularity'], x['id']), reverse=True)[:3]

    def message_change_thread(self, cr, uid, id, new_res_id, new_model, context=None):
        """
        Transfert the list of the mail thread messages from an model to another

        :param id : the old res_id of the mail.message
        :param new_res_id : the new res_id of the mail.message
        :param new_model : the name of the new model of the mail.message

        Example :   self.pool.get("crm.lead").message_change_thread(self, cr, uid, 2, 4, "project.issue", context) 
                    will transfert thread of the lead (id=2) to the issue (id=4)
        """

        # get the sbtype id of the comment Message
        subtype_res_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'mail.mt_comment', raise_if_not_found=True)
        
        # get the ids of the comment and none-comment of the thread
        message_obj = self.pool.get('mail.message')
        msg_ids_comment = message_obj.search(cr, uid, [
                    ('model', '=', self._name),
                    ('res_id', '=', id),
                    ('subtype_id', '=', subtype_res_id)], context=context)
        msg_ids_not_comment = message_obj.search(cr, uid, [
                    ('model', '=', self._name),
                    ('res_id', '=', id),
                    ('subtype_id', '!=', subtype_res_id)], context=context)
        
        # update the messages
        message_obj.write(cr, uid, msg_ids_comment, {"res_id" : new_res_id, "model" : new_model}, context=context)
        message_obj.write(cr, uid, msg_ids_not_comment, {"res_id" : new_res_id, "model" : new_model, "subtype_id" : None}, context=context)
        
        return True
