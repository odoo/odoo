# -*- coding: utf-8 -*-

import base64
import datetime
import dateutil
import email
import hashlib
import hmac
import json
import lxml
from lxml import etree
import logging
import pytz
import re
import socket
import time
import xmlrpclib

from collections import namedtuple
from email.message import Message
from email.utils import formataddr
from werkzeug import url_encode

from openerp import _, api, fields, models
from openerp import exceptions
from openerp import tools
from openerp.addons.mail.models.mail_message import decode
from openerp.tools.safe_eval import safe_eval as eval


_logger = logging.getLogger(__name__)


mail_header_msgid_re = re.compile('<[^<>]+>')


def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class MailThread(models.AbstractModel):
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

    MailThread features can be somewhat controlled through context keys :

     - ``mail_create_nosubscribe``: at create or message_post, do not subscribe
       uid to the record thread
     - ``mail_create_nolog``: at create, do not log the automatic '<Document>
       created' message
     - ``mail_notrack``: at create and write, do not perform the value tracking
       creating messages
     - ``tracking_disable``: at create and write, perform no MailThread features
       (auto subscription, tracking, post, ...)
     - ``mail_save_message_last_post``: at message_post, update message_last_post
       datetime field
     - ``mail_auto_delete``: auto delete mail notifications; True by default
       (technical hack for templates)
     - ``mail_notify_force_send``: if less than 50 email notifications to send,
       send them directly instead of using the queue; True by default
     - ``mail_notify_user_signature``: add the current user signature in
       email notifications; True by default
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'
    _mail_flat_thread = True  # flatten the discussino history
    _mail_post_access = 'write'  # access required on the document to post on it
    _mail_mass_mailing = False  # enable mass mailing on this model
    _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))

    message_is_follower = fields.Boolean(
        'Is Follower', compute='_compute_is_follower', search='_search_is_follower')
    message_follower_ids = fields.One2many(
        'mail.followers', 'res_id', string='Followers',
        domain=lambda self: [('res_model', '=', self._name)])
    message_partner_ids = fields.Many2many(
        comodel_name='res.partner', string='Followers (Partners)',
        compute='_get_followers', search='_search_follower_partners')
    message_channel_ids = fields.Many2many(
        comodel_name='mail.channel', string='Followers (Channels)',
        compute='_get_followers', search='_search_follower_channels')
    message_ids = fields.One2many(
        'mail.message', 'res_id', string='Messages',
        domain=lambda self: [('model', '=', self._name)], auto_join=True)
    message_last_post = fields.Datetime('Last Message Date', help='Date of the last message posted on the record.')
    message_unread = fields.Boolean(
        'Unread Messages', compute='_get_message_unread',
        help="If checked new messages require your attention.")
    message_unread_counter = fields.Integer(
        'Unread Messages Counter', compute='_get_message_unread',
        help="Number of unread messages")
    message_needaction = fields.Boolean(
        'Action Needed', compute='_get_message_needaction', search='_search_message_needaction',
        help="If checked, new messages require your attention.")
    message_needaction_counter = fields.Integer(
        'Number of Actions', compute='_get_message_needaction',
        help="Number of messages which requires an action")

    @api.one
    @api.depends('message_follower_ids')
    def _get_followers(self):
        self.message_partner_ids = self.message_follower_ids.mapped('partner_id')
        self.message_channel_ids = self.message_follower_ids.mapped('channel_id')

    @api.model
    def _search_follower_partners(self, operator, operand):
        """Search function for message_follower_ids

        Do not use with operator 'not in'. Use instead message_is_followers
        """
        # TOFIX make it work with not in
        assert operator != "not in", "Do not search message_follower_ids with 'not in'"
        followers = self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('partner_id', operator, operand)])
        return [('id', 'in', followers.mapped('res_id'))]

    @api.model
    def _search_follower_channels(self, operator, operand):
        """Search function for message_follower_ids

        Do not use with operator 'not in'. Use instead message_is_followers
        """
        # TOFIX make it work with not in
        assert operator != "not in", "Do not search message_follower_ids with 'not in'"
        followers = self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('channel_id', operator, operand)])
        return [('id', 'in', followers.mapped('res_id'))]

    @api.multi
    @api.depends('message_follower_ids')
    def _compute_is_follower(self):
        followers = self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
            ])
        following_ids = followers.mapped('res_id')
        for record in self:
            record.message_is_follower = record.id in following_ids

    @api.model
    def _search_is_follower(self, operator, operand):
        followers = self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('partner_id', '=', self.env.user.partner_id.id),
            ])
        # Cases ('message_is_follower', '=', True) or  ('message_is_follower', '!=', False)
        if (operator == '=' and operand) or (operator == '!=' and not operand):
            return [('id', 'in', followers.mapped('res_id'))]
        else:
            return [('id', 'not in', followers.mapped('res_id'))]

    @api.multi
    def _get_message_unread(self):
        res = dict((res_id, 0) for res_id in self.ids)
        partner_id = self.env.user.partner_id.id

        # search for unread messages, directly in SQL to improve performances
        self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                             RIGHT JOIN mail_message_mail_channel_rel rel
                             ON rel.mail_message_id = msg.id
                             RIGHT JOIN mail_channel_partner cp
                             ON (cp.channel_id = rel.mail_channel_id AND cp.partner_id = %s AND
                                (cp.seen_message_id IS NULL OR cp.seen_message_id < msg.id))
                             WHERE msg.model = %s AND msg.res_id in %s AND
                                   (msg.author_id IS NULL OR msg.author_id != %s) AND
                                   (msg.message_type != 'notification' OR msg.model != 'mail.channel')""",
                         (partner_id, self._name, tuple(self.ids), partner_id,))
        for result in self._cr.fetchall():
            res[result[0]] += 1

        for record in self:
            record.message_unread_counter = res.get(record.id, 0)
            record.message_unread = bool(record.message_unread_counter)

    @api.multi
    def _get_message_needaction(self):
        res = dict((res_id, 0) for res_id in self.ids)

        # search for unread messages, directly in SQL to improve performances
        self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                             RIGHT JOIN mail_message_res_partner_needaction_rel rel
                             ON rel.mail_message_id = msg.id AND rel.res_partner_id = %s
                             WHERE msg.model = %s AND msg.res_id in %s""",
                         (self.env.user.partner_id.id, self._name, tuple(self.ids),))
        for result in self._cr.fetchall():
            res[result[0]] += 1

        for record in self:
            record.message_needaction_counter = res.get(record.id, 0)
            record.message_needaction = bool(record.message_needaction_counter)

    @api.model
    def _search_message_needaction(self, operator, operand):
        return [('message_ids.needaction', operator, operand)]

    # ------------------------------------------------------
    # CRUD overrides for automatic subscription and logging
    # ------------------------------------------------------

    @api.model
    def create(self, values):
        """ Chatter override :
            - subscribe uid
            - subscribe followers of parent
            - log a creation message
        """
        if self._context.get('tracking_disable'):
            return super(MailThread, self).create(values)

        # subscribe uid unless asked not to
        if not self._context.get('mail_create_nosubscribe'):
            message_follower_ids = values.get('message_follower_ids') or []  # webclient can send None or False
            message_follower_ids += self.env['mail.followers']._add_follower_command(self._name, [], {self.env.user.partner_id.id: None}, {}, force=True)[0]
            values['message_follower_ids'] = message_follower_ids
        thread = super(MailThread, self).create(values)

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not self._context.get('mail_create_nolog'):
            doc_name = self.env['ir.model'].search([('model', '=', self._name)]).read(['name'])[0]['name']
            thread.message_post(body=_('%s created') % doc_name)

        # auto_subscribe: take values and defaults into account
        create_values = dict(values)
        for key, val in self._context.iteritems():
            if key.startswith('default_') and key[8:] not in create_values:
                create_values[key[8:]] = val
        thread.message_auto_subscribe(create_values.keys(), values=create_values)

        # track values
        if not self._context.get('mail_notrack'):
            if 'lang' not in self._context:
                track_thread = thread.with_context(lang=self.env.user.lang)
            else:
                track_thread = thread
            tracked_fields = track_thread._get_tracked_fields(values.keys())
            if tracked_fields:
                initial_values = {thread.id: dict.fromkeys(tracked_fields, False)}
                track_thread.message_track(tracked_fields, initial_values)

        return thread

    @api.multi
    def write(self, values):
        if self._context.get('tracking_disable'):
            return super(MailThread, self).write(values)

        # Track initial values of tracked fields
        if 'lang' not in self._context:
            track_self = self.with_context(lang=self.env.user.lang)
        else:
            track_self = self

        tracked_fields = None
        if not self._context.get('mail_notrack'):
            tracked_fields = track_self._get_tracked_fields(values.keys())
        if tracked_fields:
            initial_values = dict((record.id, dict((key, getattr(record, key)) for key in tracked_fields))
                                  for record in track_self)

        # Perform write
        result = super(MailThread, self).write(values)

        # update followers
        self.message_auto_subscribe(values.keys(), values=values)

        # Perform the tracking
        if tracked_fields:
            track_self.message_track(tracked_fields, initial_values)

        return result

    @api.multi
    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        res = super(MailThread, self).unlink()
        self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        ).unlink()
        return res

    def copy_data(self, cr, uid, id, default=None, context=None):
        context = dict(context or {}, mail_notrack=True)
        # avoid tracking multiple temporary changes during copy
        return super(MailThread, self).copy_data(cr, uid, id, default=default, context=context)

    # ------------------------------------------------------
    # Technical methods (to clean / move to controllers ?)
    # ------------------------------------------------------

    @api.model
    def get_empty_list_help(self, help):
        """ Override of BaseModel.get_empty_list_help() to generate an help message
        that adds alias information. """
        model = self._context.get('empty_list_help_model')
        res_id = self._context.get('empty_list_help_id')
        catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        document_name = self._context.get('empty_list_help_document_name', _('document'))
        add_arrow = not help or help.find("oe_view_nocontent_create") == -1
        alias = None

        if catchall_domain and model and res_id:  # specific res_id -> find its alias (i.e. section_id specified)
            record = self.env[model].sudo().browse(res_id)
            # check that the alias effectively creates new records
            if record.alias_id and record.alias_id.alias_name and \
                    record.alias_id.alias_model_id and \
                    record.alias_id.alias_model_id.model == self._name and \
                    record.alias_id.alias_force_thread_id == 0:
                alias = record.alias_id
        if not alias and catchall_domain and model:  # no res_id or res_id not linked to an alias -> generic help message, take a generic alias of the model
            Alias = self.env['mail.alias']
            aliases = Alias.search([
                ("alias_parent_model_id.model", "=", model),
                ("alias_name", "!=", False),
                ('alias_force_thread_id', '=', False),
                ('alias_parent_thread_id', '=', False)], order='id ASC')
            if aliases and len(aliases) == 1:
                alias = aliases[0]

        if alias:
            email_link = "<a href='mailto:%(email)s'>%(email)s</a>" % {'email': alias.name_get()[0][1]}
            if add_arrow:
                return "<p class='oe_view_nocontent_create'>%(dyn_help)s</p>%(static_help)s" % {
                    'static_help': help or '',
                    'dyn_help': _("Click here to add new %(document)s or send an email to: %(email_link)s") % {
                        'document': document_name,
                        'email_link': email_link
                    }
                }
            return "%(static_help)s<p>%(dyn_help)s" % {
                    'static_help': help or '',
                    'dyn_help': _("You could also add a new %(document)s by sending an email to: %(email_link)s.") %  {
                        'document': document_name,
                        'email_link': email_link,
                    }
                }

        if add_arrow:
            return "<p class='oe_view_nocontent_create'>%(dyn_help)s</p>%(static_help)s" % {
                'static_help': help or '',
                'dyn_help': _("Click here to add new %s") % document_name,
                }

        return help

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(MailThread, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']"):
                # the 'Log a note' button is employee only
                options = eval(node.get('options', '{}'))
                is_employee = self.env.user.has_group('base.group_user')
                options['display_log_button'] = is_employee
                # emoji list
                options['emoji_list'] = self.env['mail.shortcode'].search([('shortcode_type', '=', 'image')]).read(['source', 'description', 'substitution'])
                # save options on the node
                node.set('options', repr(options))
            res['arch'] = etree.tostring(doc)
        return res

    # ------------------------------------------------------
    # Automatic log / Tracking
    # ------------------------------------------------------

    @api.model
    def _get_tracked_fields(self, updated_fields):
        """ Return a structure of tracked fields for the current model.
            :param list updated_fields: modified field names
            :return dict: a dict mapping field name to description, containing
                always tracked fields and modified on_change fields
        """
        tracked_fields = []
        for name, field in self._fields.items():
            if getattr(field, 'track_visibility', False):
                tracked_fields.append(name)

        if tracked_fields:
            return self.fields_get(tracked_fields)
        return {}

    @api.multi
    def _track_subtype(self, init_values):
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
    def _track_template(self, tracking):
        return dict()

    @api.multi
    def _message_track_post_template(self, tracking):
        if not any(change for rec_id, (change, tracking_value_ids) in tracking.iteritems()):
            return True
        templates = self._track_template(tracking)
        for field_name, (template, post_kwargs) in templates.iteritems():
            if not template:
                continue
            if isinstance(template, basestring):
                self.message_post_with_view(template, **post_kwargs)
            else:
                self.message_post_with_template(template.id, **post_kwargs)
        return True

    @api.multi
    def _message_track_get_changes(self, tracked_fields, initial_values):
        """ Batch method of _message_track. """
        result = dict()
        for record in self:
            result[record.id] = record._message_track(tracked_fields, initial_values[record.id])
        return result

    @api.multi
    def _message_track(self, tracked_fields, initial):
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a structure that is a tuple containing :

         - a set of updated column names
         - a list of changes (initial value, new value, column name, column info) """
        self.ensure_one()
        changes = set()
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            initial_value = initial[col_name]
            new_value = getattr(self, col_name)

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                tracking = self.env['mail.tracking.value'].create_tracking_values(initial_value, new_value, col_name, col_info)
                if tracking:
                    tracking_value_ids.append([0, 0, tracking])

                if col_name in tracked_fields:
                    changes.add(col_name)
        return changes, tracking_value_ids

    @api.multi
    def message_track(self, tracked_fields, initial_values):
        """ Track updated values. Comparing the initial and current values of
        the fields given in tracked_fields, it generates a message containing
        the updated values. This message can be linked to a mail.message.subtype
        given by the ``_track_subtype`` method. """
        if not tracked_fields:
            return True

        tracking = self._message_track_get_changes(tracked_fields, initial_values)
        for record in self:
            changes, tracking_value_ids = tracking[record.id]
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtype_xmlid = False
            # By passing this key, that allows to let the subtype empty and so don't sent email because partners_to_notify from mail_message._notify will be empty
            if not self._context.get('mail_track_log_only'):
                subtype_xmlid = record._track_subtype(dict((col_name, initial_values[record.id][col_name]) for col_name in changes))
                # compatibility: use the deprecated _track dict
                if not subtype_xmlid and hasattr(self, '_track'):
                    for field, track_info in self._track.items():
                        if field not in changes or subtype_xmlid:
                            continue
                        for subtype, method in track_info.items():
                            if method(self, self._cr, self._uid, record, self._context):
                                _logger.warning("Model %s still using deprecated _track dict; override _track_subtype method instead" % self._name)
                                subtype_xmlid = subtype

            if subtype_xmlid:
                subtype_rec = self.env.ref(subtype_xmlid)  # TDE FIXME check for raise if not found
                if not (subtype_rec and subtype_rec.exists()):
                    _logger.debug('subtype %s not found' % subtype_xmlid)
                    continue
                record.message_post(subtype=subtype_xmlid, tracking_value_ids=tracking_value_ids)
            elif tracking_value_ids:
                record.message_post(tracking_value_ids=tracking_value_ids)

        self._message_track_post_template(tracking)

        return True

    #------------------------------------------------------
    # mail.message wrappers and tools
    #------------------------------------------------------

    @api.model
    def _needaction_domain_get(self):
        if self._needaction:
            return [('message_needaction', '=', True)]
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
        self.env['ir.attachment'].search([
            ('res_model', '=', 'mail.compose.message'),
            ('res_id', '=', 0),
            ('create_date', '<', limit_date_str),
            ('write_date', '<', limit_date_str)]
        ).unlink()
        return True

    @api.model
    def check_mail_message_access(self, res_ids, operation, model_name=None):
        """ mail.message check permission rules for related document. This method is
            meant to be inherited in order to implement addons-specific behavior.
            A common behavior would be to allow creating messages when having read
            access rule on the document, for portal document such as issues. """
        if model_name:
            DocModel = self.env[model_name]
        else:
            DocModel = self
        if hasattr(DocModel, '_mail_post_access'):
            create_allow = DocModel._mail_post_access
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

        DocModel.check_access_rights(check_operation)
        DocModel.browse(res_ids).check_access_rule(check_operation)

    @api.model
    def _get_inbox_action_xml_id(self):
        """ When redirecting towards the Inbox, choose which action xml_id has
            to be fetched. This method is meant to be inherited, at least in portal
            because portal users have a different Inbox action than classic users. """
        return 'mail.mail_channel_action_client_chat'

    @api.model
    def _generate_notification_token(self, base_link, params):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params.keys())))
        hm = hmac.new(str(secret), token, hashlib.sha1).hexdigest()
        return hm

    @api.multi
    def _notification_link_helper(self, link_type, **kwargs):
        if kwargs.get('message_id'):
            base_params = {
                'message_id': kwargs.pop('message_id')
            }
        else:
            base_params = {
                'model': kwargs.get('model', self._name),
                'res_id': kwargs.get('res_id', self.ids and self.ids[0] or False),
            }

        if link_type in ['view', 'assign', 'follow', 'unfollow']:
            params = dict(base_params)
            base_link = '/mail/%s' % link_type
        elif link_type == 'new':
            params = dict(base_params, action_id=kwargs.get('action_id', ''))
            base_link = '/mail/new'
        elif link_type == 'controller':
            controller = kwargs.pop('controller')
            params = dict(base_params)
            params.pop('model')
            base_link = '%s' % controller
        else:
            return ''

        if link_type not in ['view', 'new']:
            token = self._generate_notification_token(base_link, params)
            params['token'] = token

        link = '%s?%s' % (base_link, url_encode(params))
        return link

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Given the categories of partners to emails in group_data, set the
        right group for the recipients. The basic behavior is simply to
        distinguish users from partners.

        Inherit this method to group recipients according to specific criterions
        allowing to tune the notification email. Generally this will be based
        on user groups (res.groups), but not necessarily.

        Example: having defined a group_hr_user entry, store HR users and
        officers. """
        # TDE note: recipients is normally sudo-ed
        group_user = self.env['ir.model.data'].xmlid_to_res_id('base.group_user')
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_user in recipient.user_ids[0].groups_id.ids:
                group_data['user'] |= recipient
            else:
                group_data['partner'] |= recipient
        return group_data

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        """ Give the categories of recipients for notification emails. As emails
        are generated once for group of recipients to work in batch, the first
        thing to do is to categorize them. The basic behavior is simply
        to distinguish users from partners.

        Specific values :

         - button_access: used to display 'View Document' in email, if set
         - button_follow: used to display 'Follow' in email, if set
         - button unfollow: used to display 'Unfollow' in email, if set
        """
        # TDE note: recipients is normally sudo-ed
        return {
            'partner': {
                'button_access': None,
                'button_follow': False,
                'button_unfollow': False,
            },
            'user': {
            }
        }

    @api.multi
    def _message_notification_recipients(self, message, recipients):
        # At this point, all access rights should be ok. We sudo everything to
        # access rights checks and speedup the computation.
        recipients_sudo = recipients.sudo()
        if self._context.get('auto_delete', False):
            access_link = self._notification_link_helper('view')
        else:
            access_link = self._notification_link_helper('view', message_id=message.id)

        if message.model:
            model_name = self.env['ir.model'].sudo().search([('model', '=', self.env[message.model]._name)]).name_get()[0][1]
            view_title = '%s %s' % (_('View'), model_name)
        else:
            view_title = _('View')

        result = {}
        group_data = {}

        for category, data in self._notification_get_recipient_groups(message, recipients).iteritems():
            result[category] = {
                'followers': self.env['res.partner'],
                'not_followers': self.env['res.partner'],
                'button_access': {'url': access_link, 'title': view_title},
                'button_follow': {'url': self._notification_link_helper('follow', model=message.model, res_id=message.res_id), 'title': _('Follow')},
                'button_unfollow': {'url': self._notification_link_helper('unfollow', model=message.model, res_id=message.res_id), 'title': _('Unfollow')},
                'actions': list(),
            }
            group_data[category] = self.env['res.partner']
            result[category].update(data)

        doc_followers = self.env['mail.followers']
        if message.model and message.res_id:
            doc_followers = self.env['mail.followers'].sudo().search([
                ('res_model', '=', message.model),
                ('res_id', '=', message.res_id),
                ('partner_id', 'in', recipients_sudo.ids)])
        partner_followers = doc_followers.mapped('partner_id')

        # classify recipients, then set them in followers / not followers
        group_data = self._notification_group_recipients(message, recipients, set(), group_data)
        for category, recipients in group_data.iteritems():
            for recipient in recipients:
                if recipient in partner_followers:
                    result[category]['followers'] |= recipient
                else:
                    result[category]['not_followers'] |= recipient

        return result

    # ------------------------------------------------------
    # Email specific
    # ------------------------------------------------------

    @api.multi
    def message_get_default_recipients(self, res_model=None, res_ids=None):
        if res_model and res_ids:
            if hasattr(self.env[res_model], 'message_get_default_recipients'):
                return self.env[res_model].browse(res_ids).message_get_default_recipients()
            records = self.env[res_model].sudo().browse(res_ids)
        else:
            records = self.sudo()
        res = {}
        for record in records:
            recipient_ids, email_to, email_cc = set(), False, False
            if 'partner_id' in self._fields and record.partner_id:
                recipient_ids.add(record.partner_id.id)
            elif 'email_from' in self._fields and record.email_from:
                email_to = record.email_from
            elif 'email' in self._fields:
                email_to = record.email
            res[record.id] = {'partner_ids': list(recipient_ids), 'email_to': email_to, 'email_cc': email_cc}
        return res

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Returns the preferred reply-to email address that is basically the
        alias of the document, if it exists. Override this method to implement
        a custom behavior about reply-to for generated emails. """
        model_name = self.env.context.get('thread_model') or self._name
        alias_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
        res = dict.fromkeys(res_ids, False)

        # alias domain: check for aliases and catchall
        aliases = {}
        doc_names = {}
        if alias_domain:
            if model_name and model_name != 'mail.thread' and res_ids:
                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model_name),
                    ('alias_parent_thread_id', 'in', res_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match
                # order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    if alias.alias_parent_thread_id not in aliases:
                        aliases[alias.alias_parent_thread_id] = '%s@%s' % (alias.alias_name, alias_domain)
                doc_names.update(
                    dict((ng_res[0], ng_res[1])
                         for ng_res in self.env[model_name].sudo().browse(aliases.keys()).name_get()))
            # left ids: use catchall
            left_ids = set(res_ids).difference(set(aliases.keys()))
            if left_ids:
                catchall_alias = self.env['ir.config_parameter'].get_param("mail.catchall.alias")
                if catchall_alias:
                    aliases.update(dict((res_id, '%s@%s' % (catchall_alias, alias_domain)) for res_id in left_ids))
            # compute name of reply-to
            company_name = self.env.user.company_id.name
            for res_id in aliases.keys():
                email_name = '%s%s' % (company_name, doc_names.get(res_id) and (' ' + doc_names[res_id]) or '')
                email_addr = aliases[res_id]
                res[res_id] = formataddr((email_name, email_addr))
        left_ids = set(res_ids).difference(set(aliases.keys()))
        if left_ids:
            res.update(dict((res_id, default) for res_id in res_ids))
        return res

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        """ Get specific notification email values to store on the notification
        mail_mail. Void method, inherit it to add custom values. """
        self.ensure_one()
        database_uuid = self.env['ir.config_parameter'].get_param('database.uuid')
        return {'headers': repr({
            'X-Odoo-Objects': "%s-%s" % (self._model, self.id),
            'X-Odoo-db-uuid': database_uuid
        })}

    @api.multi
    def message_get_recipient_values(self, notif_message=None, recipient_ids=None):
        """ Get specific notification recipient values to store on the notification
        mail_mail. Basic method just set the recipient partners as mail_mail
        recipients. Inherit this method to add custom behavior like using
        recipient email_to to bypass the recipint_ids heuristics in the
        mail sending mechanism. """
        return {
            'recipient_ids': [(4, pid) for pid in recipient_ids]
        }

    # ------------------------------------------------------
    # Mail gateway
    # ------------------------------------------------------

    @api.model
    def message_capable_models(self):
        """ Used by the plugin addon, based for plugin_outlook and others. """
        ret_dict = {}
        for model_name in self.pool.obj_list():
            model = self.pool[model_name]
            if hasattr(model, "message_process") and hasattr(model, "message_post"):
                ret_dict[model_name] = model._description
        return ret_dict

    def _message_find_partners(self, message, header_fields=['From']):
        """ Find partners related to some header fields of the message.

            :param string message: an email.message instance """
        s = ', '.join([decode(message.get(h)) for h in header_fields if message.get(h)])
        return filter(lambda x: x, self._find_partner_from_emails(tools.email_split(s)))

    @api.model
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
        record_set = None

        def _create_bounce_email():
            bounce_to = decode_header(message, 'Return-Path') or email_from
            bounce_mail_values = {
                'body_html': '<div><p>Hello,</p>'
                             '<p>The following email sent to %s cannot be accepted because this is '
                             'a private email address. Only allowed people can contact us at this address.</p></div>'
                             '<blockquote>%s</blockquote>' % (message.get('to'), message_dict.get('body')),
                'subject': 'Re: %s' % message.get('subject'),
                'email_to': bounce_to,
                'auto_delete': True,
            }
            bounce_from = self.env['ir.mail_server']._get_default_bounce_address()
            if bounce_from:
                bounce_mail_values['email_from'] = 'MAILER-DAEMON <%s>' % bounce_from
            self.env['mail.mail'].create(bounce_mail_values).send()

        def _warn(message):
            _logger.info('Routing mail with Message-Id %s: route %s: %s',
                         message_id, route, message)

        # Wrong model
        if model and model not in self.pool:
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
            return False

        if model and thread_id:
            record_set = self.env[model].browse(thread_id)
        elif model:
            record_set = self.env[model]

        # Existing Document: check if exists; if not, fallback on create if allowed
        if thread_id and not record_set.exists():
            if create_fallback:
                _warn('reply to missing document (%s,%s), fall back on new document creation' % (model, thread_id))
                thread_id = None
            elif assert_model:
                # TDE FIXME: change assert to some real error
                assert record_set.exists(), 'Routing: reply to missing document (%s,%s)' % (model, thread_id)
            else:
                _warn('reply to missing document (%s,%s), skipping' % (model, thread_id))
                return False

        # Existing Document: check model accepts the mailgateway
        if thread_id and model and not hasattr(record_set, 'message_update'):
            if create_fallback:
                _warn('model %s does not accept document update, fall back on document creation' % model)
                thread_id = None
            elif assert_model:
                assert hasattr(record_set, 'message_update'), 'Routing: model %s does not accept document update, crashing' % model
            else:
                _warn('model %s does not accept document update, skipping' % model)
                return False

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(record_set, 'message_new'):
            if assert_model:
                if not hasattr(record_set, 'message_new'):
                    raise ValueError(
                        'Model %s does not accept document creation, crashing' % model
                    )
            _warn('model %s does not accept document creation, skipping' % model)
            return False

        # Update message author if asked
        # We do it now because we need it for aliases (contact settings)
        if not author_id and update_author:
            author_ids = self.env['mail.thread']._find_partner_from_emails([email_from], res_model=model, res_id=thread_id)
            if author_ids:
                author_id = author_ids[0]
                message_dict['author_id'] = author_id

        # Alias: check alias_contact settings
        if alias and alias.alias_contact == 'followers' and (thread_id or alias.alias_parent_thread_id):
            if thread_id:
                obj = record_set[0]
            else:
                obj = self.env[alias.alias_parent_model_id.model].browse(alias.alias_parent_thread_id)
            accepted_partner_ids = list(
                set(partner.id for partner in obj.message_partner_ids) |
                set(partner.id for channel in obj.message_channel_ids for partner in channel.channel_partner_ids)
            )
            if not author_id or author_id not in accepted_partner_ids:
                _warn('alias %s restricted to internal followers, skipping' % alias.alias_name)
                _create_bounce_email()
                return False
        elif alias and alias.alias_contact == 'partners' and not author_id:
            _warn('alias %s does not accept unknown author, skipping' % alias.alias_name)
            _create_bounce_email()
            return False

        if not model and not thread_id and not alias and not allow_private:
            return ()

        return (model, thread_id, route[2], route[3], None if self._context.get('drop_alias', False) else route[4])

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
        Alias = self.env['mail.alias']
        fallback_model = model

        # Get email.message.Message variables for future processing
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')
        references = decode_header(message, 'References')
        in_reply_to = decode_header(message, 'In-Reply-To').strip()
        thread_references = references or in_reply_to

        # 0. First check if this is a bounce message or not.
        #    See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #    As all MTA does not respect this RFC (googlemail is one of them),
        #    we also need to verify if the message come from "mailer-daemon"
        localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        if message.get_content_type() == 'multipart/report' or localpart == 'mailer-daemon':
            _logger.info("Not routing bounce email from %s to %s with Message-Id %s",
                         email_from, email_to, message_id)
            return []

        # 1. message is a reply to an existing message (exact match of message_id)
        ref_match = thread_references and tools.reference_re.search(thread_references)
        msg_references = mail_header_msgid_re.findall(thread_references)
        mail_messages = MailMessage.sudo().search([('message_id', 'in', msg_references)], limit=1)
        if ref_match and mail_messages:
            model, thread_id = mail_messages.model, mail_messages.res_id
            alias = Alias.search([('alias_name', '=', (tools.email_split(email_to) or [''])[0].split('@', 1)[0].lower())])
            alias = alias[0] if alias else None
            route = self.with_context(drop_alias=True).message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, alias),
                update_author=True, assert_model=False, create_fallback=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

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
                    record = self.env[model].browse(thread_id)
                    compat_mail_msg_ids = MailMessage.search([
                        ('message_id', '=', False),
                        ('model', '=', model),
                        ('res_id', '=', thread_id)])
                    if compat_mail_msg_ids and record.exists() and hasattr(record, 'message_update'):
                        route = self.message_route_verify(
                            message, message_dict,
                            (model, thread_id, custom_values, self._uid, None),
                            update_author=True, assert_model=True, create_fallback=True)
                        if route:
                            # parent is invalid for a compat-reply
                            message_dict.pop('parent_id', None)
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct thread reply (compat-mode) to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                                email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                            return [route]
                        elif route is False:
                            return []

        # 3. Reply to a private message
        if in_reply_to:
            mail_message_ids = MailMessage.search([
                ('message_id', '=', in_reply_to),
                '!', ('message_id', 'ilike', 'reply_to')
            ], limit=1)
            if mail_message_ids:
                route = self.message_route_verify(
                    message, message_dict,
                    (mail_message_ids.model, mail_message_ids.res_id, custom_values, self._uid, None),
                    update_author=True, assert_model=True, create_fallback=True, allow_private=True)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct reply to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, mail_message_ids.id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []

        # no route found for a matching reference (or reply), so parent is invalid
        message_dict.pop('parent_id', None)

        # 4. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = \
             ','.join([decode_header(message, 'Delivered-To'),
                       decode_header(message, 'To'),
                       decode_header(message, 'Cc'),
                       decode_header(message, 'Resent-To'),
                       decode_header(message, 'Resent-Cc')])
        local_parts = [e.split('@')[0].lower() for e in tools.email_split(rcpt_tos)]
        if local_parts:
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
            (email_from, email_to, message_id)
        )

    @api.model
    def message_route_process(self, message, message_dict, routes):
        self = self.with_context(attachments_mime_plainxml=True) # import XML attachments as text
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes or ():
            if model:
                Model = self.env[model]
                if not (thread_id and hasattr(Model, 'message_update') or hasattr(Model, 'message_new')):
                    raise ValueError(
                        "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" %
                        (message_dict['message_id'], model)
                    )

                # disabled subscriptions during message_new/update to avoid having the system user running the
                # email gateway become a follower of all inbound messages
                MessageModel = Model.sudo(user_id).with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
                if thread_id and hasattr(MessageModel, 'message_update'):
                    MessageModel.browse(thread_id).message_update(message_dict)
                else:
                    # if a new thread is created, parent is irrelevant
                    message_dict.pop('parent_id', None)
                    thread_id = MessageModel.message_new(message_dict, custom_values)
            else:
                if thread_id:
                    raise ValueError("Posting a message without model should be with a null res_id, to create a private message.")
                Model = self.env['mail.thread']
            if not hasattr(Model, 'message_post'):
                Model = self.env['mail.thread'].with_context(thread_model=model)
            new_msg = Model.browse(thread_id).message_post(subtype='mail.mt_comment', **message_dict)

            if partner_ids:
                # postponed after message_post, because this is an external message and we don't want to create
                # duplicate emails due to notifications
                new_msg.write({'partner_ids': partner_ids})
        return thread_id

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
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
            existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg.get('message_id'))])
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
        RecordModel = self.env[model]
        fields = RecordModel.fields_get()
        name_field = RecordModel._rec_name or 'name'
        if name_field in fields and not data.get('name'):
            data[name_field] = msg_dict.get('subject', '')
        res = RecordModel.create(data)
        return res.id

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

    def _message_extract_payload_postprocess(self, message, body, attachments):
        """ Perform some cleaning / postprocess in the body and attachments
        extracted from the email. Note that this processing is specific to the
        mail module, and should not contain security or generic html cleaning.
        Indeed those aspects should be covered by the html_sanitize method
        located in tools. """
        root = lxml.html.fromstring(body)
        postprocessed = False
        to_remove = []
        for node in root.iter():
            if 'o_mail_notification' in (node.get('class') or '') or 'o_mail_notification' in (node.get('summary') or ''):
                postprocessed = True
                if node.getparent() is not None:
                    to_remove.append(node)
            if node.tag == 'img' and node.get('src', '').startswith('cid:'):
                cid = node.get('src').split(':', 1)[1]
                related_attachment = [attach for attach in attachments if attach[2] and attach[2].get('cid') == cid]
                if related_attachment:
                    node.set('data-filename', related_attachment[0][0])
                    postprocessed = True

        for node in to_remove:
            node.getparent().remove(node)
        if postprocessed:
            body = etree.tostring(root, pretty_print=False, encoding='UTF-8')
        return body, attachments

    def _message_extract_payload(self, message, save_original=False):
        """Extract body as HTML and attachments from the mail message"""
        attachments = []
        body = u''
        if save_original:
            attachments.append(self._Attachment('original_email.eml', message.as_string(), {}))

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

                # 0) Inline Attachments -> attachments, with a third part in the tuple to match cid / attachment
                if filename and part.get('content-id'):
                    inner_cid = part.get('content-id').strip('><')
                    attachments.append(self._Attachment(filename, part.get_payload(decode=True), {'cid': inner_cid}))
                    continue
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    attachments.append(self._Attachment(filename or 'attachment', part.get_payload(decode=True), {}))
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
                    attachments.append(self._Attachment(filename or 'attachment', part.get_payload(decode=True), {}))

        body, attachments = self._message_extract_payload_postprocess(message, body, attachments)
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
            'message_type': 'email',
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
            parent_ids = self.env['mail.message'].search([('message_id', '=', decode(message['In-Reply-To'].strip()))], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list = mail_header_msgid_re.findall(decode(message['References']))
            parent_ids = self.env['mail.message'].search([('message_id', 'in', [x.strip() for x in msg_list])], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        return msg_dict

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    @api.multi
    def _message_add_suggested_recipient(self, result, partner=None, email=None, reason=''):
        """ Called by message_get_suggested_recipients, to add a suggested
            recipient in the result dictionary. The form is :
                partner_id, partner_name<partner_email> or partner_name, reason """
        self.ensure_one()
        if email and not partner:
            # get partner info from email
            partner_info = self.message_partner_info_from_emails([email])[0]
            if partner_info.get('partner_id'):
                partner = self.env['res.partner'].sudo().browse([partner_info['partner_id']])[0]
        if email and email in [val[1] for val in result[self.ids[0]]]:  # already existing email -> skip
            return result
        if partner and partner in self.message_partner_ids:  # recipient already in the followers -> skip
            return result
        if partner and partner.id in [val[0] for val in result[self.ids[0]]]:  # already existing partner ID -> skip
            return result
        if partner and partner.email:  # complete profile: id, name <email>
            result[self.ids[0]].append((partner.id, '%s<%s>' % (partner.name, partner.email), reason))
        elif partner:  # incomplete profile: id, name
            result[self.ids[0]].append((partner.id, '%s' % (partner.name), reason))
        else:  # unknown partner, we are probably managing an email address
            result[self.ids[0]].append((False, email, reason))
        return result

    @api.multi
    def message_get_suggested_recipients(self):
        """ Returns suggested recipients for ids. Those are a list of
        tuple (partner_id, partner_name, reason), to be managed by Chatter. """
        result = dict((res_id, []) for res_id in self.ids)
        if 'user_id' in self._fields:
            for obj in self.sudo():  # SUPERUSER because of a read on res.users that would crash otherwise
                if not obj.user_id or not obj.user_id.partner_id:
                    continue
                obj._message_add_suggested_recipient(result, partner=obj.user_id.partner_id, reason=self._fields['user_id'].string)
        return result

    @api.multi
    def _find_partner_from_emails(self, emails, res_model=None, res_id=None, check_followers=True, force_create=False):
        """ Utility method to find partners from email addresses. The rules are :
            1 - check in document (model | self, id) followers
            2 - try to find a matching partner that is also an user
            3 - try to find a matching partner
            4 - create a new one if force_create = True

            :param list emails: list of email addresses
            :param string model: model to fetch related record; by default self
                is used.
            :param boolean check_followers: check in document followers
            :param boolean force_create: create a new partner if not found
        """
        if res_model is None:
            res_model = self._name
        if res_id is None and self.ids:
            res_id = self.ids[0]
        followers = self.env['res.partner']
        if res_model and res_id:
            record = self.env[res_model].browse(res_id)
            if hasattr(record, 'message_partner_ids'):
                followers = record.message_partner_ids

        Partner = self.env['res.partner'].sudo()
        Users = self.env['res.users'].sudo()
        partner_ids = []

        for contact in emails:
            partner_id = False
            email_address = tools.email_split(contact)
            if not email_address:
                partner_ids.append(partner_id)
                continue
            email_address = email_address[0]
            # first try: check in document's followers
            for follower in followers:
                if follower.email == email_address:
                    partner_id = follower.id
                    break
            # second try: check in partners that are also users
            # Escape special SQL characters in email_address to avoid invalid matches
            email_address = (email_address.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_'))
            email_brackets = "<%s>" % email_address
            if not partner_id:
                # exact, case-insensitive match
                partners = Users.search([('email', '=ilike', email_address)], limit=1).mapped('partner_id')
                if not partners:
                    # if no match with addr-spec, attempt substring match within name-addr pair
                    partners = Users.search([('email', 'ilike', email_brackets)], limit=1).mapped('partner_id')
                if partners:
                    partner_id = partners[0].id
            # third try: check in partners
            if not partner_id:
                # exact, case-insensitive match
                partners = Partner.search([('email', '=ilike', email_address)], limit=1)
                if not partners:
                    # if no match with addr-spec, attempt substring match within name-addr pair
                    partners = Partner.search([('email', 'ilike', email_brackets)], limit=1)
                if partners:
                    partner_id = partners[0].id
            if not partner_id and force_create:
                partner_id = self.env['res.partner'].name_create(contact)[0]
            partner_ids.append(partner_id)
        return partner_ids

    @api.multi
    def message_partner_info_from_emails(self, emails, link_mail=False):
        """ Convert a list of emails into a list partner_ids and a list
            new_partner_ids. The return value is non conventional because
            it is meant to be used by the mail widget.

            :return dict: partner_ids and new_partner_ids """
        self.ensure_one()
        MailMessage = self.env['mail.message'].sudo()
        partner_ids = self._find_partner_from_emails(emails)
        result = list()
        for idx in range(len(emails)):
            email_address = emails[idx]
            partner_id = partner_ids[idx]
            partner_info = {'full_name': email_address, 'partner_id': partner_id}
            result.append(partner_info)
            # link mail with this from mail to the new partner id
            if link_mail and partner_info['partner_id']:
                # Escape special SQL characters in email_address to avoid invalid matches
                email_address = (email_address.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_'))
                email_brackets = "<%s>" % email_address
                MailMessage.search([
                    '|',
                    ('email_from', '=ilike', email_address),
                    ('email_from', 'ilike', email_brackets),
                    ('author_id', '=', False)
                ]).write({'author_id': partner_info['partner_id']})
        return result

    def _message_preprocess_attachments(self, attachments, attachment_ids, attach_model, attach_res_id):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``,
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param str attach_model: the model of the attachments parent record
        :param integer attach_res_id: the id of the attachments parent record
        """
        return self._message_post_process_attachments(attachments, attachment_ids, {'model': attach_model, 'res_id': attach_res_id})

    def _message_post_process_attachments(self, attachments, attachment_ids, message_data):
        IrAttachment, parameter_attachments = self.env['ir.attachment'], self.env['ir.attachment']
        m2m_attachment_ids = []
        cid_mapping = {}
        if attachment_ids:
            filtered_attachment_ids = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'mail.compose.message'),
                ('create_uid', '=', self._uid),
                ('id', 'in', attachment_ids)])
            if filtered_attachment_ids:
                filtered_attachment_ids.write({'res_model': message_data['model'], 'res_id': message_data['res_id']})
            m2m_attachment_ids += [(4, id) for id in attachment_ids]
        # Handle attachments parameter, that is a dictionary of attachments
        for attachment in attachments:
            cid = False
            if len(attachment) == 2:
                name, content = attachment
            elif len(attachment) == 3:
                name, content, info = attachment
                if info and info.get('cid'):
                    cid = info['cid']
                    cid_mapping[cid] = name
            else:
                continue
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            data_attach = {
                'name': name,
                'datas': base64.b64encode(str(content)),
                'datas_fname': cid or name,
                'description': name,
                'res_model': message_data['model'],
                'res_id': message_data['res_id'],
            }
            parameter_attachments |= IrAttachment.create(data_attach)
        m2m_attachment_ids += [(4, attach.id) for attach in parameter_attachments]

        if cid_mapping and message_data.get('body'):
            root = lxml.html.fromstring(tools.ustr(message_data['body']))
            postprocessed = False
            for node in root.iter('img'):
                if node.get('src', '').startswith('cid:'):
                    cid = node.get('src').split('cid:')[1]
                    fname = cid_mapping.get(cid, node.get('data-filename', ''))
                    attachment = parameter_attachments.filtered(lambda attachment: attachment.datas_fname == cid)
                    if not attachment:
                        attachment = parameter_attachments.filtered(lambda attachment: attachment.datas_fname == fname)
                    if attachment:
                        node.set('src', '/web/image/%s' % attachment.ids[0])
                        postprocessed = True
            if postprocessed:
                body = lxml.html.tostring(root, pretty_print=False, encoding='UTF-8')
                message_data['body'] = body

        return m2m_attachment_ids

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification',
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
        if self.ids and not self.ensure_one():
            raise exceptions.Warning(_('Invalid record set: should be called as model (without records) or on single-record recordset'))

        # if we're processing a message directly coming from the gateway, the destination model was
        # set in the context.
        model = False
        if self.ids:
            self.ensure_one()
            model = self._context.get('thread_model', False) if self._name == 'mail.thread' else self._name
            if model and model != self._name and hasattr(self.env[model], 'message_post'):
                RecordModel = self.env[model].with_context(thread_model=None)  # TDE: was removing the key ?
                return RecordModel.browse(self.ids).message_post(
                    body=body, subject=subject, message_type=message_type,
                    subtype=subtype, parent_id=parent_id, attachments=attachments,
                    content_subtype=content_subtype, **kwargs)

        # 0: Find the message's author, because we need it for private discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.env['mail.message']._get_default_author().id

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
            parent_message = self.env['mail.message'].browse(parent_id)
            private_followers = set([partner.id for partner in parent_message.partner_ids])
            if parent_message.author_id:
                private_followers.add(parent_message.author_id.id)
            private_followers -= set([author_id])
            partner_ids |= private_followers

        # 4: mail.message.subtype
        subtype_id = kwargs.get('subtype_id', False)
        if not subtype_id:
            subtype = subtype or 'mt_note'
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype)

        # automatically subscribe recipients if asked to
        if self._context.get('mail_post_autofollow') and self.ids and partner_ids:
            partner_to_subscribe = partner_ids
            if self._context.get('mail_post_autofollow_partner_ids'):
                partner_to_subscribe = filter(lambda item: item in self._context.get('mail_post_autofollow_partner_ids'), partner_ids)
            self.message_subscribe(list(partner_to_subscribe), force=False)

        # _mail_flat_thread: automatically set free messages to the first posted message
        MailMessage = self.env['mail.message']
        if self._mail_flat_thread and model and not parent_id and self.ids:
            messages = MailMessage.search(['&', ('res_id', '=', self.ids[0]), ('model', '=', model), ('message_type', '=', 'email')], order="id ASC", limit=1)
            if not messages:
                messages = MailMessage.search(['&', ('res_id', '=', self.ids[0]), ('model', '=', model)], order="id ASC", limit=1)
            parent_id = messages and messages[0].id or False
        # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            messages = MailMessage.sudo().search([('id', '=', parent_id), ('parent_id', '!=', False)], limit=1)
            # avoid loops when finding ancestors
            processed_list = []
            if messages:
                message = messages[0]
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id

        values = kwargs
        values.update({
            'author_id': author_id,
            'model': model,
            'res_id': model and self.ids[0] or False,
            'body': body,
            'subject': subject or False,
            'message_type': message_type,
            'parent_id': parent_id,
            'subtype_id': subtype_id,
            'partner_ids': [(4, pid) for pid in partner_ids],
        })

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_post_process_attachments(attachments, kwargs.pop('attachment_ids', []), values)
        values['attachment_ids'] = attachment_ids

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        new_message = MailMessage.create(values)

        # Post-process: subscribe author, update message_last_post
        # Note: the message_last_post mechanism is no longer used.  This
        # will be removed in a later version.
        if (self._context.get('mail_save_message_last_post') and
                model and model != 'mail.thread' and self.ids and subtype_id):
            subtype_rec = self.env['mail.message.subtype'].sudo().browse(subtype_id)
            if not subtype_rec.internal:
                # done with SUPERUSER_ID, because on some models users can post only with read access, not necessarily write access
                self.sudo().write({'message_last_post': fields.Datetime.now()})
        if new_message.author_id and model and self.ids and message_type != 'notification' and not self._context.get('mail_create_nosubscribe'):
            self.message_subscribe([new_message.author_id.id], force=False)
        return new_message

    @api.multi
    def message_post_with_view(self, views_or_xmlid, **kwargs):
        """ Helper method to send a mail / post a message using a view_id to
        render using the ir.qweb engine. This method is stand alone, because
        there is nothing in template and composer that allows to handle
        views in batch. This method should probably disappear when templates
        handle ir ui views. """
        values = kwargs.pop('values', None) or dict()
        try:
            from openerp.addons.website.models.website import slug
            values['slug'] = slug
        except ImportError:
            values['slug'] = lambda self: self.id
        if isinstance(views_or_xmlid, basestring):
            views = self.env.ref(views_or_xmlid, raise_if_not_found=False)
        else:
            views = views_or_xmlid
        if not views:
            return
        for record in self:
            values['object'] = record
            rendered_template = views.render(values, engine='ir.qweb')
            kwargs['body'] = rendered_template
            record.message_post_with_template(False, **kwargs)

    @api.multi
    def message_post_with_template(self, template_id, **kwargs):
        """ Helper method to send a mail with a template
            :param template_id : the id of the template to render to create the body of the message
            :param **kwargs : parameter to create a mail.compose.message woaerd (which inherit from mail.message)
        """
        # Get composition mode, or force it according to the number of record in self
        if not kwargs.get('composition_mode'):
            kwargs['composition_mode'] = 'comment' if len(self.ids) == 1 else 'mass_mail'
        if not kwargs.get('message_type'):
            kwargs['message_type'] = 'notification'
        res_id = self.ids[0] or 0

        # Create the composer
        composer = self.env['mail.compose.message'].with_context(
            active_ids=self.ids,
            active_model=self._name,
            default_composition_mode=kwargs['composition_mode'],
            default_model=self._name,
            default_res_id=self.ids[0] or 0,
            default_template_id=template_id,
        ).create(kwargs)
        # Simulate the onchange (like trigger in form the view) only
        # when having a template in single-email mode
        if template_id:
            update_values = composer.onchange_template_id(template_id, kwargs['composition_mode'], self._name, res_id)['value']
            composer.write(update_values)
        return composer.send_mail()

    # ------------------------------------------------------
    # Followers API
    # ------------------------------------------------------

    @api.multi
    def message_subscribe_users(self, user_ids=None, subtype_ids=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, subscribe uid instead. """
        if user_ids is None:
            user_ids = [self._uid]
        return self.message_subscribe(self.env['res.users'].browse(user_ids).mapped('partner_id').ids, subtype_ids=subtype_ids)

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        """ Add partners to the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids and not channel_ids:
            return True
        if partner_ids is None:
            partner_ids = []
        if channel_ids is None:
            channel_ids = []

        # TDE CHECK THIS
        if not channel_ids and partner_ids and set(partner_ids) == set([self.env.user.partner_id.id]):
            try:
                self.check_access_rights('read')
                self.check_access_rule('read')
            except exceptions.AccessError:
                return False
        else:
            self.check_access_rights('write')
            self.check_access_rule('write')

        partner_data = dict((pid, subtype_ids) for pid in partner_ids)
        channel_data = dict((cid, subtype_ids) for cid in channel_ids)
        gen, part = self.env['mail.followers']._add_follower_command(self._name, self.ids, partner_data, channel_data, force=force)
        self.sudo().write({'message_follower_ids': gen})
        for record in self.filtered(lambda self: self.id in part):
            record.write({'message_follower_ids': part[record.id]})

        self.invalidate_cache()
        return True

    @api.multi
    def message_unsubscribe_users(self, user_ids=None):
        """ Wrapper on message_subscribe, using users. If user_ids is not
            provided, unsubscribe uid instead. """
        if user_ids is None:
            user_ids = [self._uid]
        partner_ids = [user.partner_id.id for user in self.env['res.users'].browse(user_ids)]
        return self.message_unsubscribe(partner_ids)

    @api.multi
    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        """ Remove partners from the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids and not channel_ids:
            return True
        user_pid = self.env.user.partner_id.id
        if not channel_ids and set(partner_ids) == set([user_pid]):
            self.check_access_rights('read')
            self.check_access_rule('read')
        else:
            self.check_access_rights('write')
            self.check_access_rule('write')
        self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            '|',
            ('partner_id', 'in', partner_ids or []),
            ('channel_id', 'in', channel_ids or [])
        ]).unlink()

    @api.model
    def _message_get_auto_subscribe_fields(self, updated_fields, auto_follow_fields=None):
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

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids):
        """ Notify newly subscribed followers of the last posted message.
            :param partner_ids : the list of partner to add as needaction partner of the last message
                                 (This excludes the current partner)
        """
        if not partner_ids:
            return
        for record_id in self.ids:
            messages = self.env['mail.message'].sudo().search([
                ('model', '=', self._name),
                ('res_id', '=', record_id),
                ('subtype_id', '!=', False),
                ('subtype_id.internal', '=', False)], limit=1)
            if messages:
                messages.write({'needaction_partner_ids': [(4, pid) for pid in partner_ids]})

    @api.multi
    def message_auto_subscribe(self, updated_fields, values=None):
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
        new_partners, new_channels = dict(), dict()

        # fetch auto_follow_fields: res.users relation fields whose changes are tracked for subscription
        user_field_lst = self._message_get_auto_subscribe_fields(updated_fields)

        # fetch header subtypes
        subtypes = self.env['mail.message.subtype'].search(['|', ('res_model', '=', False), ('parent_id.res_model', '=', self._name)])

        # if no change in tracked field or no change in tracked relational field: quit
        relation_fields = set([subtype.relation_field for subtype in subtypes if subtype.relation_field is not False])
        if not any(relation in updated_fields for relation in relation_fields) and not user_field_lst:
            return True

        # legacy behavior: if values is not given, compute the values by browsing
        # @TDENOTE: remove me in 8.0
        if values is None:
            record = self[0]
            for updated_field in updated_fields:
                field_value = getattr(record, updated_field)
                if isinstance(field_value, models.BaseModel):
                    field_value = field_value.id
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
            for header_follower in self.env['mail.followers'].sudo().search(header_domain):
                for subtype in header_follower.subtype_ids:
                    if subtype.parent_id and subtype.parent_id.res_model == self._name:
                        new_subtype = subtype.parent_id
                    elif subtype.res_model is False:
                        new_subtype = subtype
                    else:
                        continue
                    if header_follower.partner_id:
                        new_partners.setdefault(header_follower.partner_id.id, set()).add(new_subtype.id)
                    else:
                        new_channels.setdefault(header_follower.channel_id.id, set()).add(new_subtype.id)

        # add followers coming from res.users relational fields that are tracked
        user_ids = [values[name] for name in user_field_lst if values.get(name)]
        user_pids = [user.partner_id.id for user in self.env['res.users'].sudo().browse(user_ids)]
        for partner_id in user_pids:
            new_partners.setdefault(partner_id, None)

        for pid, subtypes in new_partners.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(partner_ids=[pid], subtype_ids=subtypes, force=(subtypes != None))
        for cid, subtypes in new_channels.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(channel_ids=[cid], subtype_ids=subtypes, force=(subtypes != None))

        # remove the current user from the needaction partner to avoid to notify the author of the message
        user_pids = [user_pid for user_pid in user_pids if user_pid != self.env.user.partner_id.id]
        self._message_auto_subscribe_notify(user_pids)

        return True

    # ------------------------------------------------------
    # Thread management
    # ------------------------------------------------------

    @api.multi
    def message_set_read(self):
        messages = self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids), ('needaction', '=', True)])
        messages.write({'needaction_partner_ids': [(3, self.env.user.partner_id.id)]})
        return messages.ids

    @api.multi
    def message_change_thread(self, new_thread):
        """
        Transfer the list of the mail thread messages from an model to another

        :param id : the old res_id of the mail.message
        :param new_res_id : the new res_id of the mail.message
        :param new_model : the name of the new model of the mail.message

        Example :   my_lead.message_change_thread(my_project_issue)
                    will transfer the context of the thread of my_lead to my_project_issue
        """
        self.ensure_one()
        # get the subtype of the comment Message
        subtype_comment = self.env.ref('mail.mt_comment')

        # get the ids of the comment and not-comment of the thread
        # TDE check: sudo on mail.message, to be sure all messages are moved ?
        MailMessage = self.env['mail.message']
        msg_comment = MailMessage.search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('subtype_id', '=', subtype_comment.id)])
        msg_not_comment = MailMessage.search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('subtype_id', '!=', subtype_comment.id)])

        # update the messages
        msg_comment.write({"res_id": new_thread.id, "model": new_thread._name})
        msg_not_comment.write({"res_id": new_thread.id, "model": new_thread._name, "subtype_id": None})
        return True

    # ------------------------------------------------------
    # Mass mailing
    # ------------------------------------------------------

    def message_mass_mailing_enabled(self):
        if self._mail_mass_mailing:
            # TODO master properly translate
            # the _mail_mass_mailing is evaluted at code start so not translated
            return _(self._mail_mass_mailing)
