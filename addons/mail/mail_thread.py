# -*- coding: utf-8 -*-

import base64
from collections import OrderedDict
import datetime
import dateutil
import email
from email.message import Message
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
from email.message import Message
from email.utils import formataddr

from urllib import urlencode
import xmlrpclib

from openerp import fields, api, tools
from openerp import SUPERUSER_ID
from openerp.addons.mail.mail_message import decode
from openerp.exceptions import except_orm
from openerp.osv import osv, orm
from openerp.osv.orm import BaseModel
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.exceptions import AccessError

_logger = logging.getLogger(__name__)


mail_header_msgid_re = re.compile('<[^<>]+>')


def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class mail_thread(osv.AbstractModel):
    ''' mail_thread model is meant to be inherited by any model that needs to
    act as a discussion topic on which messages can be attached. Public methods
    are prefixed with ``message_`` in order to avoid name collisions with methods
    of the models that will inherit from this class.

    ``mail.thread`` defines fields used to handle and display the communication
    history. ``mail.thread`` also manages followers of inheriting classes. All
    features and expected behavior are managed by mail.thread. Widgets has been
    designed for the 7.0 and following versions of OpenERP.

    Inheriting classes are not required to implement any method, as the default
    implementation will work for any model. However it is common to override at
    least the ``message_new`` and ``message_update`` methods (calling ``super``)
    to add model-specific behavior at creation and update of a thread when
    processing incoming emails.

    Options:

     - _mail_flat_thread=<bool>: if set to True, all messages without parent_id are
       automatically attached to the first message posted on the ressource. If set
       to False, the display of Chatter is done using threads, and no parent_id
       is automatically set.
     - _track: automatic logging using subtypes of tracked fields. This dict has
       to use the form
        _track = {
            'field': {
                'module.subtype_xml': lambda self, cr, uid, obj, context=None: obj[state] == done,
                'module.subtype_xml2': lambda self, cr, uid, obj, context=None: obj[state] != done,
            }, 'field2': {
                ...
            },
        }
        where
        :param string field: field name
        :param module.subtype_xml: xml_id of a mail.message.subtype (i.e. mail.mt_comment)
        :param obj: is a browse_record
        :param function lambda: returns whether the tracking should record using this subtype
     - _mail_mass_mailing=<string>: when using the mass_mailing module, allow performing
       mass mailing on the model, using the string as the displayed selection value.
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'

    _mail_flat_thread = True
    _mail_post_access = 'write'
    # Mass mailing feature
    _mail_mass_mailing = False

    @api.model
    def get_empty_list_help(self, help):
        """ Override of BaseModel.get_empty_list_help() to generate an help message
            that adds alias information. """
        model = self.env.context.get('empty_list_help_model')
        res_id = self.env.context.get('empty_list_help_id')
        document_name = self.env.context.get('empty_list_help_document_name', _('document'))
        catchall_domain = self.env['ir.config_parameter'].get_param('mail.catchall.domain')
        alias = None

        if catchall_domain and model:
            if res_id:  # specific res_id -> find its alias (i.e. section_id specified)
                obj_alias = self.env[model].browse(res_id).alias_id
                # check that the alias effectively creates new records
                if obj_alias.alias_name and \
                        obj_alias.alias_model_id.model == self._name and \
                        obj_alias.alias_force_thread_id == 0:
                    alias = obj_alias
            if not alias:  # no res_id or res_id not linked to an alias -> generic help message, take a generic alias of the model
                try:
                    alias = self.env['mail.alias'].search(
                        [("alias_parent_model_id.model", "=", model), ("alias_name", "!=", False), ('alias_force_thread_id', '=', False), ('alias_parent_thread_id', '=', False)]
                    ).ensure_one()
                except except_orm:
                    pass
            if alias:
                alias_email = alias.name_get()[0][1]
                return """<p class='oe_view_nocontent_create'>%(message)s</p>%(static_help)s""" % {
                    'message': _("Click here to add new %(document)s or send an email to: %(email_link)s") % {
                        'document': document_name,
                        'email_link': "<a href='mailto:{0}'>{0}</a>".format(alias_email),
                    },
                    'static_help': help or ''}

        if document_name != 'document' and help and help.find("oe_view_nocontent_create") == -1:
            return "<p class='oe_view_nocontent_create'>%(message)s</p>%(static_help)s" % {
                'message': _("Click here to add new %s") % document_name,
                'static_help': help or '',
            }

        return help

    @api.multi
    def get_message_data(self):
        """ Computes:
            - message_unread: has uid unread message for the document
            - message_summary: html snippet summarizing the Chatter for kanban views """
        res = dict((id, dict(message_unread=False, message_unread_count=0, message_summary=' ')) for id in self.ids)

        # search for unread messages, directly in SQL to improve performances
        self.env.cr.execute("""SELECT m.res_id FROM mail_message m
            RIGHT JOIN mail_notification n
            ON (n.message_id = m.id AND n.partner_id = %s AND (n.is_read = False or n.is_read IS NULL))
            WHERE m.model = %s AND m.res_id in %s""", (self.env.user.partner_id.id, self._name, tuple(self.ids),))
        for result in self.env.cr.fetchall():
            res[result[0]]['message_unread'] = True
            res[result[0]]['message_unread_count'] += 1

        # for id in ids:
        #     if res[id]['message_unread_count']:
        #         title = res[id]['message_unread_count'] > 1 and _("You have %d unread messages") % res[id]['message_unread_count'] or _("You have one unread message")
        #         res[id]['message_summary'] = "<span class='oe_kanban_mail_new' title='%s'><i class='fa fa-comments'/> %d</span>" % (title, res[id].pop('message_unread_count'))
        #     res[id].pop('message_unread_count', None)
        # return res
        for rec in self:
            if res[rec.id]['message_unread_count']:
                res[rec.id]['message_summary'] = "<span class='oe_kanban_mail_new' title='%s'><span class='oe_e'>9</span> %d %s</span>" % (
                    ("You have %d unread message(s)") % res[rec.id]['message_unread_count'], res[rec.id].pop('message_unread_count'), _("New"))
            rec.message_unread = res[rec.id]['message_unread']
            rec.message_summary = res[rec.id]['message_summary']

    def read_followers_data(self, cr, uid, follower_ids, context=None):
        # result = []
        # technical_group = self.pool.get('ir.model.data').get_object(cr, uid, 'base', 'group_no_one', context=context)
        # for follower in self.pool.get('res.partner').browse(cr, uid, follower_ids, context=context):
        #     is_editable = uid in map(lambda x: x.id, technical_group.users)
        #     is_uid = uid in map(lambda x: x.id, follower.user_ids)
        #     data = (follower.id,
        #             follower.name,
        #             {'is_editable': is_editable, 'is_uid': is_uid},
        #             )
        #     result.append(data)
        # return result
        is_editable = self.env.ref('base.group_no_one') in self.env.user.groups_id
        return [(fol.id, fol.name, {'is_editable': is_editable, 'is_uid': self.env.user.partner_id == fol})
                for fol in self.env['res.partner'].browse(follower_ids)]

    def _get_subscription_data(self, cr, uid, ids, name, args, user_pid=None, context=None):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        # res = dict((id, dict(message_subtype_data='')) for id in ids)
        # if user_pid is None:
        #     user_pid = self.pool.get('res.users').read(cr, uid, [uid], ['partner_id'], context=context)[0]['partner_id'][0]
        if partner_id is None:
            partner_id = self.env.user.partner_id.id

        # find current model subtypes, add them to a dictionary
        subtypes = self.env['mail.message.subtype'].search(['&', ('hidden', '=', False), '|', ('res_model', '=', self._name), ('res_model', '=', False)])
        subtype_dict = OrderedDict(
            (subtype.name, {
                'default': subtype.default,
                'followed': False,
                'parent_model': subtype.parent_id and subtype.parent_id.res_model or self._name,
                'id': subtype.id
            }) for subtype in subtypes)
        res = dict((id, subtype_dict.copy()) for id in self.ids)

        # find the document followers, update the data
        followers = self.env['mail.followers'].search([
            ('partner_id', '=', partner_id),
            ('res_id', 'in', self.ids),
            ('res_model', '=', self._name)])
        for fol in followers:
            for subtype in [st for st in fol.subtype_ids if st.name in res[fol.res_id]]:
                res[fol.res_id][st.name]['followed'] = True

        return res

    def _search_message_unread(self, operator, value):
        return [('message_ids.to_read', operator, value)]

    @api.multi
    def get_followers(self):
        fols = self.sudo().env['mail.followers'].search([('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        res = dict((rec.id, dict(message_follower_ids=[], message_is_follower=False)) for rec in self)
        for fol in fols:
            res[fol.res_id]['message_follower_ids'].append(fol.partner_id.id)
            if fol.partner_id == self.env.user.partner_id:
                res[fol.res_id]['message_is_follower'] = True
        for rec in self:
            rec.message_is_follower = res[rec.id]['message_is_follower']
            print res[rec.id]['message_follower_ids']
            rec.message_follower_ids = res[rec.id]['message_follower_ids']

    @api.multi
    def set_followers(self):
        # read the old set of followers, and determine the new set of followers
        fols = self.sudo().env['mail.followers'].search([('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        old_dict = dict.fromkeys(self.ids, self.env['res.partner'])
        for fol in fols:
            old_dict[fol.res_id] += fol.partner_id
        for record in self:
            old = old_dict[record.id]
            new = record.message_follower_ids
            # remove partners that are no longer followers
            record.message_unsubscribe([p.id for p in old-new])
            # add new followers
            record.message_subscribe([p.id for p in new-old])

    def search_followers(self, operator, value):
        # TDE TODO: check with 'not in' operator
        followers = self.sudo().env['mail.followers'].search([('res_model', '=', self._name), ('partner_id', operator, value)])
        return [('id', 'in', [fol.res_id for fol in followers])]

    def search_is_follower(self, operator, value):
        partner_id = self.env.user.partner_id.id
        if (operator == '=' and value) or (operator == '!=' and not value):  # is a follower
            return [('message_follower_ids', 'in', [partner_id])]
        else:  # is not a follower or unknown domain
            return [('message_follower_ids', 'not in', [partner_id])]

    message_follower_ids = fields.Many2many(
        'res.partner', string='Followers',
        compute='get_followers', inverse='set_followers', search='search_followers'
    )
    message_is_follower = fields.Boolean(
        string='Is a Follower',
        compute='get_followers', search='search_is_follower'
    )
    message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name)],
        auto_join=True,
        string='Messages',
        help="Messages and communication history"
    )
    message_last_post = fields.Datetime('Last Message Date', help='Date of the last message posted on the record.')
    message_unread = fields.Boolean(
        string='Unread Messages',
        compute='get_message_data', search='_search_message_unread',
        help="If checked new messages require your attention."
    )
    message_summary = fields.Text(
        string='Summary',
        compute='get_message_data',
        help="Holds the Chatter summary (number of messages, ...). This summary is directly in html format in order to be inserted in kanban views."
    )

    @api.model
    def _get_user_chatter_options(self):
        return {'display_log_button': self.env.ref('base.group_user') in self.env.user.groups_id}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(mail_thread, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']"):
                options = json.loads(node.get('options', '{}'))
                options.update(self._get_user_chatter_options())
                node.set('options', json.dumps(options))
            res['arch'] = etree.tostring(doc)
        return res

    #------------------------------------------------------
    # CRUD overrides for automatic subscription and logging
    #------------------------------------------------------

    @api.model
    def create(self, values):
        """ Chatter override :
            - subscribe uid
            - subscribe followers of parent
            - log a creation message
        """
        if self.env.context.get('tracking_disable'):
            return super(mail_thread, self).create(values)

        # subscribe uid unless asked not to
        if not self.env.context.get('mail_create_nosubscribe'):
            message_follower_ids = values.get('message_follower_ids') or []  # webclient can send None or False
            message_follower_ids.append([4, self.env.user.partner_id.id])
            values['message_follower_ids'] = message_follower_ids
        thread_id = super(mail_thread, self).create(values)

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not self.env.context.get('mail_create_nolog'):
            ir_model_pool = self.pool['ir.model']
            ids = ir_model_pool.search(self.env.cr, self.env.uid, [('model', '=', self._name)], context=self.env.context)
            name = ir_model_pool.read(self.env.cr, self.env.uid, ids, ['name'], context=self.env.context)[0]['name']
            # self.message_post(thread_id.id, body=_('%s created') % name)  # TDE FIXIME: check message post arguments

        # auto_subscribe: take values and defaults into account
        create_values = dict((key[8:], val) for key, val in self.env.context.iteritems() if key.startswith('default_'), **values)
        # self.message_auto_subscribe(self.env.cr, self.env.user.id, [thread_id], create_values.keys(), context=self.env.context, values=create_values)

        # track values
        # if not self.env.context.get('mail_notrack'):
        #     track_ctx = dict(self.env.context)
        #     if 'lang' not in track_ctx:
        #         track_ctx['lang'] = self.env.user.lang
        #     tracked_fields = self._get_tracked_fields(self.env.cr, self.env.uid, values.keys(), context=track_ctx)
        #     if tracked_fields:
        #         initial_values = {thread_id: dict.fromkeys(tracked_fields, False)}
        #         self.message_track(self.env.cr, self.env.uid, [thread_id], tracked_fields, initial_values, context=track_ctx)
        return thread_id

    @api.multi
    def write(self, values):
        if self.env.context.get('tracking_disable'):
            return super(mail_thread, self).write(values)

        # if not self.env.context.get('mail_notrack'):
        #     track_ctx = dict(self.env.context)
        #     if 'lang' not in track_ctx:
        #         track_ctx['lang'] = self.env.user.lang
        #     tracked_fields = self._get_tracked_fields(values.keys(), context=track_ctx)
        #     if tracked_fields:
        #         initial_values = dict((record.id, dict((key, getattr(record, key)) for key in tracked_fields))
        #                               for record in self)  # todo: rebrowse in lang ?

        # Perform write, update followers
        result = super(mail_thread, self).write(values)
        # self.message_auto_subscribe(values.keys(), values=values)

        # # Perform the tracking
        # if not self.env.context.get('mail_notrack') and tracked_fields:
        #     self.message_track(tracked_fields, initial_values, context=track_ctx)

        return result

    @api.multi
    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
            cascaded, because link is done through (res_model, res_id). """
        self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        res = super(mail_thread, self).unlink()
        self.env['mail.followers'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        return res

    @api.cr_uid_id_context
    def copy_data(self, default=None):
        # avoid tracking multiple temporary changes during copy
        context = dict(self.env.context or {}, mail_notrack=True)
        return super(mail_thread, self).copy_data(default=default, context=context)

    #------------------------------------------------------
    # Automatically log tracked fields
    #------------------------------------------------------

    @api.model
    def _get_tracked_fields(self, updated_fields):
        """ Return a fields_get of the tracked fields. This list is based on
        updated field to match the track_visibility parameter.

        :param list updated_fields: modified field names
        :return dict: the result of fields_get on the tracked fields (or void)
        """
        tracked_fields = []
        for name, field in self._fields.items():
            if getattr(field, 'track_visibility', False):
                tracked_fields.append(name)

        if tracked_fields:
            return self.fields_get(tracked_fields)
        return {}


    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        """ Give the subtypes triggered by the changes on the record according
        to values that have been updated.

        :param ids: list of a single ID, the ID of the record being modified
        :type ids: singleton list
        :param init_values: the original values of the record; only modified fields
                            are present in the dict
        :type init_values: dict
        :returns: a subtype xml_id or False if no subtype is trigerred
        """
        return False

    @api.multi
    def message_track(self, tracked_fields, initial_values):

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

        def format_message(description, tracked_values):
            message = description and '<span>%s</span>' % description or ''
            for name, change in tracked_values.items():
                message += '<div> &nbsp; &nbsp; &bull; <b>%(col_info)s</b>: %(old_value)s%(new_value)s</div>' % {
                    'col_info': change.get('col_info'),
                    'old_value': change.get('old_value') and '%s &rarr; ' % change.get('old_value') or '',
                    'new_value': change.get('new_value')
                }
            return message

        if not tracked_fields:
            return True

        for record in self:
            changes = set()
            tracked_values = {}

            # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
            # for col_name, col_info in tracked_fields.items():
# <<<<<<< HEAD
#                 field = self._fields[col_name]
#                 initial_value = initial[col_name]
#                 record_value = getattr(browse_record, col_name)

#                 if record_value == initial_value and getattr(field, 'track_visibility', None) == 'always':
#                     tracked_values[col_name] = dict(
#                         col_info=col_info['string'],
#                         new_value=convert_for_display(record_value, col_info),
#                     )
#                 elif record_value != initial_value and (record_value or initial_value):  # because browse null != False
#                     if getattr(field, 'track_visibility', None) in ['always', 'onchange']:
#                         tracked_values[col_name] = dict(
#                             col_info=col_info['string'],
#                             old_value=convert_for_display(initial_value, col_info),
#                             new_value=convert_for_display(record_value, col_info),
#                         )
# =======
#                 initial_value = initial_values[record.id][col_name]
#                 record_value = getattr(record, col_name)
#                 column = self._all_columns[col_name].column
#                 if record_value == initial_value and getattr(column, 'track_visibility', None) == 'always':
#                     tracked_values[col_name] = dict(col_info=col_info['string'],
#                                                     new_value=convert_for_display(record_value, col_info))
#                 elif record_value != initial_value and (record_value or initial_value):  # because browse null != False
#                     if getattr(column, 'track_visibility', None) in ['always', 'onchange']:
#                         tracked_values[col_name] = dict(col_info=col_info['string'],
#                                                         old_value=convert_for_display(initial_value, col_info),
#                                                         new_value=convert_for_display(record_value, col_info))
# >>>>>>> [WIP] Migrate
#                     if col_name in tracked_fields:
#                         changes.add(col_name)
#             if not changes:
#                 continue

#             # find subtypes and post messages or log if no subtype found
# <<<<<<< HEAD
#             subtype_xmlid = False
#             # By passing this key, that allows to let the subtype empty and so don't sent email because partners_to_notify from mail_message._notify will be empty
#             if not context.get('mail_track_log_only'):
#                 subtype_xmlid = browse_record._track_subtype(dict((col_name, initial[col_name]) for col_name in changes))
#                 # compatibility: use the deprecated _track dict
#                 if not subtype_xmlid and hasattr(self, '_track'):
#                     for field, track_info in self._track.items():
#                         if field not in changes or subtype_xmlid:
#                             continue
#                         for subtype, method in track_info.items():
#                             if method(self, cr, uid, browse_record, context):
#                                 _logger.warning("Model %s still using deprecated _track dict; override _track_subtype method instead" % self._name)
#                                 subtype_xmlid = subtype

#             if subtype_xmlid:
#                 subtype_rec = self.pool['ir.model.data'].xmlid_to_object(cr, uid, subtype_xmlid, context=context)
# =======
#             subtypes = []
#             for field, track_info in self._track.items():
#                 if field not in changes:
#                     continue
#                 subtypes = [subtype for subtype, method in track_info.items() if method(self, self.env.cr, self.env.uid, record, self.env.context)]

#             posted = False
#             for subtype in subtypes:
#                 subtype_rec = self.env.ref(subtype)
# >>>>>>> [WIP] Migrate
#                 if not (subtype_rec and subtype_rec.exists()):
#                     _logger.debug('subtype %s not found' % subtype_xmlid)
#                     continue
#                 message = format_message(subtype_rec.description if subtype_rec.description else subtype_rec.name, tracked_values)
# <<<<<<< HEAD
#             else:
#                 message = format_message('', tracked_values)
#             self.message_post(cr, uid, browse_record.id, body=message, subtype=subtype_xmlid, context=context)
# =======
#                 # record.message_post(body=message, subtype=subtype)
#                 posted = True
#             if not posted:
#                 message = format_message('', tracked_values)
#                 # record.message_post(body=message)
# >>>>>>> [WIP] Migrate
        return True

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    @api.model
    def _needaction_domain_get(self):
        if self._needaction:
            return [('message_unread', '=', True)]
        return []

    @api.model
    def _garbage_collect_attachments(self):
        """ Garbage collect lost mail attachments. Those are attachments
            - linked to res_model 'mail.compose.message', the composer wizard
            - with res_id 0, because they were created outside of an existing
                wizard (typically user input through Chatter or reports
                created on-the-fly by the templates)
            - unused since at least one day (create_date and write_date)
        """
        limit_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        limit_date_str = datetime.datetime.strftime(limit_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        IrAttachment = self.env['ir.attachment']
        return IrAttachment.search([
            ('res_model', '=', 'mail.compose.message'),
            ('res_id', '=', 0),
            ('create_date', '<', limit_date_str),
            ('write_date', '<', limit_date_str)]).unlink()

    @api.model
    def check_mail_message_access(self, mids, operation, model=None):
        """ mail.message check permission rules for related document. This method is
            meant to be inherited in order to implement addons-specific behavior.
            A common behavior would be to allow creating messages when having read
            access rule on the document, for portal document such as issues. """
        model_obj = self
        if model:
            model_obj = self.env[model]
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

        model_obj.check_access_rights(check_operation)
        model_obj.check_access_rule(mids, check_operation)

    @api.model
    def _get_inbox_action_xml_id(self):
        """ When redirecting towards the Inbox, choose which action xml_id has
            to be fetched. This method is meant to be inherited, at least in portal
            because portal users have a different Inbox action than classic users. """
        return ('mail', 'action_mail_inbox_feeds')

    @api.model
    def message_redirect_action(self):
        """ For a given message, return an action that either
            - opens the form view of the related document if model, res_id, and
              read access to the document
            - opens the Inbox with a default search on the conversation if model,
              res_id
            - opens the Inbox with context propagated

        """
        # default action is the Inbox action
        act_model, act_id = self.env['ir.model.data'].get_object_reference(*self._get_inbox_action_xml_id())
        action = self.env[act_model].read(self.env.cr, self.env.uid, [act_id], [])[0]
        params = self.env.context.get('params')
        msg_id = model = res_id = None

        if params:
            msg_id = params.get('message_id')
            model = params.get('model')
            res_id = params.get('res_id', params.get('id'))  # signup automatically generated id instead of res_id
        if not msg_id and not (model and res_id):
            return action
        if msg_id and not (model and res_id):
            msg = self.pool.get('mail.message').browse(cr, uid, msg_id, context=context).exists()
            try:
                model, res_id = msg.model, msg.res_id
            except AccessError:
                pass

        # if model + res_id found: try to redirect to the document or fallback on the Inbox
        if model and res_id:
            model_obj = self.pool.get(model)
            if model_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
                try:
                    model_obj.check_access_rule(cr, uid, [res_id], 'read', context=context)
                    action = model_obj.get_access_action(cr, uid, res_id, context=context)
                except AccessError:
                    pass
            action.update({
                'context': {
                    'search_default_model': model,
                    'search_default_res_id': res_id,
                }
            })
        return action

    @api.model
    def _get_access_link(self, mail, partner):
        # the parameters to encode for the query and fragment part of url
        query = {'db': self.env.cr.dbname}
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

    @api.multi
    def message_get_default_recipients(self):
        context = self.env.context
        if context and context.get('thread_model') and context['thread_model'] in self.pool and context['thread_model'] != self._name:
            if hasattr(self.pool[context['thread_model']], 'message_get_default_recipients'):
                model_env = self.env[context['thread_model']]
                model_env.context = dict(context)
                model_env.context.pop('thread_model')
                return model_env.message_get_default_recipients()
        res = {}
        for record in self:
            recipient_ids, email_to, email_cc = set(), False, False
            if 'partner_id' in self._fields and record.partner_id:
                recipient_ids.add(record.partner_id.id)
            elif 'email_from' in self._fields and record.email_from:
                email_to = record.email_from
            elif 'email' in self._fields:
                email_to = record.email
            res[record.id] = {'partner_ids': list(recipient_ids), 'email_to': email_to, 'email_cc': email_cc}
        return res

    @api.multi
    def message_get_reply_to(self, default=None):
        """ Returns the preferred reply-to email address that is basically
            the alias of the document, if it exists. """
        model_name = self.env.context.get('thread_model') or self._name
        alias_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
        res = dict.fromkeys(self.ids, False)

        # alias domain: check for aliases and catchall
        aliases = {}
        doc_names = {}
        if alias_domain:
            if model_name and model_name != 'mail.thread':
                Alias = self.env['mail.alias'].sudo()
                alias_ids = Alias.search([
                    ('alias_parent_model_id.model', '=', model_name),
                    ('alias_parent_thread_id', 'in', self.ids),
                    ('alias_name', '!=', False)])
                aliases.update(
                    dict((alias.alias_parent_thread_id, '%s@%s' % (alias.alias_name, alias_domain))
                         for alias in Alias.browse(alias_ids)))
                doc_names.update(
                    dict((ng_res[0], ng_res[1])
                         for ng_res in self.env[model_name].sudo().name_get(aliases.keys())))
            # left ids: use catchall
            left_ids = set(self.ids).difference(set(aliases.keys()))
            if left_ids:
                catchall_alias = self.env['ir.config_parameter'].get_param("mail.catchall.alias")
                if catchall_alias:
                    aliases.update(dict((res_id, '%s@%s' % (catchall_alias, alias_domain)) for res_id in left_ids))
            # compute name of reply-to
# <<<<<<< HEAD
#             company_name = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).company_id.name
#             for res_id in aliases.keys():
#                 email_name = '%s%s' % (company_name, doc_names.get(res_id) and (' ' + doc_names[res_id]) or '')
#                 email_addr = aliases[res_id]
#                 res[res_id] = formataddr((email_name, email_addr))
#         left_ids = set(ids).difference(set(aliases.keys()))
# =======
#             res.update(
#                 dict((res_id, '"%(company_name)s%(document_name)s" <%(email)s>' %
#                      {'company_name': self.env.user.company_id.name,
#                       'document_name': doc_names.get(res_id) and ' ' + re.sub(r'[^\w+.]+', '-', doc_names[res_id]) or '',
#                       'email': aliases[res_id]
#                       } or False) for res_id in aliases.keys()))
#         left_ids = set(self.ids).difference(set(aliases.keys()))
# >>>>>>> [WIP] migrate
        if left_ids and default:
            res.update(dict((res_id, default) for res_id in left_ids))
        return res

    @api.multi
    def message_get_email_values(self, messages=None):
        """ Get specific notification email values to store on the notification
        mail_mail. Void method, inherit it to add custom values. """
        return dict.fromkeys(self.ids, dict())

    #------------------------------------------------------
    # Mail gateway
    #------------------------------------------------------

    def _message_find_partners(self, message, header_fields=['From']):
        """ Find partners related to some header fields of the message.

            :param string message: an email.message instance """
        s = ', '.join([decode(message.get(h)) for h in header_fields if message.get(h)])
        return filter(lambda x: x, self._find_partner_from_emails(None, tools.email_split(s)))

    def message_route_verify(self, message, message_dict, route, update_author=True, assert_model=True, create_fallback=True, allow_private=False):
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

        def _create_bounce_email():
            mail_mail_id = self.env['mail.mail'].create({
                'body_html': '<div><p>Hello,</p>'
                             '<p>The following email sent to %s cannot be accepted because this is '
                             'a private email address. Only allowed people can contact us at this address.</p></div>'
                             '<blockquote>%s</blockquote>' % (message.get('to'), message_dict.get('body')),
                'subject': 'Re: %s' % message.get('subject'),
                'email_to': message.get('from'),
                'auto_delete': True})
            self.env['mail.mail'].send([mail_mail_id])

        def _warn(message):
            _logger.info('Routing mail with Message-Id %s: route %s: %s',
                                message_id, route, message)

        # Wrong model
        if model and not model in self.pool:
            if assert_model:
                assert model in self.pool, 'Routing: unknown target model %s' % model
            _warn('unknown target model %s' % model)
            return ()

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
        route_env = self.env[model]
        if thread_id and not route_env.exists(thread_id):
            if create_fallback:
                _warn('reply to missing document (%s,%s), fall back on new document creation' % (model, thread_id))
                thread_id = None
            elif assert_model:
                assert route_env.exists(thread_id), 'Routing: reply to missing document (%s,%s)' % (model, thread_id)
            else:
                _warn('reply to missing document (%s,%s), skipping' % (model, thread_id))
                return ()

        # Existing Document: check model accepts the mailgateway
        if thread_id and model and not hasattr(route_env, 'message_update'):
            if create_fallback:
                _warn('model %s does not accept document update, fall back on document creation' % model)
                thread_id = None
            elif assert_model:
                assert hasattr(route_env, 'message_update'), 'Routing: model %s does not accept document update, crashing' % model
            else:
                _warn('model %s does not accept document update, skipping' % model)
                return ()

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(route_env, 'message_new'):
            if assert_model:
                if not hasattr(route_env, 'message_new'):
                    raise ValueError(
                        'Model %s does not accept document creation, crashing' % model
                    )
            _warn('model %s does not accept document creation, skipping' % model)
            return ()

        # Update message author if asked
        # We do it now because we need it for aliases (contact settings)
        if not author_id and update_author:
            author_ids = self._find_partner_from_emails(thread_id, [email_from], model=model)
            if author_ids:
                author_id = author_ids[0]
                message_dict['author_id'] = author_id

        # Alias: check alias_contact settings
        if alias and alias.alias_contact == 'followers' and (thread_id or alias.alias_parent_thread_id):
            if thread_id:
                obj = route_env.browse(thread_id)
            else:
                obj = self.env[alias.alias_parent_model_id.model].browse(alias.alias_parent_thread_id)
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

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
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
        MailMessage = self.env['mail.message']
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
        msg_references = mail_header_msgid_re.findall(thread_references)
        ref_messages = MailMessage.search([('message_id', 'in', msg_references)], limit=1)  # TDE FIXME: search limit=1 in 8
        if ref_match and ref_messages:
            model, thread_id = ref_messages[0].model, ref_messages[0].res_id
            route = self.message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, None),
                update_author=True, assert_model=False, create_fallback=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
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
                    model_obj = self.env[model]
                    compat_ref_messages = MailMessage.search([
                        ('message_id', '=', False),
                        ('model', '=', model),
                        ('res_id', '=', thread_id)], limit=1)  # TDE FIXME: search limit=1 in 8
                    if compat_ref_messages and model_obj.exists(thread_id) and hasattr(model_obj, 'message_update'):
                        route = self.message_route_verify(
                            message, message_dict,
                            (model, thread_id, custom_values, self._uid, None),
                            update_author=True, assert_model=True, create_fallback=True)
                        if route:
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct thread reply (compat-mode) to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                                email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                            return [route]

        # 3. Reply to a private message
        if in_reply_to:
            ref_messages = MailMessage.search([
                ('message_id', '=', in_reply_to),
                '!', ('message_id', 'ilike', 'reply_to')], limit=1)
            if ref_messages:
                route = self.message_route_verify(
                    message, message_dict,
                    (ref_messages[0].model, ref_messages[0].res_id, custom_values, self._uid, None),
                    update_author=True, assert_model=True, create_fallback=True, allow_private=True)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct reply to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, ref_messages[0].id, custom_values, self._uid)
                    return [route]

        # 4. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = ','.join([
            decode_header(message, 'Delivered-To'),
            decode_header(message, 'To'),
            decode_header(message, 'Cc'),
            decode_header(message, 'Resent-To'),
            decode_header(message, 'Resent-Cc')])
        local_parts = [e.split('@')[0] for e in tools.email_split(rcpt_tos)]
        if local_parts:
            Alias = self.env['mail.alias']
            aliases = Alias.search([('alias_name', 'in', local_parts)])
            if aliases:
                routes = []
                for alias in aliases:
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(cr, uid, message, context=context)
                        user_id = self._uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, eval(alias.alias_defaults), user_id, alias)
                    route = self.message_route_verify(
                        message, message_dict, route,
                        update_author=True, assert_model=True, create_fallback=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 5. Fallback to the provided parameters, if they work
        if not thread_id:
            # Legacy: fallback to matching [ID] in the Subject
            match = tools.res_re.search(decode_header(message, 'Subject'))
            thread_id = match and match.group(1)
            # Convert into int (bug spotted in 7.0 because of str)
            try:
                thread_id = int(thread_id)
            except:
                thread_id = False
        route = self.message_route_verify(
            message, message_dict,
            (fallback_model, thread_id, custom_values, self._uid, None),
            update_author=True, assert_model=True)
        if route:
            _logger.info(
                'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                email_from, email_to, message_id, fallback_model, thread_id, custom_values, self._uid)
            return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id))

    @api.model
    def message_route_process(self, message, message_dict, routes):
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes:
            if self._name == 'mail.thread':
                context['thread_model'] = model
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
            # new_msg_id = model_pool.message_post(cr, uid, [thread_id], context=context, subtype='mail.mt_comment', **message_dict)

            if partner_ids:
                # postponed after message_post, because this is an external message and we don't want to create
                # duplicate emails due to notifications
                self.pool.get('mail.message').write(cr, uid, [new_msg_id], {'partner_ids': partner_ids}, context=context)
        return thread_id

    @api.model
    def message_process(self, model, message, custom_values=None, save_original=False,
                        strip_attachments=False, thread_id=None):
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
        msg = self.message_parse(msg_txt, save_original=save_original)
        if strip_attachments:
            msg.pop('attachments', None)

        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg.get('message_id'))], limit=1)
            if existing_msg_ids:
                _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                             msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False

        # find possible routes for the message
        routes = self.message_route(msg_txt, msg, model, thread_id, custom_values)
        thread_id = self.message_route_process(msg_txt, msg, routes)
        return thread_id

    @api.model
    def message_new(self, msg_dict, custom_values=None):
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
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        model = self._context.get('thread_model') or self._name
        model_pool = self.pool[model]
        fields = model_pool.fields_get()
        if 'name' in fields and not data.get('name'):
            data['name'] = msg_dict.get('subject', '')
        res_id = model_pool.create(data)
        return res_id  # TDE FIXME: check for returns

    @api.multi
    def message_update(self, msg_dict, update_vals=None):
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
            self.write(update_vals)
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
            mixed = False
            html = u''
            for part in message.walk():
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_type() == 'multipart/mixed':
                    mixed = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                # part.get_filename returns decoded value if able to decode, coded otherwise.
                # original get_filename is not able to decode iso-8859-1 (for instance).
                # therefore, iso encoded attachements are not able to be decoded properly with get_filename
                # code here partially copy the original get_filename method, but handle more encoding
                filename = part.get_param('filename', None, 'content-disposition')
                if not filename:
                    filename = part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        # RFC2231
                        filename = email.utils.collapse_rfc2231_value(filename).strip()
                    else:
                        filename = decode(filename)
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
                    # mutlipart/alternative have one text and a html part, keep only the second
                    # mixed allows several html parts, append html content
                    append_content = not alternative or (html and mixed)
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if not append_content:
                        body = html
                    else:
                        body = tools.append_content_to_html(body, html, plaintext=False)
                # 4) Anything else -> attachment
                else:
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
        return body, attachments

    @api.model
    def message_parse(self, message, save_original=False):
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
        partner_ids = self._message_find_partners(message, ['To', 'Cc'])
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
                _logger.info('Failed to parse Date header %r in incoming mail '
                                'with message-id %r, assuming current date/time.',
                                message.get('Date'), message_id)
                stored_date = datetime.datetime.now()
            msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        if message.get('In-Reply-To'):
            parent_ids = self.env['mail.message'].search([('message_id', '=', decode(message['In-Reply-To'].strip()))], limit=1)  # TDE FIXME in 8: limit=1
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0].id

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list = mail_header_msgid_re.findall(decode(message['References']))
            parent_ids = self.env['mail.message'].search([('message_id', 'in', [x.strip() for x in msg_list])], limit=1)  # TDE FIXME in 8: limit=1
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0].id

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        return msg_dict

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    @api.model
    # TDE FIXME: check correct decorator / id / ids ?
    def _message_add_suggested_recipient(self, result, obj, partner=None, email=None, reason=''):
        """ Called by message_get_suggested_recipients, to add a suggested
            recipient in the result dictionary. The form is :
                partner_id, partner_name<partner_email> or partner_name, reason """
        if email and not partner:
            # get partner info from email
            partner_info = self.message_partner_info_from_emails(obj.id, [email])[0]
            if partner_info.get('partner_id'):
                partner = self.env['res.partner'].sudo().browse([partner_info['partner_id']])[0]
        if email and email in [val[1] for val in result[obj.id]]:  # already existing email -> skip
            return result
        if partner and partner in obj.message_follower_ids:  # recipient already in the followers -> skip
            return result
        if partner and partner.id in [val[0] for val in result[obj.id]]:  # already existing partner ID -> skip
            return result
        if partner and partner.email:  # complete profile: id, name <email>
            result[obj.id].append((partner.id, '%s<%s>' % (partner.name, partner.email), reason))
        elif partner:  # incomplete profile: id, name
            result[obj.id].append((partner.id, '%s' % (partner.name), reason))
        else:  # unknown partner, we are probably managing an email address
            result[obj.id].append((False, email, reason))
        return result

# <<<<<<< HEAD
#     def message_get_suggested_recipients(self, cr, uid, ids, context=None):
#         """ Returns suggested recipients for ids. Those are a list of
#             tuple (partner_id, partner_name, reason), to be managed by Chatter. """
#         result = dict((res_id, []) for res_id in ids)
#         if 'user_id' in self._fields:
#             for obj in self.browse(cr, SUPERUSER_ID, ids, context=context):  # SUPERUSER because of a read on res.users that would crash otherwise
#                 if not obj.user_id or not obj.user_id.partner_id:
#                     continue
#                 self._message_add_suggested_recipient(cr, uid, result, obj, partner=obj.user_id.partner_id, reason=self._fields['user_id'].string, context=context)
# =======
#     @api.multi
#     def message_get_suggested_recipients(self):
#         """ Returns list of tuple (partner_id, partner_name, reason) for each record """
#         result = dict((res_id, []) for res_id in self.ids)
#         if self._all_columns.get('user_id'):
#             for obj in self.sudo():  # SUPERUSER because of a read on res.users that would crash otherwise
#                 if not obj.user_id or not obj.user_id.partner_id:
#                     continue
#                 self._message_add_suggested_recipient(result, obj, partner=obj.user_id.partner_id, reason=self._all_columns['user_id'].column.string)
# >>>>>>> [WIP] Migrate
#         return result

    @api.model
    # TDE FIXME: check correct decorator / id / ids ?
    def _find_partner_from_emails(self, id, emails, model=None, check_followers=True):
        """ Utility method to find partners from email addresses. The rules are :
            1 - check in document (model | self, id) followers
            2 - try to find a matching partner that is also an user
            3 - try to find a matching partner

            :param list emails: list of email addresses
            :param string model: model to fetch related record; by default self
                is used.
            :param boolean check_followers: check in document followers
        """
        Partner = self.env['res.partner'].sudo()
        partner_ids = []
        obj = None
        if id and (model or self._name != 'mail.thread') and check_followers:
            if model:
                obj = self.env[model].browse(id)
            else:
                obj = self.browse(id)
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
            # Escape special SQL characters in email_address to avoid invalid matches
            email_address = (email_address.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_'))
            email_brackets = "<%s>" % email_address
            # if not partner_id:
# <<<<<<< HEAD
#                 # exact, case-insensitive match
#                 ids = partner_obj.search(cr, SUPERUSER_ID,
#                                          [('email', '=ilike', email_address),
#                                           ('user_ids', '!=', False)],
#                                          limit=1, context=context)
#                 if not ids:
#                     # if no match with addr-spec, attempt substring match within name-addr pair
#                     ids = partner_obj.search(cr, SUPERUSER_ID,
#                                              [('email', 'ilike', email_brackets),
#                                               ('user_ids', '!=', False)],
#                                              limit=1, context=context)
#                 if ids:
#                     partner_id = ids[0]
#             # third try: check in partners
#             if not partner_id:
#                 # exact, case-insensitive match
#                 ids = partner_obj.search(cr, SUPERUSER_ID,
#                                          [('email', '=ilike', email_address)],
#                                          limit=1, context=context)
#                 if not ids:
#                     # if no match with addr-spec, attempt substring match within name-addr pair
#                     ids = partner_obj.search(cr, SUPERUSER_ID,
#                                              [('email', 'ilike', email_brackets)],
#                                              limit=1, context=context)
#                 if ids:
#                     partner_id = ids[0]
# =======
#                 partners = Partner.search([('email', 'ilike', email_address), ('user_ids', '!=', False)], limit=1)
#                 if partners:
#                     partner_id = partners[0].id
#             # third try: check in partners
#             if not partner_id:
#                 partners = Partner.search([('email', 'ilike', email_address)], limit=1)
#                 if partners:
#                     partner_id = partners[0].id
# >>>>>>> [WIP] Migrate
            partner_ids.append(partner_id)
        return partner_ids

    @api.model
    # TDE FIXME: check correct decorator / id / ids ? id can be None I think
    def message_partner_info_from_emails(self, id, emails, link_mail=False):
        """ Convert a list of emails into a list partner_ids and a list
            new_partner_ids. The return value is non conventional because
            it is meant to be used by the mail widget.

            :return dict: partner_ids and new_partner_ids """
        Message = self.env['mail.message'].sudo()
        partner_ids = self._find_partner_from_emails(id, emails)
        result = list()
        for idx in range(len(emails)):
            email_address = emails[idx]
            partner_id = partner_ids[idx]
            partner_info = {'full_name': email_address, 'partner_id': partner_id}
            result.append(partner_info)
            # link mail with this from mail to the new partner id
#             if link_mail and partner_info['partner_id']:
# <<<<<<< HEAD
#                 # Escape special SQL characters in email_address to avoid invalid matches
#                 email_address = (email_address.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_'))
#                 email_brackets = "<%s>" % email_address
#                 message_ids = mail_message_obj.search(cr, SUPERUSER_ID, [
#                                     '|',
#                                     ('email_from', '=ilike', email_address),
#                                     ('email_from', 'ilike', email_brackets),
#                                     ('author_id', '=', False)
#                                 ], context=context)
#                 if message_ids:
#                     mail_message_obj.write(cr, SUPERUSER_ID, message_ids, {'author_id': partner_info['partner_id']}, context=context)
# =======
#                 messages = Message.search([
#                     '|', ('email_from', '=', email_address),
#                     ('email_from', 'ilike', '<%s>' % email_address),
#                     ('author_id', '=', False)])
#                 if messages:
#                     messages.write({'author_id': partner_info['partner_id']})
# >>>>>>> [WIP] Migrate
        return result

    @api.model
    def _message_preprocess_attachments(self, attachments, attachment_ids, attach_model, attach_res_id):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``,
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param str attach_model: the model of the attachments parent record
        :param integer attach_res_id: the id of the attachments parent record
        """
        Attachment = self.env['ir.attachment'].sudo()
        m2m_attachment_ids = []
        if attachment_ids:
            filtered_attachments = Attachment.search([
                ('res_model', '=', 'mail.compose.message'),
                ('create_uid', '=', self._uid),
                ('id', 'in', attachment_ids)])
            if filtered_attachments:
                filtered_attachments.write({'res_model': attach_model, 'res_id': attach_res_id})
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

    @api.model
    def message_post(self, thread_id=None, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None,
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
        if attachments is None:
            attachments = {}
        mail_message = self.env['mail.message']

#         assert (not thread_id) or \
# <<<<<<< HEAD
#                 isinstance(thread_id, (int, long)) or \
#                 (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
#                 "Invalid thread_id; should be 0, False, an ID or a list with one ID"
#         if thread_id and isinstance(thread_id, (list, tuple)):
# =======
#             isinstance(thread_id, (int, long)) or \
#             (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
#             "Invalid thread_id; should be 0, False, an ID or a list with one ID"
#         if isinstance(thread_id, (list, tuple)):
# >>>>>>> [WIP] Migrate
            # thread_id = thread_id[0]

        # if we're processing a message directly coming from the gateway, the destination model was
        # set in the context.
        model = False
        if thread_id:
            model = self._context.get('thread_model', False) if self._name == 'mail.thread' else self._name
            if model and model != self._name and hasattr(self.pool[model], 'message_post'):
                new_ctx = dict(self._context)
                new_ctx.pop('thread_model', None)
                return self.env[model].with_context(new_ctx).message_post(
                    thread_id, body=body, subject=subject, type=type,
                    subtype=subtype, parent_id=parent_id, attachments=attachments,
                    content_subtype=content_subtype, **kwargs)

        #0: Find the message's author, because we need it for private discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.env.user.partner_id.id

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
            parent_message = mail_message.browse(parent_id)
            private_followers = set([partner.id for partner in parent_message.partner_ids])
            if parent_message.author_id:
                private_followers.add(parent_message.author_id.id)
            private_followers -= set([author_id])
            partner_ids |= private_followers

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_preprocess_attachments(attachments, kwargs.pop('attachment_ids', []), model, thread_id)

        # 4: mail.message.subtype
        subtype_id = False
        if subtype:
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype)

        # automatically subscribe recipients if asked to
        if self._context.get('mail_post_autofollow') and thread_id and partner_ids:
            partner_to_subscribe = partner_ids
            if self._context.get('mail_post_autofollow_partner_ids'):
                partner_to_subscribe = filter(lambda item: item in self._context.get('mail_post_autofollow_partner_ids'), partner_ids)
            self.message_subscribe([thread_id], list(partner_to_subscribe))  # TDE: check me

        # _mail_flat_thread: automatically set free messages to the first posted message
        if self._mail_flat_thread and model and not parent_id and thread_id:
            message_ids = mail_message.search(['&', ('res_id', '=', thread_id), ('model', '=', model), ('type', '=', 'email')], order="id ASC", limit=1)
            if not message_ids:
                message_ids = mail_message.search( ['&', ('res_id', '=', thread_id), ('model', '=', model)], order="id ASC", limit=1)
            parent_id = message_ids and message_ids[0] or False
        # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            message_ids = mail_message.sudo().search([('id', '=', parent_id), ('parent_id', '!=', False)])
            # avoid loops when finding ancestors
            processed_list = []
            if message_ids:
                message = message_ids[0]
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id

        values = kwargs
        values.update({
            'author_id': author_id,
            'model': model,
            'res_id': model and thread_id or False,
            'body': body,
            # 'subject': subject or False,
            # 'type': type,
            'parent_id': parent_id,
            'attachment_ids': attachment_ids,
            'subtype_id': subtype_id,
            'partner_ids': [(4, pid) for pid in partner_ids],
        })

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        message = mail_message.create(values)

        # Post-process: subscribe author, update message_last_post
        if model and model != 'mail.thread' and thread_id and subtype_id:
            # done with SUPERUSER_ID, because on some models users can post only with read access, not necessarily write access
            self.sudo().browse(thread_id).write({'message_last_post': fields.Datetime.now()})
        if message.author_id and model and thread_id and type != 'notification' and not self._context.get('mail_create_nosubscribe'):
            self.message_subscribe([thread_id], [message.author_id.id])
        return message.id  # TDE FIXME: @returns ?

    #------------------------------------------------------
    # Followers API
    #------------------------------------------------------

    @api.multi
    def message_subscribe_users(self, user_ids=None, subtype_ids=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, subscribe uid instead. """
        if user_ids is None:
            user_ids = [self.env.uid]
        partner_ids = [user.partner_id.id for user in self.env['res.users'].browse(user_ids)]
        result = self.message_subscribe(partner_ids, subtype_ids=subtype_ids)
        if partner_ids and result:
            self.env['ir.ui.menu'].clear_cache()
        return result

    @api.multi
    def message_subscribe(self, partner_ids, subtype_ids=None):
        """ Add partners to the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True

        user_pid = self.env.user.partner_id.id
        if set(partner_ids) == set([user_pid]):
            try:
                self.check_access_rights('read')
                self.check_access_rule('read')
            except AccessError:
                return False
        else:
            self.check_access_rights('write')
            self.check_access_rule('write')

        Followers = self.sudo().env['mail.followers']
        existing_pids_dict = {}
        followers = Followers.search(['&', '&', ('res_model', '=', self._name), ('res_id', 'in', self.ids), ('partner_id', 'in', partner_ids)])
        for fol in followers:
            existing_pids_dict.setdefault(fol.res_id, set()).add(fol.partner_id.id)

        # subtype_ids specified: update already subscribed partners
        if subtype_ids and followers:
            followers.write({'subtype_ids': [(6, 0, subtype_ids)]})
        # subtype_ids not specified: do not update already subscribed partner, fetch default subtypes for new partners
        if subtype_ids is None:
            subtypes = self.env['mail.message.subtype'].search([('default', '=', True), '|', ('res_model', '=', self._name), ('res_model', '=', False)])
            subtype_ids = subtypes.ids

        for id in self.ids:
            existing_pids = existing_pids_dict.get(id, set())
            new_pids = set(partner_ids) - existing_pids

            # subscribe new followers
            for new_pid in new_pids:
                Followers.create({
                    'res_model': self._name,
                    'res_id': id,
                    'partner_id': new_pid,
                    'subtype_ids': [(6, 0, subtype_ids)],
                })

        return True

    @api.multi
    def message_unsubscribe_users(self, user_ids=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, unsubscribe uid instead. """
        if user_ids is None:
            user_ids = [self.env.uid]
        partner_ids = [user.partner_id.id for user in self.env['res.users'].browse(user_ids)]
        result = self.message_unsubscribe(partner_ids)
        if partner_ids and result:
            self.env['ir.ui.menu'].clear_cache()
        return result

    @api.multi
    def message_unsubscribe(self, partner_ids):
        """ Remove partners from the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True
        user_pid = self.env.user.partner_id
        if set(partner_ids) == set([user_pid]):
            self.check_access_rights('read')
            self.check_access_rule('read')
        else:
            self.check_access_rights('write')
            self.check_access_rule('write')
        fol_ids = self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name),
             ('res_id', 'in', self.ids),
             ('partner_id', 'in', partner_ids)])
        return fol_ids.unlink()

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
        for name, field in self._fields.items():
            if name in auto_follow_fields and name in updated_fields and getattr(field, 'track_visibility', False) and field.comodel_name == 'res.users':
                user_field_lst.append(name)
        return user_field_lst

<<<<<<< HEAD
    def _message_auto_subscribe_notify(self, cr, uid, ids, partner_ids, context=None):
        """ Send notifications to the partners automatically subscribed to the thread
            Override this method if a custom behavior is needed about partners
            that should be notified or messages that should be sent
        """
        # find first email message, set it as unread for auto_subscribe fields for them to have a notification
        if partner_ids:
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
                    notification_obj = self.pool.get('mail.notification')
                    notification_obj._notify(cr, uid, msg_ids[0], partners_to_notify=partner_ids, context=context)
                    message = message_obj.browse(cr, uid, msg_ids[0], context=context)
                    if message.parent_id:
                        partner_ids_to_parent_notify = set(partner_ids).difference(partner.id for partner in message.parent_id.notified_partner_ids)
                        for partner_id in partner_ids_to_parent_notify:
                            notification_obj.create(cr, uid, {
                                'message_id': message.parent_id.id,
                                'partner_id': partner_id,
                                'is_read': True,
                            }, context=context)

    def message_auto_subscribe(self, cr, uid, ids, updated_fields, context=None, values=None):
        """ Handle auto subscription. Two methods for auto subscription exist:

         - tracked res.users relational fields, such as user_id fields. Those fields
           must be relation fields toward a res.users record, and must have the
           track_visilibity attribute set.
         - using subtypes parent relationship: check if the current model being
           modified has an header record (such as a project for tasks) whose followers
           can be added as followers of the current records. Example of structure
           with project and task:
=======
    def _subscribe_from_parent(self, values):
        Subtype = self.env['mail.message.subtype'].sudo()
        Followers = self.env['mail.followers'].sudo()
>>>>>>> [WIP] Migrate

        new_followers = dict()

        # fetch header subtypes (ex: project for updated tasks)
        subtypes = Subtype.search(['&', ('relation_field', '!=', False), '|', ('res_model', '=', False), ('parent_id.res_model', '=', self._name)])

        # find followers of parents, update structure for new followers
        parents = set()
        for subtype in subtypes:
            if subtype.relation_field and values.get(subtype.relation_field):
                parents.add((subtype.res_model, values.get(subtype.relation_field)))
        if parents:
            header_followers_domain = ['|'] * (len(parents) - 1)
            for header in parents:
                header_followers_domain += ['&', ('res_model', '=', header[0]), ('res_id', '=', header[1])]
            for header_follower in Followers.search(header_followers_domain):
                for subtype in header_follower.subtype_ids:
                    if subtype.parent_id and subtype.parent_id.res_model == self._name:
                        new_followers.setdefault(header_follower.partner_id.id, set()).add(subtype.parent_id.id)
                    elif subtype.res_model is False:
                        new_followers.setdefault(header_follower.partner_id.id, set()).add(subtype.id)

        return new_followers

    def _subscribe_from_fields(self, values):
        new_followers = dict()

        # fetch auto_follow_fields: res.users relation fields whose changes are tracked for subscription
        user_field_lst = self._message_get_auto_subscribe_fields(values)

        # add followers coming from res.users relational fields that are tracked
        user_ids = [values[name] for name in user_field_lst if values.get(name)]
        user_pids = [user.partner_id.id for user in self.env['res.users'].sudo().browse(user_ids)]
        for partner_id in user_pids:
            new_followers.setdefault(partner_id, None)

<<<<<<< HEAD
        for pid, subtypes in new_followers.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(cr, uid, ids, [pid], subtypes, context=context)

        self._message_auto_subscribe_notify(cr, uid, ids, user_pids, context=context)

=======
        # find first email message, set it as unread for auto_subscribe fields for them to have a notification
        if new_followers:
            Message = self.env['mail.message'].sudo()
            for record_id in self.ids:
                messages = Message.search([
                    ('model', '=', self._name),
                    ('res_id', '=', record_id),
                    ('type', '=', 'email')], limit=1)
                if not messages:
                    messages = Message.search([
                        ('model', '=', self._name),
                        ('res_id', '=', record_id)], limit=1)
                if messages:
                    # TDE FIXME check notify call
                    self.env['mail.notification']._notify(messages[0].id, partners_to_notify=new_followers.keys())

        return new_followers

    @api.multi
    def message_auto_subscribe(self, values):
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
        parents_followers = self._subscribe_from_parent(values)
        fields_followers = self._subscribe_from_fields(values)
        new_followers = dict(
            (pid, parents_followers.get(pid, set()).union(fields_followers.get(pid, set())))
            for pid in set(parents_followers).union(fields_followers))
        for pid, subtypes in new_followers.items():
            subtypes = list(subtypes) if subtypes else None
            self.message_subscribe([pid], subtypes)
>>>>>>> [WIP] Migrate

        return True

    #------------------------------------------------------
    # Thread management
    #------------------------------------------------------

    @api.multi
    def message_mark_as_unread(self):
        self.env.cr.execute('''
            UPDATE mail_notification SET
                is_read=false
            WHERE
                message_id IN (SELECT id from mail_message where res_id=any(%s) and model=%s limit 1) and
                partner_id = %s
        ''', (self.ids, self._name, self.env.user.partner_id.id))
        self.env['mail.notification'].invalidate_cache(['is_read'])
        return True

    @api.multi
    def message_mark_as_read(self):
        self.env.cr.execute('''
            UPDATE mail_notification SET
                is_read=true
            WHERE
                message_id IN (SELECT id FROM mail_message WHERE res_id=ANY(%s) AND model=%s) AND
                partner_id = %s
        ''', (self.ids, self._name, self.env.user.partner_id.id))
        self.env['mail.notification'].invalidate_cache(['is_read'])
        return True

    @api.model
    def message_get_suggested_threads(self, removed_suggested_threads=None, limit=3):
        """ Return a list of suggested threads, sorted by the numbers of followers"""
        # TDE HACK: originally by MAT from portal/mail_mail.py but not working until the inheritance graph bug is not solved in trunk
        # TDE FIXME: relocate in portal when it won't be necessary to reload the hr.employee model in an additional bridge module
<<<<<<< HEAD
        if 'is_portal' in self.pool['res.groups']._fields:
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
            if any(group.is_portal for group in user.groups_id):
=======
        # TDE BACKWARD: should be optimized in 8.0
        if self.env['res.groups']._all_columns.get('is_portal'):
            if any(group.is_portal for group in self.env.user.groups_id):
>>>>>>> [WIP] Migrate
                return []

        threads = self.search([('id', 'not in', removed_suggested_threads or []), ('message_is_follower', '=', False)], limit=3)
        data = [{
            'id': thread.id,
            'popularity': len(thread.message_follower_ids),
            'name': thread.name,
            'image_small': thread.image_small} for thread in threads]
        return sorted(data, key=lambda x: (x['popularity'], x['id']), reverse=True)
    # backward compatibility (remove in v9)
    get_suggested_thread = message_get_suggested_threads

    @api.multi
    # TDE FIXME: was for 1 id only -> fixme
    def message_change_thread(self, new_res_id, new_model):
        """ Transfer the list of the mail thread messages from a document to
        another possibly in another model. All messages having a subtype different
        from discussion will be reset, to avoid potential issues with subtypes.

        :param id : the old res_id of the mail.message
        :param new_res_id : the new res_id of the mail.message
        :param new_model : the name of the new model of the mail.message """
        subtype_res_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment', raise_if_not_found=True)
        Message = self.env['mail.message']
        comments = Message.search([('model', '=', self._name), ('res_id', 'in', self.ids), ('subtype_id', '=', subtype_res_id)])
        others = Message.search([('model', '=', self._name), ('res_id', '=', self.ids), ('subtype_id', '!=', subtype_res_id)])
        comments.write({"res_id": new_res_id, "model": new_model})
        others.write({"res_id": new_res_id, "model": new_model, "subtype_id": None})
        return True
