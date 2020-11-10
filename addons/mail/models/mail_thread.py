# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import dateutil
import email
import hashlib
import hmac
import lxml
import logging
import pytz
import re
import socket
import time
import threading
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

from collections import namedtuple
from email.message import Message
from lxml import etree
from werkzeug import url_encode
from werkzeug import urls

from odoo import _, api, exceptions, fields, models, tools, registry, SUPERUSER_ID
from odoo.osv import expression

from odoo.tools import pycompat, ustr
from odoo.tools.misc import clean_context, split_every
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    ''' mail_thread model is meant to be inherited by any model that needs to
        act as a discussion topic on which messages can be attached. Public
        methods are prefixed with ``message_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.

        ``mail.thread`` defines fields used to handle and display the
        communication history. ``mail.thread`` also manages followers of
        inheriting classes. All features and expected behavior are managed
        by mail.thread. Widgets has been designed for the 7.0 and following
        versions of Odoo.

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
     - ``mail_notify_force_send``: if less than 50 email notifications to send,
       send them directly instead of using the queue; True by default
    '''
    _name = 'mail.thread'
    _description = 'Email Thread'
    _mail_flat_thread = True  # flatten the discussino history
    _mail_post_access = 'write'  # access required on the document to post on it
    _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))

    message_is_follower = fields.Boolean(
        'Is Follower', compute='_compute_is_follower', search='_search_is_follower')
    message_follower_ids = fields.One2many(
        'mail.followers', 'res_id', string='Followers')
    message_partner_ids = fields.Many2many(
        comodel_name='res.partner', string='Followers (Partners)',
        compute='_get_followers', search='_search_follower_partners')
    message_channel_ids = fields.Many2many(
        comodel_name='mail.channel', string='Followers (Channels)',
        compute='_get_followers', search='_search_follower_channels')
    message_ids = fields.One2many(
        'mail.message', 'res_id', string='Messages',
        domain=lambda self: [('message_type', '!=', 'user_notification')], auto_join=True)
    message_unread = fields.Boolean(
        'Unread Messages', compute='_get_message_unread',
        help="If checked, new messages require your attention.")
    message_unread_counter = fields.Integer(
        'Unread Messages Counter', compute='_get_message_unread',
        help="Number of unread messages")
    message_needaction = fields.Boolean(
        'Action Needed', compute='_get_message_needaction', search='_search_message_needaction',
        help="If checked, new messages require your attention.")
    message_needaction_counter = fields.Integer(
        'Number of Actions', compute='_get_message_needaction',
        help="Number of messages which requires an action")
    message_has_error = fields.Boolean(
        'Message Delivery error', compute='_compute_message_has_error', search='_search_message_has_error',
        help="If checked, some messages have a delivery error.")
    message_has_error_counter = fields.Integer(
        'Number of errors', compute='_compute_message_has_error',
        help="Number of messages with delivery error")
    message_attachment_count = fields.Integer('Attachment Count', compute='_compute_message_attachment_count', groups="base.group_user")
    message_main_attachment_id = fields.Many2one(string="Main Attachment", comodel_name='ir.attachment', index=True, copy=False)

    @api.depends('message_follower_ids')
    def _get_followers(self):
        for thread in self:
            thread.message_partner_ids = thread.message_follower_ids.mapped('partner_id')
            thread.message_channel_ids = thread.message_follower_ids.mapped('channel_id')

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
        # using read() below is much faster than followers.mapped('res_id')
        return [('id', 'in', [res['res_id'] for res in followers.read(['res_id'])])]

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
        # using read() below is much faster than followers.mapped('res_id')
        return [('id', 'in', [res['res_id'] for res in followers.read(['res_id'])])]

    @api.depends('message_follower_ids')
    def _compute_is_follower(self):
        followers = self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
            ])
        # using read() below is much faster than followers.mapped('res_id')
        following_ids = [res['res_id'] for res in followers.read(['res_id'])]
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
            # using read() below is much faster than followers.mapped('res_id')
            return [('id', 'in', [res['res_id'] for res in followers.read(['res_id'])])]
        else:
            # using read() below is much faster than followers.mapped('res_id')
            return [('id', 'not in', [res['res_id'] for res in followers.read(['res_id'])])]

    def _get_message_unread(self):
        partner_id = self.env.user.partner_id.id
        res = dict.fromkeys(self.ids, 0)
        if self.ids:
            # search for unread messages, directly in SQL to improve performances
            self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                                 RIGHT JOIN mail_message_mail_channel_rel rel
                                 ON rel.mail_message_id = msg.id
                                 RIGHT JOIN mail_channel_partner cp
                                 ON (cp.channel_id = rel.mail_channel_id AND cp.partner_id = %s AND
                                    (cp.seen_message_id IS NULL OR cp.seen_message_id < msg.id))
                                 WHERE msg.model = %s AND msg.res_id = ANY(%s) AND
                                        msg.message_type != 'user_notification' AND
                                       (msg.author_id IS NULL OR msg.author_id != %s) AND
                                       (msg.message_type not in ('notification', 'user_notification') OR msg.model != 'mail.channel')""",
                             (partner_id, self._name, list(self.ids), partner_id,))
            for result in self._cr.fetchall():
                res[result[0]] += 1

        for record in self:
            record.message_unread_counter = res.get(record._origin.id, 0)
            record.message_unread = bool(record.message_unread_counter)

    def _get_message_needaction(self):
        res = dict.fromkeys(self.ids, 0)
        if self.ids:
            # search for unread messages, directly in SQL to improve performances
            self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                                 RIGHT JOIN mail_message_res_partner_needaction_rel rel
                                 ON rel.mail_message_id = msg.id AND rel.res_partner_id = %s AND (rel.is_read = false OR rel.is_read IS NULL)
                                 WHERE msg.model = %s AND msg.res_id in %s AND msg.message_type != 'user_notification'""",
                             (self.env.user.partner_id.id, self._name, tuple(self.ids),))
            for result in self._cr.fetchall():
                res[result[0]] += 1

        for record in self:
            record.message_needaction_counter = res.get(record._origin.id, 0)
            record.message_needaction = bool(record.message_needaction_counter)

    @api.model
    def _search_message_needaction(self, operator, operand):
        return [('message_ids.needaction', operator, operand)]

    def _compute_message_has_error(self):
        res = {}
        if self.ids:
            self._cr.execute(""" SELECT msg.res_id, COUNT(msg.res_id) FROM mail_message msg
                                 RIGHT JOIN mail_message_res_partner_needaction_rel rel
                                 ON rel.mail_message_id = msg.id AND rel.notification_status in ('exception','bounce')
                                 WHERE msg.author_id = %s AND msg.model = %s AND msg.res_id in %s AND msg.message_type != 'user_notification'
                                 GROUP BY msg.res_id""",
                             (self.env.user.partner_id.id, self._name, tuple(self.ids),))
            res.update(self._cr.fetchall())

        for record in self:
            record.message_has_error_counter = res.get(record._origin.id, 0)
            record.message_has_error = bool(record.message_has_error_counter)

    @api.model
    def _search_message_has_error(self, operator, operand):
        return ['&', ('message_ids.has_error', operator, operand), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    def _compute_message_attachment_count(self):
        read_group_var = self.env['ir.attachment'].read_group([('res_id', 'in', self.ids), ('res_model', '=', self._name)],
                                                              fields=['res_id'],
                                                              groupby=['res_id'])

        attachment_count_dict = dict((d['res_id'], d['res_id_count']) for d in read_group_var)
        for record in self:
            record.message_attachment_count = attachment_count_dict.get(record.id, 0)

    # ------------------------------------------------------
    # CRUD overrides for automatic subscription and logging
    # ------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ Chatter override :
            - subscribe uid
            - subscribe followers of parent
            - log a creation message
        """
        if self._context.get('tracking_disable'):
            return super(MailThread, self).create(vals_list)

        # subscribe uid unless asked not to
        if not self._context.get('mail_create_nosubscribe'):
            default_followers = self.env['mail.followers']._add_default_followers(self._name, [], self.env.user.partner_id.ids, customer_ids=[])[0][0]
            for values in vals_list:
                message_follower_ids = values.get('message_follower_ids') or []
                message_follower_ids += [(0, 0, fol_vals) for fol_vals in default_followers]
                values['message_follower_ids'] = message_follower_ids

        threads = super(MailThread, self).create(vals_list)

        # auto_subscribe: take values and defaults into account
        create_values_list = {}
        for thread, values in zip(threads, vals_list):
            create_values = dict(values)
            for key, val in self._context.items():
                if key.startswith('default_') and key[8:] not in create_values:
                    create_values[key[8:]] = val
            thread._message_auto_subscribe(create_values)
            create_values_list[thread.id] = create_values

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not self._context.get('mail_create_nolog'):
            threads_no_subtype = self.env[self._name]
            for thread in threads:
                body = thread._get_creation_message()
                subtype = thread._creation_subtype()
                if subtype:  # if we have a subtype, post message to notify users from _message_auto_subscribe
                    thread.sudo().message_post(body=body, subtype_id=subtype.id, author_id=self.env.user.partner_id.id)
                else:
                    threads_no_subtype += thread
            if threads_no_subtype:
                threads_no_subtype._message_log_batch(bodies={t.id: body for t in threads_no_subtype})

        # post track template if a tracked field changed
        if not self._context.get('mail_notrack'):
            track_threads = threads.with_lang()
            tracked_fields = self._get_tracked_fields()
            for thread in track_threads:
                create_values = create_values_list[thread.id]
                changes = [field for field in tracked_fields if create_values.get(field)]
                # based on tracked field to stay consistent with write
                # we don't consider that a falsy field is a change, to stay consistent with previous implementation,
                # but we may want to change that behaviour later.
                thread._message_track_post_template(changes)

        return threads

    def write(self, values):
        if self._context.get('tracking_disable'):
            return super(MailThread, self).write(values)

        # Track initial values of tracked fields
        track_self = self.with_lang()

        tracked_fields = None
        if not self._context.get('mail_notrack'):
            tracked_fields = track_self._get_tracked_fields()
        if tracked_fields:
            initial_values = dict((record.id, dict((key, getattr(record, key)) for key in tracked_fields))
                                  for record in track_self)

        # Perform write
        result = super(MailThread, self).write(values)

        # update followers
        self._message_auto_subscribe(values)

        # Perform the tracking
        if tracked_fields:
            tracking = track_self.with_context(clean_context(self._context)).message_track(tracked_fields, initial_values)
            if any(change for rec_id, (change, tracking_value_ids) in tracking.items()):
                (changes, tracking_value_ids) = tracking[track_self[0].id]
                track_self._message_track_post_template(changes)
        return result

    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids)]).sudo().unlink()
        res = super(MailThread, self).unlink()
        self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        ).unlink()
        return res

    def copy_data(self, default=None):
        # avoid tracking multiple temporary changes during copy
        return super(MailThread, self.with_context(mail_notrack=True)).copy_data(default=default)

    @api.model
    def get_empty_list_help(self, help):
        """ Override of BaseModel.get_empty_list_help() to generate an help message
        that adds alias information. """
        model = self._context.get('empty_list_help_model')
        res_id = self._context.get('empty_list_help_id')
        catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        document_name = self._context.get('empty_list_help_document_name', _('document'))
        nothing_here = not help
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
            email_link = "<a href='mailto:%(email)s'>%(email)s</a>" % {'email': alias.display_name}
            if nothing_here:
                return "<p class='o_view_nocontent_smiling_face'>%(dyn_help)s</p>" % {
                    'dyn_help': _("Add a new %(document)s or send an email to %(email_link)s") % {
                        'document': document_name,
                        'email_link': email_link
                    }
                }
            # do not add alias two times if it was added previously
            if "oe_view_nocontent_alias" not in help:
                return "%(static_help)s<p class='oe_view_nocontent_alias'>%(dyn_help)s</p>" % {
                    'static_help': help,
                    'dyn_help': _("Create a new %(document)s by sending an email to %(email_link)s") %  {
                        'document': document_name,
                        'email_link': email_link,
                    }
                }

        if nothing_here:
            return "<p class='o_view_nocontent_smiling_face'>%(dyn_help)s</p>" % {
                'dyn_help': _("Create a new %(document)s") % {
                    'document': document_name,
                }
            }

        return help

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(MailThread, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']"):
                # the 'Log a note' button is employee only
                options = safe_eval(node.get('options', '{}'))
                is_employee = self.env.user.has_group('base.group_user')
                options['display_log_button'] = is_employee
                # save options on the node
                node.set('options', repr(options))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    # ------------------------------------------------------
    # Technical methods / wrappers / tools
    # ------------------------------------------------------

    def with_lang(self):
        if not self._context.get("lang"):
            return self.with_context(lang=self.env.user.lang)
        return self

    def _replace_local_links(self, html, base_url=None):
        """ Replace local links by absolute links. It is required in various
        cases, for example when sending emails on chatter or sending mass
        mailings. It replaces

         * href of links (mailto will not match the regex)
         * src of images (base64 hardcoded data will not match the regex)
         * styling using url like background-image: url

        It is done using regex because it is shorten than using an html parser
        to create a potentially complex soupe and hope to have a result that
        has not been harmed.
        """
        if not html:
            return html

        html = ustr(html)

        def _sub_relative2absolute(match):
            # compute here to do it only if really necessary + cache will ensure it is done only once
            # if not base_url
            if not _sub_relative2absolute.base_url:
                _sub_relative2absolute.base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            return match.group(1) + urls.url_join(_sub_relative2absolute.base_url, match.group(2))

        _sub_relative2absolute.base_url = base_url
        html = re.sub(r"""(<img(?=\s)[^>]*\ssrc=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<a(?=\s)[^>]*\shref=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<[^>]+\bstyle="[^"]+\burl\('?)(/[^/'][^'")]+)""", _sub_relative2absolute, html)

        return html

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
    def get_mail_message_access(self, res_ids, operation, model_name=None):
        """ mail.message check permission rules for related document. This method is
            meant to be inherited in order to implement addons-specific behavior.
            A common behavior would be to allow creating messages when having read
            access rule on the document, for portal document such as issues. """

        DocModel = self.env[model_name] if model_name else self
        create_allow = getattr(DocModel, '_mail_post_access', 'write')

        if operation in ['write', 'unlink']:
            check_operation = 'write'
        elif operation == 'create' and create_allow in ['create', 'read', 'write', 'unlink']:
            check_operation = create_allow
        elif operation == 'create':
            check_operation = 'write'
        else:
            check_operation = operation
        return check_operation

    def message_change_thread(self, new_thread):
        """
        Transfer the list of the mail thread messages from an model to another

        :param id : the old res_id of the mail.message
        :param new_res_id : the new res_id of the mail.message
        :param new_model : the name of the new model of the mail.message

        Example :   my_lead.message_change_thread(my_project_task)
                    will transfer the context of the thread of my_lead to my_project_task
        """
        self.ensure_one()
        # get the subtype of the comment Message
        subtype_comment = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        # get the ids of the comment and not-comment of the thread
        # TDE check: sudo on mail.message, to be sure all messages are moved ?
        MailMessage = self.env['mail.message']
        msg_comment = MailMessage.search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('message_type', '!=', 'user_notification'),
            ('subtype_id', '=', subtype_comment)])
        msg_not_comment = MailMessage.search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('message_type', '!=', 'user_notification'),
            ('subtype_id', '!=', subtype_comment)])

        # update the messages
        msg_comment.write({"res_id": new_thread.id, "model": new_thread._name})
        msg_not_comment.write({"res_id": new_thread.id, "model": new_thread._name, "subtype_id": None})
        return True

    # ------------------------------------------------------
    # Automatic log / Tracking
    # ------------------------------------------------------

    @api.model
    def _get_tracked_fields(self):
        """ Return a structure of tracked fields for the current model.
            :return dict: a dict mapping field name to description, containing on_change fields
        """
        tracked_fields = []
        for name, field in self._fields.items():
            tracking = getattr(field, 'tracking', None) or getattr(field, 'track_visibility', None)
            if tracking:
                tracked_fields.append(name)

        if tracked_fields:
            return self.fields_get(tracked_fields)
        return {}

    def _creation_subtype(self):
        """ Give the subtypes triggered by the creation of a record

        :returns: a subtype browse record (empty if no subtype is triggered)
        """
        return self.env['mail.message.subtype']

    def _get_creation_message(self):
        """ Get the creation message to log into the chatter at the record's creation.
        :returns: The message's body to log.
        """
        self.ensure_one()
        doc_name = self.env['ir.model']._get(self._name).name
        return _('%s created') % doc_name

    def _track_subtype(self, init_values):
        """ Give the subtypes triggered by the changes on the record according
        to values that have been updated.

        :param init_values: the original values of the record; only modified fields
                            are present in the dict
        :type init_values: dict
        :returns: a subtype browse record or False if no subtype is trigerred
        """
        return False

    def _track_template(self, changes):
        return dict()

    def _message_track_post_template(self, changes):
        if not changes:
            return True
        # Clean the context to get rid of residual default_* keys
        # that could cause issues afterward during the mail.message
        # generation. Example: 'default_parent_id' would refer to
        # the parent_id of the current record that was used during
        # its creation, but could refer to wrong parent message id,
        # leading to a traceback in case the related message_id
        # doesn't exist
        self = self.with_context(clean_context(self._context))
        templates = self._track_template(changes)
        for field_name, (template, post_kwargs) in templates.items():
            if not template:
                continue
            if isinstance(template, str):
                self.message_post_with_view(template, **post_kwargs)
            else:
                self.message_post_with_template(template.id, **post_kwargs)
        return True

    def _message_track(self, tracked_fields, initial):
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a structure that is a tuple containing :

         - a set of updated column names
         - a list of ORM (0, 0, values) commands to create 'mail.tracking.value' """
        self.ensure_one()
        changes = set()  # contains onchange tracked fields that changed
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            initial_value = initial[col_name]
            new_value = self[col_name]

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                tracking_sequence = getattr(self._fields[col_name], 'tracking',
                                            getattr(self._fields[col_name], 'track_sequence', 100))  # backward compatibility with old parameter name
                if tracking_sequence is True:
                    tracking_sequence = 100
                tracking = self.env['mail.tracking.value'].create_tracking_values(initial_value, new_value, col_name, col_info, tracking_sequence)
                if tracking:
                    tracking_value_ids.append([0, 0, tracking])
                changes.add(col_name)

        return changes, tracking_value_ids

    def message_track(self, tracked_fields, initial_values):
        """ Track updated values. Comparing the initial and current values of
        the fields given in tracked_fields, it generates a message containing
        the updated values. This message can be linked to a mail.message.subtype
        given by the ``_track_subtype`` method. """
        if not tracked_fields:
            return True

        tracking = dict()
        for record in self:
            tracking[record.id] = record._message_track(tracked_fields, initial_values[record.id])

        for record in self:
            changes, tracking_value_ids = tracking[record.id]
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtype = False
            # By passing this key, that allows to let the subtype empty and so don't sent email because partners_to_notify from mail_message._notify will be empty
            if not self._context.get('mail_track_log_only'):
                subtype = record._track_subtype(dict((col_name, initial_values[record.id][col_name]) for col_name in changes))
            if subtype:
                if not subtype.exists():
                    _logger.debug('subtype "%s" not found' % subtype.name)
                    continue
                record.message_post(subtype_id=subtype.id, tracking_value_ids=tracking_value_ids)
            elif tracking_value_ids:
                record._message_log(tracking_value_ids=tracking_value_ids)

        return tracking

    # ------------------------------------------------------
    # Mail gateway
    # ------------------------------------------------------

    def _routing_warn(self, error_message, message_id, route, raise_exception=True):
        """ Tools method used in _routing_check_route: whether to log a warning or raise an error """
        short_message = _("Mailbox unavailable - %s") % error_message
        full_message = ('Routing mail with Message-Id %s: route %s: %s' %
                        (message_id, route, error_message))
        _logger.info(full_message)
        if raise_exception:
            # sender should not see private diagnostics info, just the error
            raise ValueError(short_message)

    def _routing_create_bounce_email(self, email_from, body_html, message, **mail_values):
        bounce_to = tools.decode_message_header(message, 'Return-Path') or email_from
        bounce_mail_values = {
            'body_html': body_html,
            'subject': 'Re: %s' % message.get('subject'),
            'email_to': bounce_to,
            'auto_delete': True,
        }
        bounce_from = self.env['ir.mail_server']._get_default_bounce_address()
        if bounce_from:
            bounce_mail_values['email_from'] = 'MAILER-DAEMON <%s>' % bounce_from
        bounce_mail_values.update(mail_values)
        self.env['mail.mail'].create(bounce_mail_values).send()

    @api.model
    def _routing_handle_bounce(self, email_message, message_dict):
        """ Handle bounce of incoming email. Based on values of the bounce (email
        and related partner, send message and its messageID)

          * find blacklist-enabled records with email_normalized = bounced email
            and call ``_message_receive_bounce`` on each of them to propagate
            bounce information through various records linked to same email;
          * if not already done (i.e. if original record is not blacklist enabled
            like a bounce on an applicant), find record linked to bounced message
            and call ``_message_receive_bounce``;

        :param email_message: incoming email;
        :type email_message: email.message;
        :param message_dict: dictionary holding already-parsed values and in
            which bounce-related values will be added;
        :type message_dict: dictionary;
        """
        bounced_record, bounced_record_done = False, False
        bounced_email, bounced_partner = message_dict['bounced_email'], message_dict['bounced_partner']
        bounced_msg_id, bounced_message = message_dict['bounced_msg_id'], message_dict['bounced_message']

        if bounced_email:
            bounced_model, bounced_res_id = bounced_message.model, bounced_message.res_id

            if bounced_model and bounced_model in self.env and bounced_res_id:
                bounced_record = self.env[bounced_model].sudo().browse(bounced_res_id).exists()

            bl_models = self.env['ir.model'].sudo().search(['&', ('is_mail_blacklist', '=', True), ('model', '!=', 'mail.thread.blacklist')])
            for model in [bl_model for bl_model in bl_models if bl_model.model in self.env]:  # transient test mode
                rec_bounce_w_email = self.env[model.model].sudo().search([('email_normalized', '=', bounced_email)])
                rec_bounce_w_email._message_receive_bounce(bounced_email, bounced_partner)
                bounced_record_done = bool(bounced_record and model.model == bounced_model and bounced_record in rec_bounce_w_email)

            # set record as bounced unless already done due to blacklist mixin
            if bounced_record and not bounced_record_done and issubclass(type(bounced_record), self.pool['mail.thread']):
                bounced_record._message_receive_bounce(bounced_email, bounced_partner)

            if bounced_partner and bounced_message:
                self.env['mail.notification'].sudo().search([
                    ('mail_message_id', '=', bounced_message.id),
                    ('res_partner_id', 'in', bounced_partner.ids)]
                ).write({'notification_status': 'bounce'})

        if bounced_record:
            _logger.info('Routing mail from %s to %s with Message-Id %s: not routing bounce email from %s replying to %s (model %s ID %s)',
                         message_dict['email_from'], message_dict['to'], message_dict['message_id'], bounced_email, bounced_msg_id, bounced_model, bounced_res_id)
        elif bounced_email:
            _logger.info('Routing mail from %s to %s with Message-Id %s: not routing bounce email from %s replying to %s (no document found)',
                         message_dict['email_from'], message_dict['to'], message_dict['message_id'], bounced_email, bounced_msg_id)
        else:
            _logger.info('Routing mail from %s to %s with Message-Id %s: not routing bounce email.',
                         message_dict['email_from'], message_dict['to'], message_dict['message_id'])

    @api.model
    def _routing_check_route(self, message, message_dict, route, raise_exception=True):
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

        :param message: an email.message instance
        :param message_dict: dictionary of values that will be given to
                             mail_message.create()
        :param route: route to check which is a tuple (model, thread_id,
                      custom_values, uid, alias)
        :param raise_exception: if an error occurs, tell whether to raise an error
                                or just log a warning and try other processing or
                                invalidate route
        """

        assert isinstance(route, (list, tuple)), 'A route should be a list or a tuple'
        assert len(route) == 5, 'A route should contain 5 elements: model, thread_id, custom_values, uid, alias record'

        message_id = message_dict['message_id']
        email_from = message_dict['email_from']
        author_id = message_dict.get('author_id')
        model, thread_id, alias = route[0], route[1], route[4]
        record_set = None

        _generic_bounce_body_html = """<div>
<p>Hello,</p>
<p>The following email sent to %s cannot be accepted because this is a private email address.
   Only allowed people can contact us at this address.</p>
</div><blockquote>%s</blockquote>""" % (message_dict.get('to'), message_dict.get('body'))

        # Wrong model
        if not model:
            self._routing_warn(_('target model unspecified'), message_id, route, raise_exception)
            return ()
        elif model not in self.env:
            self._routing_warn(_('unknown target model %s') % model, message_id, route, raise_exception)
            return ()
        record_set = self.env[model].browse(thread_id) if thread_id else self.env[model]

        # Existing Document: check if exists and model accepts the mailgateway; if not, fallback on create if allowed
        if thread_id:
            if not record_set.exists():
                self._routing_warn(_('reply to missing document (%s,%s), fall back on document creation') % (model, thread_id), message_id, route, False)
                thread_id = None
            elif not hasattr(record_set, 'message_update'):
                self._routing_warn(_('reply to model %s that does not accept document update, fall back on document creation') % model, message_id, route, False)
                thread_id = None

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(record_set, 'message_new'):
            self._routing_warn(_('model %s does not accept document creation') % model, message_id, route, raise_exception)
            return ()

        # Update message author if asked. We do it now because we need it for aliases (contact settings)
        if not author_id:
            if record_set:
                authors = self._mail_find_partner_from_emails([email_from], records=record_set)
            elif alias and alias.alias_parent_model_id and alias.alias_parent_thread_id:
                records = self.env[alias.alias_parent_model_id.model].browse(alias.alias_parent_thread_id)
                authors = self._mail_find_partner_from_emails([email_from], records=records)
            else:
                authors = self._mail_find_partner_from_emails([email_from], records=None)
            if authors:
                message_dict['author_id'] = authors[0].id

        # Alias: check alias_contact settings
        if alias:
            if thread_id:
                obj = record_set[0]
            elif alias.alias_parent_model_id and alias.alias_parent_thread_id:
                obj = self.env[alias.alias_parent_model_id.model].browse(alias.alias_parent_thread_id)
            else:
                obj = self.env[model]
            if hasattr(obj, '_alias_check_contact'):
                check_result = obj._alias_check_contact(message, message_dict, alias)
            else:
                check_result = self.env['mail.alias.mixin']._alias_check_contact_on_record(obj, message, message_dict, alias)
            if check_result is not True:
                self._routing_warn(_('alias %s: %s') % (alias.alias_name, check_result.get('error_message', _('unknown error'))), message_id, route, False)
                self._routing_create_bounce_email(email_from, check_result.get('error_template', _generic_bounce_body_html), message)
                return False

        return (model, thread_id, route[2], route[3], route[4])

    @api.model
    def _routing_reset_bounce(self, email_message, message_dict):
        """Called by ``message_process`` when a new mail is received from an email address.
        If the email is related to a partner, we consider that the number of message_bounce
        is not relevant anymore as the email is valid - as we received an email from this
        address. The model is here hardcoded because we cannot know with which model the
        incomming mail match. We consider that if a mail arrives, we have to clear bounce for
        each model having bounce count.

        :param email_from: email address that sent the incoming email."""
        valid_email = message_dict['email_from']
        if valid_email:
            bl_models = self.env['ir.model'].sudo().search(['&', ('is_mail_blacklist', '=', True), ('model', '!=', 'mail.thread.blacklist')])
            for model in [bl_model for bl_model in bl_models if bl_model.model in self.env]:  # transient test mode
                self.env[model.model].sudo().search([('message_bounce', '>', 0), ('email_normalized', '=', valid_email)])._message_reset_bounce(valid_email)

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:

         * if the message replies to an existing thread by having a Message-Id
           that matches an existing mail_message.message_id, we take the original
           message model/thread_id pair and ignore custom_value as no creation will
           take place;
         * look for a mail.alias entry matching the message recipients and use the
           corresponding model, thread_id, custom_values and user_id. This could
           lead to a thread update or creation depending on the alias;
         * fallback on provided ``model``, ``thread_id`` and ``custom_values``;
         * raise an exception as no route has been found

        :param string message: an email.message instance
        :param dict message_dict: dictionary holding parsed message variables
        :param string model: the fallback model to use if the message does not match
            any of the currently configured mail aliases (may be None if a matching
            alias is supposed to be present)
        :type dict custom_values: optional dictionary of default field values
            to pass to ``message_new`` if a new record needs to be created.
            Ignored if the thread record already exists, and also if a matching
            mail.alias was found (aliases define their own defaults)
        :param int thread_id: optional ID of the record/thread from ``model`` to
            which this mail should be attached. Only used if the message does not
            reply to an existing thread and does not match any mail alias.
        :return: list of routes [(model, thread_id, custom_values, user_id, alias)]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        fallback_model = model

        # get email.message.Message variables for future processing
        local_hostname = socket.gethostname()
        message_id = message_dict['message_id']

        # compute references to find if message is a reply to an existing thread
        thread_references = message_dict['references'] or message_dict['in_reply_to']
        msg_references = [ref for ref in tools.mail_header_msgid_re.findall(thread_references) if 'reply_to' not in ref]
        mail_messages = self.env['mail.message'].sudo().search([('message_id', 'in', msg_references)], limit=1, order='id desc, message_id')
        is_a_reply = bool(mail_messages)
        reply_model, reply_thread_id = mail_messages.model, mail_messages.res_id

        # author and recipients
        email_from = message_dict['email_from']
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = message_dict['to']
        email_to_localparts = [
            e.split('@', 1)[0].lower()
            for e in (tools.email_split(email_to) or [''])
        ]
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos_localparts = [
            e.split('@')[0].lower()
            for e in tools.email_split(message_dict['recipients'])
        ]
        rcpt_tos_valid_localparts = [to for to in rcpt_tos_localparts]

        # 0. Handle bounce: verify whether this is a bounced email and use it to collect bounce data and update notifications for customers
        #    Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
        #       group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID 
        #    Bounce message (not alias)
        #       See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #        As all MTA does not respect this RFC (googlemail is one of them),
        #       we also need to verify if the message come from "mailer-daemon"
        #    If not a bounce: reset bounce information
        if bounce_alias and any(email.startswith(bounce_alias) for email in email_to_localparts):
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                self._routing_handle_bounce(message, message_dict)
                return []
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            self._routing_handle_bounce(message, message_dict)
            return []
        self._routing_reset_bounce(message, message_dict)

        # 1. Handle reply
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        if reply_model and reply_thread_id:
            other_model_aliases = self.env['mail.alias'].search([
                '&', '&',
                ('alias_name', '!=', False),
                ('alias_name', 'in', email_to_localparts),
                ('alias_model_id.model', '!=', reply_model),
            ])
            if other_model_aliases:
                is_a_reply = False
                rcpt_tos_valid_localparts = [to for to in rcpt_tos_valid_localparts if to in other_model_aliases.mapped('alias_name')]

        if is_a_reply:
            dest_aliases = self.env['mail.alias'].search([
                ('alias_name', 'in', rcpt_tos_localparts),
                ('alias_model_id.model', '=', reply_model)
            ], limit=1)

            user_id = self._mail_find_user_for_gateway(email_from, alias=dest_aliases).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (reply_model, reply_thread_id, custom_values, user_id, dest_aliases),
                raise_exception=False)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, reply_model, reply_thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 2. Handle new incoming email by checking aliases and applying their settings
        if rcpt_tos_localparts:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and all(email_localpart == catchall_alias for email_localpart in email_to_localparts):
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env.ref('mail.mail_bounce_catchall').render({
                    'message': message,
                }, engine='ir.qweb')
                self._routing_create_bounce_email(email_from, body, message, reply_to=self.env.company.email)
                return []

            dest_aliases = self.env['mail.alias'].search([('alias_name', 'in', rcpt_tos_valid_localparts)])
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = self._mail_find_user_for_gateway(email_from, alias=alias).id or self._uid
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, safe_eval(alias.alias_defaults), user_id, alias)
                    route = self._routing_check_route(message, message_dict, route, raise_exception=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 3. Fallback to the provided parameters, if they work
        if fallback_model:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)
            user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (fallback_model, thread_id, custom_values, user_id, None),
                raise_exception=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                    email_from, email_to, message_id, fallback_model, thread_id, custom_values, user_id)
                return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        self = self.with_context(attachments_mime_plainxml=True) # import XML attachments as text
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        original_partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes or ():
            subtype_id = False
            Model = self.env[model].with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
            if not (thread_id and hasattr(Model, 'message_update') or hasattr(Model, 'message_new')):
                raise ValueError(
                    "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" %
                    (message_dict['message_id'], model)
                )

            # disabled subscriptions during message_new/update to avoid having the system user running the
            # email gateway become a follower of all inbound messages
            ModelCtx = Model.with_user(user_id).sudo()
            if thread_id and hasattr(ModelCtx, 'message_update'):
                thread = ModelCtx.browse(thread_id)
                thread.message_update(message_dict)
            else:
                # if a new thread is created, parent is irrelevant
                message_dict.pop('parent_id', None)
                thread = ModelCtx.message_new(message_dict, custom_values)
                thread_id = thread.id
                subtype_id = thread._creation_subtype().id

            # replies to internal message are considered as notes, but parent message
            # author is added in recipients to ensure he is notified of a private answer
            parent_message = False
            if message_dict.get('parent_id'):
                parent_message = self.env['mail.message'].sudo().browse(message_dict['parent_id'])
            partner_ids = []
            if not subtype_id:
                if message_dict.pop('internal', False):
                    subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')
                    if parent_message and parent_message.author_id:
                        partner_ids = [parent_message.author_id.id]
                else:
                    subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

            post_params = dict(subtype_id=subtype_id, partner_ids=partner_ids, **message_dict)
            # remove computational values not stored on mail.message and avoid warnings when creating it
            for x in ('from', 'to', 'cc', 'recipients', 'references', 'in_reply_to', 'bounced_email', 'bounced_message', 'bounced_msg_id', 'bounced_partner'):
                post_params.pop(x, None)
            new_msg = False
            if thread._name == 'mail.thread':  # message with parent_id not linked to record
                new_msg = thread.message_notify(**post_params)
            else:
                new_msg = thread.message_post(**post_params)

            if new_msg and original_partner_ids:
                # postponed after message_post, because this is an external message and we don't want to create
                # duplicate emails due to notifications
                new_msg.write({'partner_ids': original_partner_ids})
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
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        message = email.message_from_bytes(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg_dict = self.message_parse(message, save_original=save_original)
        if strip_attachments:
            msg_dict.pop('attachments', None)

        existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg_dict['message_id'])], limit=1)
        if existing_msg_ids:
            _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                         msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return False

        # find possible routes for the message
        routes = self.message_route(message, msg_dict, model, thread_id, custom_values)
        thread_id = self._message_route_process(message, msg_dict, routes)
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
           :rtype: int
           :return: the id of the newly created thread object
        """
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        fields = self.fields_get()
        name_field = self._rec_name or 'name'
        if name_field in fields and not data.get('name'):
            data[name_field] = msg_dict.get('subject', '')
        return self.create(data)

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

    def _message_receive_bounce(self, email, partner):
        """Called by ``message_process`` when a bounce email (such as Undelivered
        Mail Returned to Sender) is received for an existing thread. The default
        behavior is to do nothing. This method is meant to be overridden in various
        modules to add some specific behavior like blacklist management or mass
        mailing statistics update. check is an integer  ``message_bounce`` column exists.
        If it is the case, its content is incremented.

        :param string email: email that caused the bounce;
        :param record partner: partner matching the bounced email address, if any;
        """
        pass

    def _message_reset_bounce(self, email):
        """Called by ``message_process`` when an email is considered as not being
        a bounce. The default behavior is to do nothing. This method is meant to
        be overridden in various modules to add some specific behavior like
        blacklist management.

        :param string email: email for which to reset bounce information
        """
        pass

    def _message_parse_extract_payload_postprocess(self, message, payload_dict):
        """ Perform some cleaning / postprocess in the body and attachments
        extracted from the email. Note that this processing is specific to the
        mail module, and should not contain security or generic html cleaning.
        Indeed those aspects should be covered by the html_sanitize method
        located in tools. """
        body, attachments = payload_dict['body'], payload_dict['attachments']
        if not body:
            return payload_dict
        try:
            root = lxml.html.fromstring(body)
        except ValueError:
            # In case the email client sent XHTML, fromstring will fail because 'Unicode strings
            # with encoding declaration are not supported'.
            root = lxml.html.fromstring(body.encode('utf-8'))

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
            body = etree.tostring(root, pretty_print=False, encoding='unicode')
        return {'body': body, 'attachments': attachments}

    def _message_parse_extract_payload(self, message, save_original=False):
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
        if message.get_content_maintype() == 'text':
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
                        filename = tools.decode_smtp_header(filename)
                encoding = part.get_content_charset()  # None if attachment

                # 0) Inline Attachments -> attachments, with a third part in the tuple to match cid / attachment
                if filename and part.get('content-id'):
                    inner_cid = str(part.get('content-id')).strip('><')
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
                    # we only strip_classes here everything else will be done in by html field of mail.message
                    body = tools.html_sanitize(body, sanitize_tags=False, strip_classes=True)
                # 4) Anything else -> attachment
                else:
                    attachments.append(self._Attachment(filename or 'attachment', part.get_payload(decode=True), {}))

        return self._message_parse_extract_payload_postprocess(message, {'body': body, 'attachments': attachments})

    def _message_parse_extract_bounce(self, email_message, message_dict):
        """ Parse email and extract bounce information to be used in future
        processing.

        :param email_message: an email.message instance;
        :param message_dict: dictionary holding already-parsed values and in
            which bounce-related values will be added;
        """
        if not isinstance(email_message, Message):
            raise TypeError('message must be an email.message.Message at this point')

        email_part = next((part for part in email_message.walk() if part.get_content_type() == 'message/rfc822'), None)
        dsn_part = next((part for part in email_message.walk() if part.get_content_type() == 'message/delivery-status'), None)

        bounced_email = False
        bounced_partner = self.env['res.partner'].sudo()
        if dsn_part and len(dsn_part.get_payload()) > 1:
            dsn = dsn_part.get_payload()[1]
            final_recipient_data = tools.decode_message_header(dsn, 'Final-Recipient')
            bounced_email = tools.email_normalize(final_recipient_data.split(';', 1)[1].strip())
            if bounced_email:
                bounced_partner = self.env['res.partner'].sudo().search([('email_normalized', '=', bounced_email)])

        bounced_msg_id = False
        bounced_message = self.env['mail.message'].sudo()
        if email_part:
            email = email_part.get_payload()[0]
            bounced_msg_id = tools.mail_header_msgid_re.findall(tools.decode_message_header(email, 'Message-Id'))
            if bounced_msg_id:
                bounced_message = self.env['mail.message'].sudo().search([('message_id', 'in', bounced_msg_id)])

        return {
            'bounced_email': bounced_email,
            'bounced_partner': bounced_partner,
            'bounced_msg_id': bounced_msg_id,
            'bounced_message': bounced_message,
        }

    @api.model
    def message_parse(self, message, save_original=False):
        """ Parses an email.message.Message representing an RFC-2822 email
        and returns a generic dict holding the message details.

        :param message: email to parse
        :type message: email.message.Message
        :param bool save_original: whether the returned dict should include
            an ``original`` attachment containing the source of the message
        :rtype: dict
        :return: A dict with the following structure, where each field may not
            be present if missing in original message::

            { 'message_id': msg_id,
              'subject': subject,
              'email_from': from,
              'to': to + delivered-to,
              'cc': cc,
              'recipients': delivered-to + to + cc + resent-to + resent-cc,
              'partner_ids': partners found based on recipients emails,
              'body': unified_body,
              'references': references,
              'in_reply_to': in-reply-to,
              'parent_id': parent mail.message based on in_reply_to or references,
              'internal': answer to an internal message (note),
              'date': date,
              'attachments': [('file1', 'bytes'),
                              ('file2', 'bytes')}
            }
        """
        if not isinstance(message, Message):
            raise ValueError(_('Message should be a valid Message instance'))
        msg_dict = {'message_type': 'email'}

        message_id = message.get('Message-Id')
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id.strip()

        if message.get('Subject'):
            msg_dict['subject'] = tools.decode_message_header(message, 'Subject')

        email_from = tools.decode_message_header(message, 'From', quoted=True)
        email_cc = tools.decode_message_header(message, 'cc', quoted=True)
        email_from_list = tools.email_split_and_format(email_from)
        email_cc_list = tools.email_split_and_format(email_cc)
        msg_dict['email_from'] = email_from_list[0] if email_from_list else email_from
        msg_dict['from'] = msg_dict['email_from']  # compatibility for message_new
        msg_dict['cc'] = ','.join(email_cc_list) if email_cc_list else email_cc
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        msg_dict['recipients'] = ','.join(set(formatted_email
            for address in [
                tools.decode_message_header(message, 'Delivered-To', quoted=True),
                tools.decode_message_header(message, 'To', quoted=True),
                tools.decode_message_header(message, 'Cc', quoted=True),
                tools.decode_message_header(message, 'Resent-To', quoted=True),
                tools.decode_message_header(message, 'Resent-Cc', quoted=True)
            ] if address
            for formatted_email in tools.email_split_and_format(address))
        )
        msg_dict['to'] = ','.join(set(formatted_email
            for address in [
                tools.decode_message_header(message, 'Delivered-To', quoted=True),
                tools.decode_message_header(message, 'To', quoted=True)
            ] if address
            for formatted_email in tools.email_split_and_format(address))
        )
        partner_ids = [x.id for x in self._mail_find_partner_from_emails(tools.email_split(msg_dict['recipients']), records=self) if x]
        msg_dict['partner_ids'] = partner_ids
        # compute references to find if email_message is a reply to an existing thread
        msg_dict['references'] = tools.decode_message_header(message, 'References')
        msg_dict['in_reply_to'] = tools.decode_message_header(message, 'In-Reply-To').strip()

        if message.get('Date'):
            try:
                date_hdr = tools.decode_message_header(message, 'Date')
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

        if msg_dict['in_reply_to']:
            parent_ids = self.env['mail.message'].search([('message_id', '=', msg_dict['in_reply_to'])], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id
                msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        if msg_dict['references'] and 'parent_id' not in msg_dict:
            references_msg_id_list = tools.mail_header_msgid_re.findall(msg_dict['references'])
            parent_ids = self.env['mail.message'].search([('message_id', 'in', [x.strip() for x in references_msg_id_list])], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id
                msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        msg_dict.update(self._message_parse_extract_payload(message, save_original=save_original))
        msg_dict.update(self._message_parse_extract_bounce(message, msg_dict))
        return msg_dict

    # ------------------------------------------------------
    # Recipient management
    # ------------------------------------------------------

    @api.model
    def _message_get_default_recipients_on_records(self, records):
        """ Generic implementation for finding default recipient to mail on
        a recordset. ``_message_get_default_recipients`` may be defined to
        implement custom behavior. """
        if hasattr(records, '_message_get_default_recipients'):
            return records._message_get_default_recipients()

        res = {}
        for record in records:
            recipient_ids, email_to, email_cc = [], False, False
            if 'partner_id' in record and record.partner_id:
                recipient_ids.append(record.partner_id.id)
            elif 'email_normalized' in record and record.email_normalized:
                email_to = record.email_normalized
            elif 'email_from' in record and record.email_from:
                email_to = record.email_from
            elif 'partner_email' in record and record.partner_email:
                email_to = record.partner_email
            elif 'email' in record and record.email:
                email_to = record.email
            res[record.id] = {'partner_ids': recipient_ids, 'email_to': email_to, 'email_cc': email_cc}
        return res

    def _message_add_suggested_recipient(self, result, partner=None, email=None, reason=''):
        """ Called by _message_get_suggested_recipients, to add a suggested
            recipient in the result dictionary. The form is :
                partner_id, partner_name<partner_email> or partner_name, reason """
        self.ensure_one()
        if email and not partner:
            # get partner info from email
            partner_info = self._message_partner_info_from_emails([email])[0]
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

    def _message_get_suggested_recipients(self):
        """ Returns suggested recipients for ids. Those are a list of
        tuple (partner_id, partner_name, reason), to be managed by Chatter. """
        result = dict((res_id, []) for res_id in self.ids)
        if 'user_id' in self._fields:
            for obj in self.sudo():  # SUPERUSER because of a read on res.users that would crash otherwise
                if not obj.user_id or not obj.user_id.partner_id:
                    continue
                obj._message_add_suggested_recipient(result, partner=obj.user_id.partner_id, reason=self._fields['user_id'].string)
        return result

    def _mail_search_on_user(self, normalized_emails, extra_domain=False):
        """ Find partners linked to users, given an email address that will
        be normalized. Search is done as sudo on res.users model to avoid domain
        on partner like ('user_ids', '!=', False) that would not be efficient. """
        domain = [('email_normalized', 'in', normalized_emails)]
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        partners = self.env['res.users'].sudo().search(domain, order='name ASC').mapped('partner_id')
        # return a search on partner to filter results current user should not see (multi company for example)
        return self.env['res.partner'].search([('id', 'in', partners.ids)])

    def _mail_search_on_partner(self, normalized_emails, extra_domain=False):
        domain = [('email_normalized', 'in', normalized_emails)]
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return self.env['res.partner'].search(domain)

    def _mail_find_user_for_gateway(self, email, alias=None):
        """ Utility method to find user from email address that can create documents
        in the target model. Purpose is to link document creation to users whenever
        possible, for example when creating document through mailgateway.

        Heuristic

          * alias owner record: fetch in its followers for user with matching email;
          * find any user with matching emails;
          * try alias owner as fallback;

        Note that standard search order is applied.

        :param str email: will be sanitized and parsed to find email;
        :param mail.alias alias: optional alias. Used to fetch owner followers
          or fallback user (alias owner);
        :param fallback_model: if not alias, related model to check access rights;

        :return res.user user: user matching email or void recordset if none found
        """
        # find normalized emails and exclude aliases (to avoid subscribing alias emails to records)
        normalized_email = tools.email_normalize(email)
        catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        if normalized_email and catchall_domain:
            left_part = normalized_email.split('@')[0] if normalized_email.split('@')[1] == catchall_domain.lower() else False
            if left_part:
                if self.env['mail.alias'].sudo().search_count([('alias_name', '=', left_part)]):
                    return self.env['res.users']

        if alias and alias.alias_parent_model_id and alias.alias_parent_thread_id:
            followers = self.env['mail.followers'].search([
                ('res_model', '=', alias.alias_parent_model_id.model),
                ('res_id', '=', alias.alias_parent_thread_id)]
            ).mapped('partner_id')
        else:
            followers = self.env['res.partner']

        follower_users = self.env['res.users'].search([
            ('partner_id', 'in', followers.ids), ('email_normalized', '=', normalized_email)
        ], limit=1) if followers else self.env['res.users']
        matching_user = follower_users[0] if follower_users else self.env['res.users']
        if matching_user:
            return matching_user

        if not matching_user:
            std_users = self.env['res.users'].sudo().search([('email_normalized', '=', normalized_email)], limit=1, order='name ASC')
            matching_user = std_users[0] if std_users else self.env['res.users']
        if matching_user:
            return matching_user

        if not matching_user and alias and alias.alias_user_id:
            matching_user = alias and alias.alias_user_id
        if matching_user:
            return matching_user

        return matching_user

    @api.model
    def _mail_find_partner_from_emails(self, emails, records=None, force_create=False):
        """ Utility method to find partners from email addresses. If no partner is
        found, create new partners if force_create is enabled. Search heuristics

          * 1: check in records (record set) followers if records is mail.thread
               enabled and if check_followers parameter is enabled;
          * 2: search for partners with user;
          * 3: search for partners;

        :param records: record set on which to check followers;
        :param list emails: list of email addresses for finding partner;
        :param boolean force_create: create a new partner if not found

        :return list partners: a list of partner records ordered as given emails.
          If no partner has been found and/or created for a given emails its
          matching partner is an empty record.
        """
        if records and issubclass(type(records), self.pool['mail.thread']):
            followers = records.mapped('message_partner_ids')
        else:
            followers = self.env['res.partner']
        catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")

        # first, build a normalized email list and remove those linked to aliases to avoid adding aliases as partners
        normalized_emails = [tools.email_normalize(contact) for contact in emails if tools.email_normalize(contact)]
        if catchall_domain:
            domain_left_parts = [email.split('@')[0] for email in normalized_emails if email and email.split('@')[1] == catchall_domain.lower()]
            if domain_left_parts:
                found_alias_names = self.env['mail.alias'].sudo().search([('alias_name', 'in', domain_left_parts)]).mapped('alias_name')
                normalized_emails = [email for email in normalized_emails if email.split('@')[0] not in found_alias_names]

        done_partners = [follower for follower in followers if follower.email_normalized in normalized_emails]
        remaining = [email for email in normalized_emails if email not in [partner.email_normalized for partner in done_partners]]

        user_partners = self._mail_search_on_user(remaining)
        done_partners += [user_partner for user_partner in user_partners]
        remaining = [email for email in normalized_emails if email not in [partner.email_normalized for partner in done_partners]]

        partners = self._mail_search_on_partner(remaining)
        done_partners += [partner for partner in partners]
        remaining = [email for email in normalized_emails if email not in [partner.email_normalized for partner in done_partners]]

        # iterate and keep ordering
        partners = []
        for contact in emails:
            normalized_email = tools.email_normalize(contact)
            partner = next((partner for partner in done_partners if partner.email_normalized == normalized_email), self.env['res.partner'])
            if not partner and force_create and normalized_email in normalized_emails:
                partner = self.env['res.partner'].browse(self.env['res.partner'].name_create(contact)[0])
            partners.append(partner)
        return partners

    def _message_partner_info_from_emails(self, emails, link_mail=False):
        """ Convert a list of emails into a list partner_ids and a list
            new_partner_ids. The return value is non conventional because
            it is meant to be used by the mail widget.

            :return dict: partner_ids and new_partner_ids """
        self.ensure_one()
        MailMessage = self.env['mail.message'].sudo()
        partners = self._mail_find_partner_from_emails(emails, records=self)
        result = list()
        for idx, contact in enumerate(emails):
            partner = partners[idx]
            partner_info = {'full_name': partner.email_formatted if partner else contact, 'partner_id': partner.id}
            result.append(partner_info)
            # link mail with this from mail to the new partner id
            if link_mail and partner:
                MailMessage.search([
                    ('email_from', '=ilike', partner.email_normalized),
                    ('author_id', '=', False)
                ]).write({'author_id': partner.id})
        return result

    # ------------------------------------------------------
    # Post / Send message API
    # ------------------------------------------------------

    def _message_post_process_attachments(self, attachments, attachment_ids, message_values):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``, #todo xdo update that
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param dict message_data: model: the model of the attachments parent record,
          res_id: the id of the attachments parent record
        """
        return_values = {}
        body = message_values.get('body')
        model = message_values['model']
        res_id = message_values['res_id']

        m2m_attachment_ids = []
        if attachment_ids:
            # taking advantage of cache looks better in this case, to check
            filtered_attachment_ids = self.env['ir.attachment'].sudo().browse(attachment_ids).filtered(
                lambda a: a.res_model == 'mail.compose.message' and a.create_uid.id == self._uid)
            # update filtered (pending) attachments to link them to the proper record
            if filtered_attachment_ids:
                filtered_attachment_ids.write({'res_model': model, 'res_id': res_id})
            # prevent public and portal users from using attachments that are not theirs
            if not self.env.user.has_group('base.group_user'):
                attachment_ids = filtered_attachment_ids.ids

            m2m_attachment_ids += [(4, id) for id in attachment_ids]
        # Handle attachments parameter, that is a dictionary of attachments

        if attachments: # generate 
            cids_in_body = set()
            names_in_body = set()
            cid_list = []
            name_list = []

            if body:
                root = lxml.html.fromstring(tools.ustr(body))
                # first list all attachments that will be needed in body
                for node in root.iter('img'):
                    if node.get('src', '').startswith('cid:'):
                        cids_in_body.add(node.get('src').split('cid:')[1])
                    elif node.get('data-filename'):
                        names_in_body.add(node.get('data-filename'))
            attachement_values_list = []

            # generate values
            for attachment in attachments:
                cid = False
                if len(attachment) == 2:
                    name, content = attachment
                elif len(attachment) == 3:
                    name, content, info = attachment
                    cid = info and info.get('cid')
                else:
                    continue
                if isinstance(content, str):
                    content = content.encode('utf-8')
                elif content is None:
                    continue
                attachement_values= {
                    'name': name,
                    'datas': base64.b64encode(content),
                    'type': 'binary',
                    'description': name,
                    'res_model': model,
                    'res_id': res_id,
                }
                if body and (cid and cid in cids_in_body or name in names_in_body):
                    attachement_values['access_token'] = self.env['ir.attachment']._generate_access_token()
                attachement_values_list.append(attachement_values)
                # keep cid and name list synced with attachement_values_list length to match ids latter
                cid_list.append(cid)
                name_list.append(name)
            new_attachments = self.env['ir.attachment'].create(attachement_values_list)
            cid_mapping = {}
            name_mapping = {}
            for counter, new_attachment in enumerate(new_attachments):
                cid = cid_list[counter]
                if 'access_token' in attachement_values_list[counter]:
                    if cid:
                        cid_mapping[cid] = (new_attachment.id, attachement_values_list[counter]['access_token'])
                    name = name_list[counter]
                    name_mapping[name] = (new_attachment.id, attachement_values_list[counter]['access_token'])
                m2m_attachment_ids.append((4, new_attachment.id))

            # note: right know we are only taking attachments and ignoring attachment_ids.
            if (cid_mapping or name_mapping) and body:
                postprocessed = False
                for node in root.iter('img'):
                    attachment_data = False
                    if node.get('src', '').startswith('cid:'):
                        cid = node.get('src').split('cid:')[1]
                        attachment_data = cid_mapping.get(cid)
                    if not attachment_data and node.get('data-filename'):
                        attachment_data = name_mapping.get(node.get('data-filename'), False)
                    if attachment_data:
                        node.set('src', '/web/image/%s?access_token=%s' % attachment_data)
                        postprocessed = True
                if postprocessed:
                    return_values['body'] = lxml.html.tostring(root, pretty_print=False, encoding='UTF-8')
        return_values['attachment_ids'] = m2m_attachment_ids
        return return_values

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *,
                     body='', subject=None, message_type='notification',
                     email_from=None, author_id=None, parent_id=False,
                     subtype_id=False, subtype=None, partner_ids=None, channel_ids=None,
                     attachments=None, attachment_ids=None,
                     add_sign=True, record_name=False,
                     **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID.
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str subject: subject of the message
            :param str message_type: see mail_message.message_type field. Can be anything but 
                user_notification, reserved for message_notify
            :param int parent_id: handle thread formation
            :param int subtype_id: subtype_id of the message, mainly use fore
                followers mechanism
            :param int subtype: xmlid that will be used to compute subtype_id
                if subtype_id is not given.
            :param list(int) partner_ids: partner_ids to notify
            :param list(int) channel_ids: channel_ids to notify
            :param list(tuple(str,str), tuple(str,str, dict) or int) attachments : list of attachment tuples in the form
                ``(name,content)`` or ``(name,content, info)``, where content is NOT base64 encoded
            :param list id attachment_ids: list of existing attachement to link to this message
                -Should only be setted by chatter
                -Attachement object attached to mail.compose.message(0) will be attached
                    to the related document.
            Extra keyword arguments will be used as default column values for the
            new mail.message record.
            :return int: ID of newly created mail.message
        """
        self.ensure_one()  # should always be posted on a record, use message_notify if no record
        # split message additional values from notify additional values
        msg_kwargs = dict((key, val) for key, val in kwargs.items() if key in self.env['mail.message']._fields)
        notif_kwargs = dict((key, val) for key, val in kwargs.items() if key not in msg_kwargs)

        if self._name == 'mail.thread' or not self.id or message_type == 'user_notification':
            raise ValueError('message_post should only be call to post message on record. Use message_notify instead')

        if 'model' in msg_kwargs or 'res_id' in msg_kwargs:
            raise ValueError("message_post doesn't support model and res_id parameters anymore. Please call message_post on record")

        self = self.with_lang() # add lang to context imediatly since it will be usefull in various flows latter.

        # Explicit access rights check, because display_name is computed as sudo.
        self.check_access_rights('read')
        self.check_access_rule('read')
        record_name = record_name or self.display_name

        partner_ids = set(partner_ids or [])
        channel_ids = set(channel_ids or [])

        if any(not isinstance(pc_id, int) for pc_id in partner_ids | channel_ids):
            raise ValueError('message_post partner_ids and channel_ids must be integer list, not commands')

        # Find the message's author
        author_info = self._message_compute_author(author_id, email_from, raise_exception=True)
        author_id, email_from = author_info['author_id'], author_info['email_from']

        if not subtype_id:
            subtype = subtype or 'mt_note'
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype)

        # automatically subscribe recipients if asked to
        if self._context.get('mail_post_autofollow') and partner_ids:
            self.message_subscribe(list(partner_ids))

        MailMessage_sudo = self.env['mail.message'].sudo()
        if self._mail_flat_thread and not parent_id:
            parent_message = MailMessage_sudo.search([('res_id', '=', self.id), ('model', '=', self._name), ('message_type', '!=', 'user_notification')], order="id ASC", limit=1)
            # parent_message searched in sudo for performance, only used for id.
            # Note that with sudo we will match message with internal subtypes.
            parent_id = parent_message.id if parent_message else False
        elif parent_id:
            old_parent_id = parent_id
            parent_message = MailMessage_sudo.search([('id', '=', parent_id), ('parent_id', '!=', False)], limit=1)
            # avoid loops when finding ancestors
            processed_list = []
            if parent_message:
                new_parent_id = parent_message.parent_id and parent_message.parent_id.id
                while (new_parent_id and new_parent_id not in processed_list):
                    processed_list.append(new_parent_id)
                    parent_message = parent_message.parent_id
                parent_id = parent_message.id

        values = dict(msg_kwargs)
        values.update({
            'author_id': author_id,
            'email_from': email_from,
            'model': self._name,
            'res_id': self.id,
            'body': body,
            'subject': subject or False,
            'message_type': message_type,
            'parent_id': parent_id,
            'subtype_id': subtype_id,
            'partner_ids': partner_ids,
            'channel_ids': channel_ids,
            'add_sign': add_sign,
            'record_name': record_name,
        })
        attachments = attachments or []
        attachment_ids = attachment_ids or []
        attachement_values = self._message_post_process_attachments(attachments, attachment_ids, values)
        values.update(attachement_values)  # attachement_ids, [body]

        new_message = self._message_create(values)

        # Set main attachment field if necessary
        self._message_set_main_attachment_id(values['attachment_ids'])

        if values['author_id'] and values['message_type'] != 'notification' and not self._context.get('mail_create_nosubscribe'):
            # if self.env['res.partner'].browse(values['author_id']).active:  # we dont want to add odoobot/inactive as a follower
            self._message_subscribe([values['author_id']])

        self._message_post_after_hook(new_message, values)
        self._notify_thread(new_message, values, **notif_kwargs)
        return new_message

    def _message_set_main_attachment_id(self, attachment_ids):  # todo move this out of mail.thread
        if not self._abstract and attachment_ids and not self.message_main_attachment_id:
            all_attachments = self.env['ir.attachment'].browse([attachment_tuple[1] for attachment_tuple in attachment_ids])
            prioritary_attachments = all_attachments.filtered(lambda x: x.mimetype.endswith('pdf')) \
                                     or all_attachments.filtered(lambda x: x.mimetype.startswith('image')) \
                                     or all_attachments
            self.sudo().with_context(tracking_disable=True).write({'message_main_attachment_id': prioritary_attachments[0].id})

    def _message_post_after_hook(self, message, msg_vals):
        """ Hook to add custom behavior after having posted the message. Both
        message and computed value are given, to try to lessen query count by
        using already-computed values instead of having to rebrowse things. """
        pass

    def message_post_with_view(self, views_or_xmlid, **kwargs):
        """ Helper method to send a mail / post a message using a view_id to
        render using the ir.qweb engine. This method is stand alone, because
        there is nothing in template and composer that allows to handle
        views in batch. This method should probably disappear when templates
        handle ir ui views. """
        values = kwargs.pop('values', None) or dict()
        try:
            from odoo.addons.http_routing.models.ir_http import slug
            values['slug'] = slug
        except ImportError:
            values['slug'] = lambda self: self.id
        if isinstance(views_or_xmlid, str):
            views = self.env.ref(views_or_xmlid, raise_if_not_found=False)
        else:
            views = views_or_xmlid
        if not views:
            return
        for record in self:
            values['object'] = record
            rendered_template = views.render(values, engine='ir.qweb', minimal_qcontext=True)
            kwargs['body'] = rendered_template
            record.message_post_with_template(False, **kwargs)

    def message_post_with_template(self, template_id, email_layout_xmlid=None, auto_commit=False, **kwargs):
        """ Helper method to send a mail with a template
            :param template_id : the id of the template to render to create the body of the message
            :param **kwargs : parameter to create a mail.compose.message woaerd (which inherit from mail.message)
        """
        # Get composition mode, or force it according to the number of record in self
        if not kwargs.get('composition_mode'):
            kwargs['composition_mode'] = 'comment' if len(self.ids) == 1 else 'mass_mail'
        if not kwargs.get('message_type'):
            kwargs['message_type'] = 'notification'
        res_id = kwargs.get('res_id', self.ids and self.ids[0] or 0)
        res_ids = kwargs.get('res_id') and [kwargs['res_id']] or self.ids

        # Create the composer
        composer = self.env['mail.compose.message'].with_context(
            active_id=res_id,
            active_ids=res_ids,
            active_model=kwargs.get('model', self._name),
            default_composition_mode=kwargs['composition_mode'],
            default_model=kwargs.get('model', self._name),
            default_res_id=res_id,
            default_template_id=template_id,
            custom_layout=email_layout_xmlid,
        ).create(kwargs)
        # Simulate the onchange (like trigger in form the view) only
        # when having a template in single-email mode
        if template_id:
            update_values = composer.onchange_template_id(template_id, kwargs['composition_mode'], self._name, res_id)['value']
            composer.write(update_values)
        return composer.send_mail(auto_commit=auto_commit)

    def message_notify(self, *,
                       partner_ids=False, parent_id=False, model=False, res_id=False,
                       author_id=None, email_from=None, body='', subject=False, **kwargs):
        """ Shortcut allowing to notify partners of messages that shouldn't be 
        displayed on a document. It pushes notifications on inbox or by email depending
        on the user configuration, like other notifications. """
        if self:
            self.ensure_one()
        # split message additional values from notify additional values
        msg_kwargs = dict((key, val) for key, val in kwargs.items() if key in self.env['mail.message']._fields)
        notif_kwargs = dict((key, val) for key, val in kwargs.items() if key not in msg_kwargs)

        author_info = self._message_compute_author(author_id, email_from, raise_exception=True)
        author_id, email_from = author_info['author_id'], author_info['email_from']

        if not partner_ids:
            _logger.warning('Message notify called without recipient_ids, skipping')
            return self.env['mail.message']

        if not (model and res_id):  # both value should be set or none should be set (record)
            model = False
            res_id = False

        MailThread = self.env['mail.thread']
        values = {
            'parent_id': parent_id,
            'model': self._name if self else False,
            'res_id': self.id if self else False,
            'message_type': 'user_notification',
            'subject': subject,
            'body': body,
            'author_id': author_id,
            'email_from': email_from,
            'partner_ids': partner_ids,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': MailThread._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        values.update(msg_kwargs)
        new_message = MailThread._message_create(values)
        MailThread._notify_thread(new_message, values, **notif_kwargs)
        return new_message

    def _message_log(self, *, body='', author_id=None, email_from=None, subject=False, message_type='notification', **kwargs):
        """ Shortcut allowing to post note on a document. It does not perform
        any notification and pre-computes some values to have a short code
        as optimized as possible. This method is private as it does not check
        access rights and perform the message creation as sudo to speedup
        the log process. This method should be called within methods where
        access rights are already granted to avoid privilege escalation. """
        self.ensure_one()
        author_info = self._message_compute_author(author_id, email_from, raise_exception=False)
        author_id, email_from = author_info['author_id'], author_info['email_from']

        message_values = {
            'subject': subject,
            'body': body,
            'author_id': author_id,
            'email_from': email_from,
            'message_type': message_type,
            'model': kwargs.get('model', self._name),
            'res_id': self.ids[0] if self.ids else False,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),  # why? this is all but a notify
        }
        message_values.update(kwargs)
        return self.sudo()._message_create(message_values)

    def _message_log_batch(self, bodies, author_id=None, email_from=None, subject=False, message_type='notification'):
        """ Shortcut allowing to post notes on a batch of documents. It achieve the
        same purpose as _message_log, done in batch to speedup quick note log.

          :param bodies: dict {record_id: body}
        """
        author_info = self._message_compute_author(author_id, email_from, raise_exception=False)
        author_id, email_from = author_info['author_id'], author_info['email_from']

        base_message_values = {
            'subject': subject,
            'author_id': author_id,
            'email_from': email_from,
            'message_type': message_type,
            'model': self._name,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),  # why? this is all but a notify
        }
        values_list = [dict(base_message_values,
                            res_id=record.id,
                            body=bodies.get(record.id, ''))
                       for record in self]
        return self.sudo()._message_create(values_list)

    def _message_compute_author(self, author_id=None, email_from=None, raise_exception=True):
        """ Tool method computing author information for messages. Purpose is
        to ensure maximum coherence between author / current user / email_from
        when sending emails. """
        if author_id is None:
            if email_from:
                author = self._mail_find_partner_from_emails([email_from])[0]
            else:
                author = self.env.user.partner_id
                email_from = author.email_formatted
            author_id = author.id

        if email_from is None:
            if author_id:
                author = self.env['res.partner'].browse(author_id)
                email_from = author.email_formatted

        # superuser mode without author email -> probably public user; anyway we don't want to crash
        if not email_from and not self.env.su and raise_exception:
            raise exceptions.UserError(_("Unable to log message, please configure the sender's email address."))

        return {
            'author_id': author_id,
            'email_from': email_from,
        }

    def _message_create(self, values_list):
        if not isinstance(values_list, (list)):
            values_list = [values_list]
        create_values_list = []
        for values in values_list:
            create_values = dict(values)
            # Avoid warnings about non-existing fields
            for x in ('from', 'to', 'cc', 'canned_response_ids'):
                create_values.pop(x, None)
            create_values['partner_ids'] = [(4, pid) for pid in create_values.get('partner_ids', [])]
            create_values['channel_ids'] = [(4, cid) for cid in create_values.get('channel_ids', [])]
            create_values_list.append(create_values)
        if 'default_child_ids' in self._context:
            ctx = {key: val for key, val in self._context.items() if key != 'default_child_ids'}
            self = self.with_context(ctx)
        return self.env['mail.message'].create(create_values_list)

    # ------------------------------------------------------
    # Notification API
    # ------------------------------------------------------

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """ Main notification method. This method basically does two things

         * call ``_notify_compute_recipients`` that computes recipients to
           notify based on message record or message creation values if given
           (to optimize performance if we already have data computed);
         * performs the notification process by calling the various notification
           methods implemented;

        This method cnn be overridden to intercept and postpone notification
        mechanism like mail.channel moderation.

        :param message: mail.message record to notify;
        :param msg_vals: dictionary of values used to create the message. If given
          it is used instead of accessing ``self`` to lessen query count in some
          simple cases where no notification is actually required;

        Kwargs allow to pass various parameters that are given to sub notification
        methods. See those methods for more details about the additional parameters.
        Parameters used for email-style notifications
        """
        msg_vals = msg_vals if msg_vals else {}
        rdata = self._notify_compute_recipients(message, msg_vals)
        if not rdata:
            return False

        message_values = {}
        if rdata['channels']:
            message_values['channel_ids'] = [(6, 0, [r['id'] for r in rdata['channels']])]

        self._notify_record_by_inbox(message, rdata, msg_vals=msg_vals, **kwargs)
        self._notify_record_by_email(message, rdata, msg_vals=msg_vals, **kwargs)

        return rdata

    def _notify_record_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Notification method: inbox. Do two main things

          * create an inbox notification for users;
          * create channel / message link (channel_ids field of mail.message);
          * send bus notifications;

        TDE/XDO TODO: flag rdata directly, with for example r['notif'] = 'ocn_client' and r['needaction']=False
        and correctly override notify_recipients
        """
        channel_ids = [r['id'] for r in recipients_data['channels']]
        if channel_ids:
            message.write({'channel_ids': [(6, 0, channel_ids)]})

        inbox_pids = [r['id'] for r in recipients_data['partners'] if r['notif'] == 'inbox']
        if inbox_pids:
            notif_create_values = [{
                'mail_message_id': message.id,
                'res_partner_id': pid,
                'notification_type': 'inbox',
                'notification_status': 'sent',
            } for pid in inbox_pids]
            self.env['mail.notification'].sudo().create(notif_create_values)

        bus_notifications = []
        if inbox_pids or channel_ids:
            message_format_values = False
            if inbox_pids:
                message_format_values = message.message_format()[0]
                for partner_id in inbox_pids:
                    bus_notifications.append([(self._cr.dbname, 'ir.needaction', partner_id), dict(message_format_values)])
            if channel_ids:
                bus_notifications += self.env['mail.channel'].sudo().browse(channel_ids)._channel_message_notifications(message, message_format_values)
        if bus_notifications:
            self.env['bus.bus'].sudo().sendmany(bus_notifications)

    def _notify_record_by_email(self, message, recipients_data, msg_vals=False,
                                model_description=False, mail_auto_delete=True, check_existing=False,
                                force_send=True, send_after_commit=True,
                                **kwargs):
        """ Method to send email linked to notified messages.

        :param message: mail.message record to notify;
        :param recipients_data: see ``_notify_thread``;
        :param msg_vals: see ``_notify_thread``;

        :param model_description: model description used in email notification process
          (computed if not given);
        :param mail_auto_delete: delete notification emails once sent;
        :param check_existing: check for existing notifications to update based on
          mailed recipient, otherwise create new notifications;

        :param force_send: send emails directly instead of using queue;
        :param send_after_commit: if force_send, tells whether to send emails after
          the transaction has been committed using a post-commit hook;
        """
        partners_data = [r for r in recipients_data['partners'] if r['notif'] == 'email']
        if not partners_data:
            return True

        model = msg_vals.get('model') if msg_vals else message.model
        model_name = model_description or (self.with_lang().env['ir.model']._get(model).display_name if model else False) # one query for display name
        recipients_groups_data = self._notify_classify_recipients(partners_data, model_name)

        if not recipients_groups_data:
            return True
        force_send = self.env.context.get('mail_notify_force_send', force_send)

        template_values = self._notify_prepare_template_context(message, msg_vals, model_description=model_description) # 10 queries

        email_layout_xmlid = msg_vals.get('email_layout_xmlid') if msg_vals else message.email_layout_xmlid
        template_xmlid = email_layout_xmlid if email_layout_xmlid else 'mail.message_notification_email'
        try:
            base_template = self.env.ref(template_xmlid, raise_if_not_found=True).with_context(lang=template_values['lang']) # 1 query
        except ValueError:
            _logger.warning('QWeb template %s not found when sending notification emails. Sending without layouting.' % (template_xmlid))
            base_template = False

        mail_subject = message.subject or (message.record_name and 'Re: %s' % message.record_name) # in cache, no queries
        # prepare notification mail values
        base_mail_values = {
            'mail_message_id': message.id,
            'mail_server_id': message.mail_server_id.id, # 2 query, check acces + read, may be useless, Falsy, when will it be used?
            'auto_delete': mail_auto_delete,
            # due to ir.rule, user have no right to access parent message if message is not published
            'references': message.parent_id.sudo().message_id if message.parent_id else False,
            'subject': mail_subject,
        }
        base_mail_values = self._notify_by_email_add_values(base_mail_values)

        Mail = self.env['mail.mail'].sudo()
        emails = self.env['mail.mail'].sudo()

        # loop on groups (customer, portal, user,  ... + model specific like group_sale_salesman)
        notif_create_values = []
        recipients_max = 50
        for recipients_group_data in recipients_groups_data:
            # generate notification email content
            recipients_ids = recipients_group_data.pop('recipients')
            render_values = {**template_values, **recipients_group_data}
            # {company, is_discussion, lang, message, model_description, record, record_name, signature, subtype, tracking_values, website_url}
            # {actions, button_access, has_button_access, recipients}

            if base_template:
                mail_body = base_template.render(render_values, engine='ir.qweb', minimal_qcontext=True)
            else:
                mail_body = message.body
            mail_body = self._replace_local_links(mail_body)

            # create email
            for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
                recipient_values = self._notify_email_recipient_values(recipients_ids_chunk)
                email_to = recipient_values['email_to']
                recipient_ids = recipient_values['recipient_ids']

                create_values = {
                    'body_html': mail_body,
                    'subject': mail_subject,
                    'recipient_ids': [(4, pid) for pid in recipient_ids],
                }
                if email_to:
                    create_values['email_to'] = email_to
                create_values.update(base_mail_values)  # mail_message_id, mail_server_id, auto_delete, references, headers
                email = Mail.create(create_values)

                if email and recipient_ids:
                    tocreate_recipient_ids = list(recipient_ids)
                    if check_existing:
                        existing_notifications = self.env['mail.notification'].sudo().search([
                            ('mail_message_id', '=', message.id),
                            ('notification_type', '=', 'email'),
                            ('res_partner_id', 'in', tocreate_recipient_ids)
                        ])
                        if existing_notifications:
                            tocreate_recipient_ids = [rid for rid in recipient_ids if rid not in existing_notifications.mapped('res_partner_id.id')]
                            existing_notifications.write({
                                'notification_status': 'ready',
                                'mail_id': email.id,
                            })
                    notif_create_values += [{
                        'mail_message_id': message.id,
                        'res_partner_id': recipient_id,
                        'notification_type': 'email',
                        'mail_id': email.id,
                        'is_read': True,  # discard Inbox notification
                        'notification_status': 'ready',
                    } for recipient_id in tocreate_recipient_ids]
                emails |= email

        if notif_create_values:
            self.env['mail.notification'].sudo().create(notif_create_values)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if force_send and len(emails) < recipients_max and (not self.pool._init or test_mode):
            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                email_ids = emails.ids
                dbname = self.env.cr.dbname
                _context = self._context
                def send_notifications():
                    db_registry = registry(dbname)
                    with api.Environment.manage(), db_registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, _context)
                        env['mail.mail'].browse(email_ids).send()
                self._cr.after('commit', send_notifications)
            else:
                emails.send()

        return True

    @api.model
    def _notify_prepare_template_context(self, message, msg_vals, model_description=False, mail_auto_delete=True):
        # compute send user and its related signature
        signature = ''
        user = self.env.user
        author = message.env['res.partner'].browse(msg_vals.get('author_id')) if msg_vals else message.author_id
        model = msg_vals.get('model') if msg_vals else message.model
        add_sign = msg_vals.get('add_sign') if msg_vals else message.add_sign
        subtype_id = msg_vals.get('subtype_id') if msg_vals else message.subtype_id.id
        message_id = message.id
        record_name = msg_vals.get('record_name') if msg_vals else message.record_name
        author_user = user if user.partner_id == author else author.user_ids[0] if author and author.user_ids else False
        # trying to use user (self.env.user) instead of browing user_ids if he is the author will give a sudo user,
        # improving access performances and cache usage.
        if author_user:
            user = author_user
            if add_sign:
                signature = user.signature
        else:
            if add_sign:
                signature = "<p>-- <br/>%s</p>" % author.name

        company = self.company_id.sudo() if self and 'company_id' in self else user.company_id
        if company.website:
            website_url = 'http://%s' % company.website if not company.website.lower().startswith(('http:', 'https:')) else company.website
        else:
            website_url = False

        # Retrieve the language in which the template was rendered, in order to render the custom
        # layout in the same language.
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= self.env.context.keys():
            template = self.env['mail.template'].browse(self.env.context['default_template_id'])
            if template and template.lang:
                lang = template._render_template(template.lang, self.env.context['default_model'], self.env.context['default_res_id'])

        if not model_description and model:
            model_description = self.env['ir.model'].with_context(lang=lang)._get(model).display_name

        tracking = []
        if msg_vals.get('tracking_value_ids', True) if msg_vals else bool(self): # could be tracking
            for tracking_value in self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', message.id)]):
                groups = tracking_value.field_groups
                if not groups or self.env.is_superuser() or self.user_has_groups(groups):
                    tracking.append((tracking_value.field_desc,
                                    tracking_value.get_old_display_value()[0],
                                    tracking_value.get_new_display_value()[0]))

        is_discussion = subtype_id == self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        return {
            'message': message,
            'signature': signature,
            'website_url': website_url,
            'company': company,
            'model_description': model_description,
            'record': self,
            'record_name': record_name,
            'tracking_values': tracking,
            'is_discussion': is_discussion,
            'subtype': message.subtype_id,
            'lang': lang,
        }

    def _notify_by_email_add_values(self, base_mail_values):
        """ Add model-specific values to the dictionary used to create the
        notification email. Its base behavior is to compute model-specific
        headers.

        :param dict base_mail_values: base mail.mail values, holding message
        to notify (mail_message_id and its fields), server, references, subject.
        """
        headers = self._notify_email_headers()
        if headers:
            base_mail_values['headers'] = headers
        return base_mail_values

    def _notify_compute_recipients(self, message, msg_vals):
        """ Compute recipients to notify based on subtype and followers. This
        method returns data structured as expected for ``_notify_recipients``. """
        msg_sudo = message.sudo()
        # get values from msg_vals or from message if msg_vals doen't exists
        pids = msg_vals.get('partner_ids', []) if msg_vals else msg_sudo.partner_ids.ids
        cids = msg_vals.get('channel_ids', []) if msg_vals else msg_sudo.channel_ids.ids
        message_type = msg_vals.get('message_type') if msg_vals else msg_sudo.message_type
        subtype_id = msg_vals.get('subtype_id') if msg_vals else msg_sudo.subtype_id.id
        # is it possible to have record but no subtype_id ?
        recipient_data = {
            'partners': [],
            'channels': [],
        }
        res = self.env['mail.followers']._get_recipient_data(self, message_type, subtype_id, pids, cids)
        if not res:
            return recipient_data

        author_id = msg_vals.get('author_id') or message.author_id.id
        for pid, cid, active, pshare, ctype, notif, groups in res:
            if pid and pid == author_id and not self.env.context.get('mail_notify_author'):  # do not notify the author of its own messages
                continue
            if pid:
                if active is False:
                    continue
                pdata = {'id': pid, 'active': active, 'share': pshare, 'groups': groups}
                if notif == 'inbox':
                    recipient_data['partners'].append(dict(pdata, notif=notif, type='user'))
                elif not pshare and notif:  # has an user and is not shared, is therefore user
                    recipient_data['partners'].append(dict(pdata, notif=notif, type='user'))
                elif pshare and notif:  # has an user but is shared, is therefore portal
                    recipient_data['partners'].append(dict(pdata, notif=notif, type='portal'))
                else:  # has no user, is therefore customer
                    recipient_data['partners'].append(dict(pdata, notif=notif if notif else 'email', type='customer'))
            elif cid:
                recipient_data['channels'].append({'id': cid, 'notif': notif, 'type': ctype})

        # add partner ids in email channels
        email_cids = [r['id'] for r in recipient_data['channels'] if r['notif'] == 'email']
        if email_cids:
            # we are doing a similar search in ocn_client
            # Could be interesting to make everything in a single query.
            # ocn_client: (searching all partners linked to channels of type chat).
            # here      : (searching all partners linked to channels with notif email if email is not the author one)
            # TDE FIXME: use email_sanitized
            email_from = msg_vals.get('email_from') or message.email_from
            exept_partner = [r['id'] for r in recipient_data['partners']]
            if author_id:
                exept_partner.append(author_id)
            new_pids = self.env['res.partner'].sudo().search([
                ('id', 'not in', exept_partner),
                ('channel_ids', 'in', email_cids),
                ('email', 'not in', [email_from]),
            ])
            for partner in new_pids:
                # caution: side effect, if user has notif type inbox, will receive en email anyway?
                # ocn_client: will add partners to recipient recipient_data. more ocn notifications. We neeed to filter them maybe
                recipient_data['partners'].append({'id': partner.id, 'share': True, 'active': True, 'notif': 'email', 'type': 'channel_email', 'groups': []})

        return recipient_data

    @api.model
    def _notify_encode_link(self, base_link, params):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params)))
        hm = hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha1).hexdigest()
        return hm

    def _notify_get_action_link(self, link_type, **kwargs):
        local_kwargs = dict(kwargs)  # do not modify in-place, modify copy instead
        base_params = {
            'model': kwargs.get('model', self._name),
            'res_id': kwargs.get('res_id', self.ids and self.ids[0] or False),
        }

        local_kwargs.pop('message_id', None)
        local_kwargs.pop('model', None)
        local_kwargs.pop('res_id', None)

        if link_type in ['view', 'assign', 'follow', 'unfollow']:
            params = dict(base_params, **local_kwargs)
            base_link = '/mail/%s' % link_type
        elif link_type == 'controller':
            controller = local_kwargs.pop('controller')
            params = dict(base_params, **local_kwargs)
            params.pop('model')
            base_link = '%s' % controller
        else:
            return ''

        if link_type not in ['view']:
            token = self._notify_encode_link(base_link, params)
            params['token'] = token

        link = '%s?%s' % (base_link, url_encode(params))
        if self:
            link = self[0].get_base_url() + link

        return link

    def _notify_get_groups(self):
        """ Return groups used to classify recipients of a notification email.
        Groups is a list of tuple containing of form (group_name, group_func,
        group_data) where
         * group_name is an identifier used only to be able to override and manipulate
           groups. Default groups are user (recipients linked to an employee user),
           portal (recipients linked to a portal user) and customer (recipients not
           linked to any user). An example of override use would be to add a group
           linked to a res.groups like Hr Officers to set specific action buttons to
           them.
         * group_func is a function pointer taking a partner record as parameter. This
           method will be applied on recipients to know whether they belong to a given
           group or not. Only first matching group is kept. Evaluation order is the
           list order.
         * group_data is a dict containing parameters for the notification email
          * has_button_access: whether to display Access <Document> in email. True
            by default for new groups, False for portal / customer.
          * button_access: dict with url and title of the button
          * actions: list of action buttons to display in the notification email.
            Each action is a dict containing url and title of the button.
        Groups has a default value that you can find in mail_thread
        ``_notify_classify_recipients`` method.
        """
        return [
            (
                'user',
                lambda pdata: pdata['type'] == 'user',
                {}
            ), (
                'portal',
                lambda pdata: pdata['type'] == 'portal',
                {'has_button_access': False}
            ), (
                'customer',
                lambda pdata: True,
                {'has_button_access': False}
            )
        ]

    def _notify_classify_recipients(self, recipient_data, model_name):
        """ Classify recipients to be notified of a message in groups to have
        specific rendering depending on their group. For example users could
        have access to buttons customers should not have in their emails.
        Module-specific grouping should be done by overriding ``_notify_get_groups``
        method defined here-under.
        :param recipient_data:todo xdo UPDATE ME
        return example:
        [{
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                                'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': False,
            'recipients': [11]
        },
        {
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                            'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': False,
            'recipients': [4, 5, 6] 
        },
        {
            'actions': [],
            'button_access': {'title': 'View Simple Chatter Model',
                                'url': '/mail/view?model=mail.test.simple&res_id=1497'},
            'has_button_access': True,
            'recipients': [10, 11, 12]
        }]
        only return groups with recipients
        """

        groups = self._notify_get_groups()

        access_link = self._notify_get_action_link('view')

        if model_name:
            view_title = _('View %s') % model_name
        else:
            view_title = _('View')

        # fill group_data with default_values if they are not complete
        for group_name, group_func, group_data in groups:
            group_data.setdefault('has_button_access', True)
            group_button_access = group_data.setdefault('button_access', {})
            group_button_access.setdefault('url', access_link)
            group_button_access.setdefault('title', view_title)
            group_data.setdefault('actions', list())
            group_data.setdefault('recipients', list())

        # classify recipients in each group
        for recipient in recipient_data:
            for group_name, group_func, group_data in groups:
                if group_func(recipient):
                    group_data['recipients'].append(recipient['id'])
                    break

        result = []
        for group_name, group_method, group_data in groups:
            if group_data['recipients']:
                result.append(group_data)

        return result

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Returns the preferred reply-to email address when replying to a thread
        on documents. Documents are either given by self it this method is called
        as a true multi method on a record set or can be given using records to
        have a generic implementation available for all models.
        Reply-to is formatted like "MyCompany MyDocument <reply.to@domain>".
        Heuristic it the following:
         * search for specific aliases as they always have priority; it is limited
           to aliases linked to documents (like project alias for task for example);
         * use catchall address;
         * use default;
        This method works on documents
         * as a true multi method for models inheriting from mail.thread; call
           ``records._notify_get_reply_to(...)``;
         * as a generic implementation if records are given; call ``MailThread.
           _notify_get_reply_to(records=records, ...)``;
         * as a generic implementation is self is a void mail.thread record set
           meaning catchall is computed; call ``MailThread._notify_get_reply_to
           (records=None)``;
        Tweak this method on a specific model by overriding if it inherits from
        mail.thread. An example would be tasks taking their reply-to alias from
        their project.
        :param default: default email if no alias or catchall is found;
        :param records: record_set if self if a generic mail.thread record allowing
          generic implementation of finding reply-to;
        :param company: used to compute company name part of the from name; provide
          it if already known, otherwise fall back on user company;
        :param doc_names: dict(res_id, doc_name) used to compute doc name part of
          the from name; provide it if already known to avoid queries, otherwise
          name_get on document will be performed;
        :return result: dictionary. Keys are record IDs and value is formatted
          like an email "Company_name Document_name <reply_to@email>"/
        """
        _records = self if self and self._name != 'mail.thread' else records
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False

        alias_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        result = dict.fromkeys(_res_ids, False)
        result_email = dict()
        doc_names = doc_names if doc_names else dict()

        if alias_domain:
            if model and res_ids:
                if not doc_names:
                    doc_names = dict((rec.id, rec.display_name) for rec in _records)

                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model),
                    ('alias_parent_thread_id', 'in', res_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    result_email.setdefault(alias.alias_parent_thread_id, '%s@%s' % (alias.alias_name, alias_domain))

            # left ids: use catchall
            left_ids = set(_res_ids) - set(result_email)
            if left_ids:
                catchall = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
                if catchall:
                    result_email.update(dict((rid, '%s@%s' % (catchall, alias_domain)) for rid in left_ids))

            # compute name of reply-to - TDE tocheck: quotes and stuff like that
            company_name = company.name if company else self.env.company.name
            for res_id in result_email.keys():
                name = '%s%s%s' % (company_name, ' ' if doc_names.get(res_id) else '', doc_names.get(res_id, ''))
                result[res_id] = tools.formataddr((name, result_email[res_id]))

        left_ids = set(_res_ids) - set(result_email)
        if left_ids:
            result.update(dict((res_id, default) for res_id in left_ids))

        return result

    @api.model
    def _notify_get_reply_to_on_records(self, default=None, records=None, company=None, doc_names=None):
        """ Generic wrapper on ``_notify_get_reply_to`` checking mail.thread inheritance
        and allowing to call model-specific implementation in a one liner. This
        method should not be overridden. """
        if records and hasattr(records, '_notify_get_reply_to'):
            return records._notify_get_reply_to(default=default, company=company, doc_names=doc_names)
        return self._notify_get_reply_to(default=default, records=records, company=company, doc_names=doc_names)

    def _notify_email_recipient_values(self, recipient_ids):
        """ Format email notification recipient values to store on the notification
        mail.mail. Basic method just set the recipient partners as mail_mail
        recipients. Override to generate other mail values like email_to or
        email_cc.
        :param recipient_ids: res.partner recordset to notify
        """
        return {
            'email_to': False,
            'recipient_ids': recipient_ids,
        }

    # ------------------------------------------------------
    # Followers API
    # ------------------------------------------------------

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """ Main public API to add followers to a record set. Its main purpose is
        to perform access rights checks before calling ``_message_subscribe``. """
        if not self or (not partner_ids and not channel_ids):
            return True

        partner_ids = partner_ids or []
        channel_ids = channel_ids or []
        adding_current = set(partner_ids) == set([self.env.user.partner_id.id])
        customer_ids = [] if adding_current else None

        if not channel_ids and partner_ids and adding_current:
            try:
                self.check_access_rights('read')
                self.check_access_rule('read')
            except exceptions.AccessError:
                return False
        else:
            self.check_access_rights('write')
            self.check_access_rule('write')

        # filter inactive
        if partner_ids and not adding_current:
            partner_ids = self.env['res.partner'].sudo().search([('id', 'in', partner_ids), ('active', '=', True)]).ids

        return self._message_subscribe(partner_ids, channel_ids, subtype_ids, customer_ids=customer_ids)

    def _message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, customer_ids=None):
        """ Main private API to add followers to a record set. This method adds
        partners and channels, given their IDs, as followers of all records
        contained in the record set.

        If subtypes are given existing followers are erased with new subtypes.
        If default one have to be computed only missing followers will be added
        with default subtypes matching the record set model.

        This private method does not specifically check for access right. Use
        ``message_subscribe`` public API when not sure about access rights.

        :param customer_ids: see ``_insert_followers`` """
        if not self:
            return True

        if not subtype_ids:
            self.env['mail.followers']._insert_followers(
                self._name, self.ids, partner_ids, None, channel_ids, None,
                customer_ids=customer_ids)
        else:
            self.env['mail.followers']._insert_followers(
                self._name, self.ids,
                partner_ids, dict((pid, subtype_ids) for pid in partner_ids),
                channel_ids, dict((cid, subtype_ids) for cid in channel_ids),
                customer_ids=customer_ids, check_existing=True, existing_policy='replace')

        return True

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

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """ Optional method to override in addons inheriting from mail.thread.
        Return a list tuples containing (
          partner ID,
          subtype IDs (or False if model-based default subtypes),
          QWeb template XML ID for notification (or False is no specific
            notification is required),
          ), aka partners and their subtype and possible notification to send
        using the auto subscription mechanism linked to updated values.

        Default value of this method is to return the new responsible of
        documents. This is done using relational fields linking to res.users
        with track_visibility set. Since OpenERP v7 it is considered as being
        responsible for the document and therefore standard behavior is to
        subscribe the user and send him a notification.

        Override this method to change that behavior and/or to add people to
        notify, using possible custom notification.

        :param updated_values: see ``_message_auto_subscribe``
        :param default_subtype_ids: coming from ``_get_auto_subscription_subtypes``
        """
        fnames = []
        field = self._fields.get('user_id')
        user_id = updated_values.get('user_id')
        if field and user_id and field.comodel_name == 'res.users' and (getattr(field, 'track_visibility', False) or getattr(field, 'tracking', False)):
            user = self.env['res.users'].sudo().browse(user_id)
            try: # avoid to make an exists, lets be optimistic and try to read it.
                if user.active:
                    return [(user.partner_id.id, default_subtype_ids, 'mail.message_user_assigned' if user != self.env.user else False)]
            except:
                pass
        return []

    def _message_auto_subscribe_notify(self, partner_ids, template):
        """ Notify new followers, using a template to render the content of the
        notification message. Notifications pushed are done using the standard
        notification mechanism in mail.thread. It is either inbox either email
        depending on the partner state: no user (email, customer), share user
        (email, customer) or classic user (notification_type)

        :param partner_ids: IDs of partner to notify;
        :param template: XML ID of template used for the notification;
        """
        if not self or self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        if not self.env.registry.ready:  # Don't send notification during install
            return

        view = self.env['ir.ui.view'].browse(self.env['ir.model.data'].xmlid_to_res_id(template))

        for record in self:
            model_description = self.env['ir.model']._get(record._name).display_name
            values = {
                'object': record,
                'model_description': model_description,
            }
            assignation_msg = view.render(values, engine='ir.qweb', minimal_qcontext=True)
            assignation_msg = self.env['mail.thread']._replace_local_links(assignation_msg)
            record.message_notify(
                subject=_('You have been assigned to %s') % record.display_name,
                body=assignation_msg,
                partner_ids=partner_ids,
                record_name=record.display_name,
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
            )

    def _message_auto_subscribe(self, updated_values):
        """ Handle auto subscription. Auto subscription is done based on two
        main mechanisms

         * using subtypes parent relationship. For example following a parent record
           (i.e. project) with subtypes linked to child records (i.e. task). See
           mail.message.subtype ``_get_auto_subscription_subtypes``;
         * calling _message_auto_subscribe_notify that returns a list of partner
           to subscribe, as well as data about the subtypes and notification
           to send. Base behavior is to subscribe responsible and notify them;

        Adding application-specific auto subscription should be done by overriding
        ``_message_auto_subscribe_followers``. It should return structured data
        for new partner to subscribe, with subtypes and eventual notification
        to perform. See that method for more details.

        :param updated_values: values modifying the record trigerring auto subscription
        """
        if not self:
            return True

        new_partners, new_channels = dict(), dict()

        # fetch auto subscription subtypes data
        updated_relation = dict()
        all_ids, def_ids, int_ids, parent, relation = self.env['mail.message.subtype']._get_auto_subscription_subtypes(self._name)

        # check effectively modified relation field
        for res_model, fnames in relation.items():
            for field in (fname for fname in fnames if updated_values.get(fname)):
                updated_relation.setdefault(res_model, set()).add(field)
        udpated_fields = [fname for fnames in updated_relation.values() for fname in fnames if updated_values.get(fname)]

        if udpated_fields:
            doc_data = [(model, [updated_values[fname] for fname in fnames]) for model, fnames in updated_relation.items()]
            res = self.env['mail.followers']._get_subscription_data(doc_data, None, None, include_pshare=True)
            for fid, rid, pid, cid, subtype_ids, pshare in res:
                sids = [parent[sid] for sid in subtype_ids if parent.get(sid)]
                sids += [sid for sid in subtype_ids if sid not in parent and sid in def_ids]
                if pid:
                    new_partners[pid] = (set(sids) & set(all_ids)) - set(int_ids) if pshare else set(sids) & set(all_ids)
                if cid:
                    new_channels[cid] = (set(sids) & set(all_ids)) - set(int_ids)

        notify_data = dict()
        res = self._message_auto_subscribe_followers(updated_values, def_ids)
        for pid, sids, template in res:
            new_partners.setdefault(pid, sids)
            if template:
                partner = self.env['res.partner'].browse(pid)
                lang = partner.lang if partner else None
                notify_data.setdefault((template, lang), list()).append(pid)

        self.env['mail.followers']._insert_followers(
            self._name, self.ids,
            list(new_partners), new_partners,
            list(new_channels), new_channels,
            check_existing=True, existing_policy='skip')

        # notify people from auto subscription, for example like assignation
        for (template, lang), pids in notify_data.items():
            self.with_context(lang=lang)._message_auto_subscribe_notify(pids, template)

        return True

    # ------------------------------------------------------
    # Controllers
    # ------------------------------------------------------

    def _get_mail_redirect_suggested_company(self):
        """ Return the suggested company to be set on the context
        in case of a mail redirection to the record. To avoid multi
        company issues when clicking on a link sent by email, this
        could be called to try setting the most suited company on
        the allowed_company_ids in the context. This method can be 
        overridden, for example on the hr.leave model, where the
        most suited company is the company of the leave type, as
        specified by the ir.rule.
        """
        if 'company_id' in self:
            return self.company_id
        return False
