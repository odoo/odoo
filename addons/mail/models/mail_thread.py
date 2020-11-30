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
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

from collections import namedtuple
from email.message import Message
from lxml import etree
from werkzeug import url_encode
from werkzeug import urls

from odoo import _, api, exceptions, fields, models, tools
from odoo.tools import pycompat, ustr, formataddr
from odoo.tools.misc import clean_context
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
    message_has_error = fields.Boolean(
        'Message Delivery error', compute='_compute_message_has_error', search='_search_message_has_error',
        help="If checked, some messages have a delivery error.")
    message_has_error_counter = fields.Integer(
        'Number of error', compute='_compute_message_has_error',
        help="Number of messages with delivery error")
    message_attachment_count = fields.Integer('Attachment Count', compute='_compute_message_attachment_count')
    message_main_attachment_id = fields.Many2one(string="Main Attachment", comodel_name='ir.attachment', index=True, copy=False)

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

    @api.multi
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
                             WHERE msg.model = %s AND msg.res_id = ANY(%s) AND
                                   (msg.author_id IS NULL OR msg.author_id != %s) AND
                                   (msg.message_type != 'notification' OR msg.model != 'mail.channel')""",
                         (partner_id, self._name, list(self.ids), partner_id,))
        for result in self._cr.fetchall():
            res[result[0]] += 1

        for record in self:
            record.message_unread_counter = res.get(record.id, 0)
            record.message_unread = bool(record.message_unread_counter)

    @api.multi
    def _get_message_needaction(self):
        res = dict((res_id, 0) for res_id in self.ids)
        if not res:
            return

        # search for unread messages, directly in SQL to improve performances
        self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                             RIGHT JOIN mail_message_res_partner_needaction_rel rel
                             ON rel.mail_message_id = msg.id AND rel.res_partner_id = %s AND (rel.is_read = false OR rel.is_read IS NULL)
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

    @api.multi
    def _compute_message_has_error(self):
        self._cr.execute(""" SELECT msg.res_id, COUNT(msg.res_id) FROM mail_message msg
                             RIGHT JOIN mail_message_res_partner_needaction_rel rel
                             ON rel.mail_message_id = msg.id AND rel.email_status in ('exception','bounce')
                             WHERE msg.author_id = %s AND msg.model = %s AND msg.res_id in %s
                             GROUP BY msg.res_id""",
                         (self.env.user.partner_id.id, self._name, tuple(self.ids),))
        res = dict()
        for result in self._cr.fetchall():
            res[result[0]] = result[1]

        for record in self:
            record.message_has_error_counter = res.get(record.id, 0)
            record.message_has_error = bool(record.message_has_error_counter)

    @api.model
    def _search_message_has_error(self, operator, operand):
        return ['&', ('message_ids.has_error', operator, operand), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    @api.multi
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
            for values in vals_list:
                message_follower_ids = values.get('message_follower_ids') or []
                message_follower_ids += [(0, 0, fol_vals) for fol_vals in self.env['mail.followers']._add_default_followers(self._name, [], self.env.user.partner_id.ids, customer_ids=[])[0][0]]
                values['message_follower_ids'] = message_follower_ids

        threads = super(MailThread, self).create(vals_list)

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not self._context.get('mail_create_nolog'):
            doc_name = self.env['ir.model']._get(self._name).name
            for thread in threads:
                thread._message_log(body=_('%s created') % doc_name)

        # auto_subscribe: take values and defaults into account
        for thread, values in pycompat.izip(threads, vals_list):
            create_values = dict(values)
            for key, val in self._context.items():
                if key.startswith('default_') and key[8:] not in create_values:
                    create_values[key[8:]] = val
            thread._message_auto_subscribe(create_values)

        # track values
        if not self._context.get('mail_notrack'):
            if not self._context.get('lang'):
                track_threads = threads.with_context(lang=self.env.user.lang)
            else:
                track_threads = threads
            for thread, values in pycompat.izip(track_threads, vals_list):
                tracked_fields = thread._get_tracked_fields(list(values))
                if tracked_fields:
                    initial_values = {thread.id: dict.fromkeys(tracked_fields, False)}
                    thread.message_track(tracked_fields, initial_values)

        return threads

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
            tracked_fields = track_self._get_tracked_fields(list(values))
        if tracked_fields:
            initial_values = dict((record.id, dict((key, getattr(record, key)) for key in tracked_fields))
                                  for record in track_self)

        # Perform write
        result = super(MailThread, self).write(values)

        # update followers
        self._message_auto_subscribe(values)

        # Perform the tracking
        if tracked_fields:
            track_self.with_context(clean_context(self._context)).message_track(tracked_fields, initial_values)

        return result

    @api.multi
    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        self.env['mail.message'].search([('model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        res = super(MailThread, self).unlink()
        self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        ).unlink()
        return res

    @api.multi
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
            email_link = "<a href='mailto:%(email)s'>%(email)s</a>" % {'email': alias.name_get()[0][1]}
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

    @api.multi
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
            ('subtype_id', '=', subtype_comment)])
        msg_not_comment = MailMessage.search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('subtype_id', '!=', subtype_comment)])

        # update the messages
        msg_comment.write({"res_id": new_thread.id, "model": new_thread._name})
        msg_not_comment.write({"res_id": new_thread.id, "model": new_thread._name, "subtype_id": None})
        return True

    # ------------------------------------------------------
    # Automatic log / Tracking
    # ------------------------------------------------------

    @api.model
    def _get_tracked_fields(self, updated_fields):
        """ Return a structure of tracked fields for the current model.
            :param list updated_fields: modified field names
            :return dict: a dict mapping field name to description, containing on_change fields
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
        if not any(change for rec_id, (change, tracking_value_ids) in tracking.items()):
            return True
        # Clean the context to get rid of residual default_* keys
        # that could cause issues afterward during the mail.message
        # generation. Example: 'default_parent_id' would refer to
        # the parent_id of the current record that was used during
        # its creation, but could refer to wrong parent message id,
        # leading to a traceback in case the related message_id
        # doesn't exist
        self = self.with_context(clean_context(self._context))
        templates = self._track_template(tracking)
        for field_name, (template, post_kwargs) in templates.items():
            if not template:
                continue
            if isinstance(template, pycompat.string_types):
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
        changes = set()  # contains onchange tracked fields that changed
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            initial_value = initial[col_name]
            new_value = getattr(self, col_name)

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                track_sequence = getattr(self._fields[col_name], 'track_sequence', 100)
                tracking = self.env['mail.tracking.value'].create_tracking_values(initial_value, new_value, col_name, col_info, track_sequence)
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

            if subtype_xmlid:
                subtype_rec = self.env.ref(subtype_xmlid)  # TDE FIXME check for raise if not found
                if not (subtype_rec and subtype_rec.exists()):
                    _logger.debug('subtype %s not found' % subtype_xmlid)
                    continue
                record.message_post(subtype=subtype_xmlid, tracking_value_ids=tracking_value_ids)
            elif tracking_value_ids:
                record._message_log(tracking_value_ids=tracking_value_ids)

        self._message_track_post_template(tracking)

        return True

    # ------------------------------------------------------
    # Email Notification
    # ------------------------------------------------------

    @api.model
    def _notify_encode_link(self, base_link, params):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params)))
        hm = hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha1).hexdigest()
        return hm

    @api.multi
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

        if self and hasattr(self, 'get_base_url'):
            link = self[0].get_base_url() + link

        return link

    @api.multi
    def _notify_get_groups(self, message, groups):
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
        return groups

    @api.multi
    def _notify_classify_recipients(self, message, recipient_data):
        """ Classify recipients to be notified of a message in groups to have
        specific rendering depending on their group. For example users could
        have access to buttons customers should not have in their emails.

        Module-specific grouping should be done by overriding ``_notify_get_groups``
        method defined here-under.

        :param message: mail.message record about to be notified
        :param recipients: res.partner recordset to notify UPDATE ME
        """
        result = {}

        access_link = self._notify_get_action_link('view')

        if message.model:
            model = self.env['ir.model'].with_context(
                lang=self.env.context.get('lang', self.env.user.lang))
            model_name = model._get(message.model).display_name
            view_title = _('View %s') % model_name
        else:
            view_title = _('View')

        default_groups = [
            ('user', lambda pdata: pdata['type'] == 'user', {}),
            ('portal', lambda pdata: pdata['type'] == 'portal', {
                'has_button_access': False,
            }),
            ('customer', lambda pdata: True, {
                'has_button_access': False,
            })
        ]

        groups = self._notify_get_groups(message, default_groups)

        for group_name, group_func, group_data in groups:
            group_data.setdefault('has_button_access', True)
            group_data.setdefault('button_access', {
                'url': access_link,
                'title': view_title})
            group_data.setdefault('actions', list())
            group_data.setdefault('recipients', list())

        for recipient in recipient_data:
            for group_name, group_func, group_data in groups:
                if group_func(recipient):
                    group_data['recipients'].append(recipient['id'])
                    break

        for group_name, group_method, group_data in groups:
            result[group_name] = group_data

        return result

    def _notify_classify_recipients_on_records(self, message, recipient_data, records=None):
        """ Generic wrapper on ``_notify_classify_recipients`` checking mail.thread
        inheritance and allowing to call model-specific implementation in a one liner.
        This method should not be overridden. """
        if records and hasattr(records, '_notify_classify_recipients'):
            return records._notify_classify_recipients(message, recipient_data)
        return self._notify_classify_recipients(message, recipient_data)

    @api.multi
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
            company_name = company.name if company else self.env.user.company_id.name
            for res_id in result_email.keys():
                name = '%s%s%s' % (company_name, ' ' if doc_names.get(res_id) else '', doc_names.get(res_id, ''))
                result[res_id] = formataddr((name, result_email[res_id]))

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

    @api.multi
    def _notify_specific_email_values(self, message):
        """ Get specific notification email values to store on the notification
        mail.mail. Override to add values related to a specific model.

        :param message: mail.message record being notified by email
        """
        if not self:
            return {}
        self.ensure_one()
        return {'headers': repr({
            'X-Odoo-Objects': "%s-%s" % (self._name, self.id),
        })}

    @api.model
    def _notify_specific_email_values_on_records(self, message, records=None):
        """ Generic wrapper on ``_notify_specific_email_values`` checking mail.thread
        inheritance and allowing to call model-specific implementation in a one liner.
        This method should not be overridden. """
        if records and hasattr(records, '_notify_specific_email_values'):
            return records._notify_specific_email_values(message)
        return self._notify_specific_email_values(message)

    @api.multi
    def _notify_email_recipients(self, message, recipient_ids):
        """ Format email notification recipient values to store on the notification
        mail.mail. Basic method just set the recipient partners as mail_mail
        recipients. Override to generate other mail values like email_to or
        email_cc.

        :param message: mail.message record being notified by email
        :param recipient_ids: res.partner recordset to notify
        """
        return {
            'recipient_ids': [(4, pid) for pid in recipient_ids]
        }

    @api.model
    def _notify_email_recipients_on_records(self, message, recipient_ids, records=None):
        """ Generic wrapper on ``_notify_email_recipients`` checking mail.thread
        inheritance and allowing to call model-specific implementation in a one liner.
        This method should not be overridden. """
        if records and hasattr(records, '_notify_email_recipients'):
            return records._notify_email_recipients(message, recipient_ids)
        return self._notify_email_recipients(message, recipient_ids)

    # ------------------------------------------------------
    # Mail gateway
    # ------------------------------------------------------

    def _message_find_partners(self, message, header_fields=['From']):
        """ Find partners related to some header fields of the message.

            :param string message: an email.message instance """
        s = ', '.join([tools.decode_smtp_header(message.get(h)) for h in header_fields if message.get(h)])
        return [x for x in self._find_partner_from_emails(tools.email_split(s)) if x]

    def _routing_warn(self, error_message, warn_suffix, message_id, route, raise_exception):
        """ Tools method used in message_route_verify: whether to log a warning or raise an error """
        short_message = _("Mailbox unavailable - %s") % error_message
        full_message = ('Routing mail with Message-Id %s: route %s: %s' %
                        (message_id, route, error_message))
        _logger.info(full_message + (warn_suffix and '; %s' % warn_suffix or ''))
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
    def message_route_verify(self, message, message_dict, route,
                             update_author=True, assert_model=True,
                             create_fallback=True, allow_private=False,
                             drop_alias=False):
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
        :param update_author: update message_dict['author_id']. TDE TODO: move me
        :param assert_model: if an error occurs, tell whether to raise an error
                             or just log a warning and try other processing or
                             invalidate route
        :param create_fallback: if the route aims at updating a record and that
                                record does not exists or does not support update
                                either fallback on creating a new record in the
                                same model or raise / warn
        :param allow_private: allow void model / thread_id routes, aka private
                              discussions
        """

        assert isinstance(route, (list, tuple)), 'A route should be a list or a tuple'
        assert len(route) == 5, 'A route should contain 5 elements: model, thread_id, custom_values, uid, alias record'

        message_id = message.get('Message-Id')
        email_from = tools.decode_message_header(message, 'From')
        author_id = message_dict.get('author_id')
        model, thread_id, alias = route[0], route[1], route[4]
        record_set = None

        _generic_bounce_body_html = """<div>
<p>Hello,</p>
<p>The following email sent to %s cannot be accepted because this is a private email address.
   Only allowed people can contact us at this address.</p>
</div><blockquote>%s</blockquote>""" % (message.get('to'), message_dict.get('body'))

        # Wrong model
        if model and model not in self.env:
            self._routing_warn(_('unknown target model %s') % model, '', message_id, route, assert_model)
            return ()

        # Private message
        if not model:
            # should not contain any thread_id
            if thread_id:
                self._routing_warn(_('posting a message without model should be with a null res_id (private message), received %s') % thread_id, _('resetting thread_id'), message_id, route, assert_model)
                thread_id = 0
            # should have a parent_id (only answers)
            if not message_dict.get('parent_id'):
                self._routing_warn(_('posting a message without model should be with a parent_id (private message)'), _('skipping'), message_id, route, assert_model)
                return False

        if model and thread_id:
            record_set = self.env[model].browse(thread_id)
        elif model:
            record_set = self.env[model]

        # Existing Document: check if exists and model accepts the mailgateway; if not, fallback on create if allowed
        if thread_id:
            if not record_set.exists() and create_fallback:
                self._routing_warn(_('reply to missing document (%s,%s), fall back on new document creation') % (model, thread_id), '', message_id, route, False)
                thread_id = None
            elif not hasattr(record_set, 'message_update') and create_fallback:
                self._routing_warn(_('model %s does not accept document update, fall back on document creation') % model, '', message_id, route, False)
                thread_id = None

            if not record_set.exists():
                self._routing_warn(_('reply to missing document (%s,%s)') % (model, thread_id), _('skipping'), message_id, route, assert_model)
                return False
            elif not hasattr(record_set, 'message_update'):
                self._routing_warn(_('model %s does not accept document update') % model, _('skipping'), message_id, route, assert_model)
                return False

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(record_set, 'message_new'):
            self._routing_warn(_('model %s does not accept document creation') % model, _('skipping'), message_id, route, assert_model)
            return False

        # Update message author if asked. We do it now because we need it for aliases (contact settings)
        if not author_id and update_author:
            author_ids = self.env['mail.thread']._find_partner_from_emails([email_from], res_model=model, res_id=thread_id)
            if author_ids:
                message_dict['author_id'] = author_ids[0]

        # Alias: check alias_contact settings
        if alias:
            obj = None
            if thread_id:
                obj = record_set[0]
            elif alias.alias_parent_model_id and alias.alias_parent_thread_id:
                obj = self.env[alias.alias_parent_model_id.model].browse(alias.alias_parent_thread_id)
            elif model:
                obj = self.env[model]
            if hasattr(obj, '_alias_check_contact'):
                check_result = obj._alias_check_contact(message, message_dict, alias)
            else:
                check_result = self.env['mail.alias.mixin']._alias_check_contact_on_record(obj, message, message_dict, alias)
            if check_result is not True:
                self._routing_warn(_('alias %s: %s') % (alias.alias_name, check_result.get('error_message', _('unknown error'))), _('skipping'), message_id, route, False)
                self._routing_create_bounce_email(email_from, check_result.get('error_template', _generic_bounce_body_html), message)
                return False

        if not model and not thread_id and not alias and not allow_private:
            return False

        return (model, thread_id, route[2], route[3], None if drop_alias else route[4])

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
           take place
         * if the message replies to an existing thread by having In-Reply-To or
           References matching odoo model/thread_id Message-Id and if this thread
           has messages without message_id, take this model/thread_id pair and
           ignore custom_value as no creation will take place (6.1 compatibility)
         * look for a mail.alias entry matching the message recipients and use the
           corresponding model, thread_id, custom_values and user_id. This could
           lead to a thread update or creation depending on the alias
         * fallback on provided ``model``, ``thread_id`` and ``custom_values``
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
        MailMessage = self.env['mail.message']
        Alias, dest_aliases = self.env['mail.alias'], self.env['mail.alias']
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        alias_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        # activate strict alias domain check for stable, will be falsy by default to be backward compatible
        alias_domain_check = tools.str2bool(self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain.strict", "False"))
        fallback_model = model

        # get email.message.Message variables for future processing
        message_id = message.get('Message-Id')

        # compute references to find if message is a reply to an existing thread
        references = tools.decode_message_header(message, 'References')
        in_reply_to = tools.decode_message_header(message, 'In-Reply-To').strip()
        thread_references = references or in_reply_to
        reply_match, reply_model, reply_thread_id, reply_hostname, reply_private = tools.email_references(thread_references)

        # author and recipients
        email_from = tools.decode_message_header(message, 'From')
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = tools.decode_message_header(message, 'To')
        email_to_localparts = [
            e.split('@', 1)[0].lower()
            for e in (tools.email_split(email_to) or [''])
            if not alias_domain_check or (not alias_domain or e.endswith('@%s' % alias_domain))
        ]

        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = ','.join([
            tools.decode_message_header(message, 'Delivered-To'),
            tools.decode_message_header(message, 'To'),
            tools.decode_message_header(message, 'Cc'),
            tools.decode_message_header(message, 'Resent-To'),
            tools.decode_message_header(message, 'Resent-Cc')])
        rcpt_tos_localparts = [
            e.split('@')[0].lower()
            for e in tools.email_split(rcpt_tos)
            if not alias_domain_check or (not alias_domain or e.endswith('@%s' % alias_domain))
        ]

        # 0. Verify whether this is a bounced email and use it to collect bounce data and update notifications for customers
        if bounce_alias and any(email.startswith(bounce_alias) for email in email_to_localparts):
            # Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)

            if bounce_match:
                bounced_mail_id, bounced_model, bounced_thread_id = bounce_match.group(1), bounce_match.group(2), bounce_match.group(3)

                email_part = next((part for part in message.walk() if part.get_content_type() == 'message/rfc822'), None)
                dsn_part = next((part for part in message.walk() if part.get_content_type() == 'message/delivery-status'), None)

                partners, partner_address = self.env['res.partner'], False
                if dsn_part and len(dsn_part.get_payload()) > 1:
                    dsn = dsn_part.get_payload()[1]
                    final_recipient_data = tools.decode_message_header(dsn, 'Final-Recipient')
                    partner_address = final_recipient_data.split(';', 1)[1].strip()
                    if partner_address:
                        partners = partners.sudo().search([('email', '=', partner_address)])
                        for partner in partners:
                            partner.message_receive_bounce(partner_address, partner, mail_id=bounced_mail_id)

                mail_message = self.env['mail.message']
                if email_part:
                    email = email_part.get_payload()[0]
                    bounced_message_id = tools.mail_header_msgid_re.findall(tools.decode_message_header(email, 'Message-Id'))
                    mail_message = MailMessage.sudo().search([('message_id', 'in', bounced_message_id)])

                if partners and mail_message:
                    notifications = self.env['mail.notification'].sudo().search([
                        ('mail_message_id', '=', mail_message.id),
                        ('res_partner_id', 'in', partners.ids)])
                    notifications.write({
                        'email_status': 'bounce'
                    })

                if bounced_model in self.env and hasattr(self.env[bounced_model], 'message_receive_bounce') and bounced_thread_id:
                    self.env[bounced_model].browse(int(bounced_thread_id)).message_receive_bounce(partner_address, partners, mail_id=bounced_mail_id)

                _logger.info('Routing mail from %s to %s with Message-Id %s: bounced mail from mail %s, model: %s, thread_id: %s: dest %s (partner %s)',
                             email_from, email_to, message_id, bounced_mail_id, bounced_model, bounced_thread_id, partner_address, partners)
                return []

        # 0. First check if this is a bounce message or not.
        #    See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #    As all MTA does not respect this RFC (googlemail is one of them),
        #    we also need to verify if the message come from "mailer-daemon"
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            _logger.info('Routing mail with Message-Id %s: not routing bounce email from %s to %s',
                         message_id, email_from, email_to)
            return []

        # 1. Check if message is a reply on a thread
        msg_references = [ref for ref in tools.mail_header_msgid_re.findall(thread_references) if 'reply_to' not in ref]
        mail_messages = MailMessage.sudo().search([('message_id', 'in', msg_references)], limit=1, order='id desc, message_id')
        is_a_reply = bool(mail_messages)
        alias_domain = [('alias_name', 'in', rcpt_tos_localparts)]

        # 1.1 Handle forward to an alias with a different model: do not consider it as a reply
        if reply_model and reply_thread_id:
            other_aliases = Alias.search([
                '&',
                ('alias_name', '!=', False),
                ('alias_name', 'in', email_to_localparts),
            ])
            for other_alias in other_aliases:
                if other_alias.alias_model_id.model == reply_model:
                    is_a_reply = bool(mail_messages)
                    alias_domain.append(("alias_model_id.model", "=", reply_model))
                    break
                if other_alias.alias_model_id.model != reply_model:
                    is_a_reply = False

        if is_a_reply:
            model, thread_id = mail_messages.model, mail_messages.res_id
            if not reply_private:  # TDE note: not sure why private mode as no alias search, copying existing behavior
                dest_aliases = Alias.search(alias_domain, limit=1)

            route = self.message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, dest_aliases),
                update_author=True, assert_model=reply_private, create_fallback=True,
                allow_private=reply_private, drop_alias=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 2. Look for a matching mail.alias entry
        if rcpt_tos_localparts:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and all(email_localpart == catchall_alias for email_localpart in email_to_localparts):
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env.ref('mail.mail_bounce_catchall').render({
                    'message': message,
                }, engine='ir.qweb')
                self._routing_create_bounce_email(email_from, body, message, reply_to=self.env.user.company_id.email)
                return []

            dest_aliases = Alias.search(alias_domain)
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(message)
                        user_id = self._uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, safe_eval(alias.alias_defaults), user_id, alias)
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
        if fallback_model:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)
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
        original_partner_ids = message_dict.pop('partner_ids', [])
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
                MessageModel = Model.sudo(self.env.uid == 1 and user_id or None).with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
                if thread_id and hasattr(MessageModel, 'message_update'):
                    thread = MessageModel.browse(thread_id)
                    thread.message_update(message_dict)
                else:
                    # if a new thread is created, parent is irrelevant
                    message_dict.pop('parent_id', None)
                    thread = MessageModel.message_new(message_dict, custom_values)
                    thread_id = thread.id
            else:
                if thread_id:
                    raise ValueError("Posting a message without model should be with a null res_id, to create a private message.")
                thread = self.env['mail.thread']

            # replies to internal message are considered as notes, but parent message
            # author is added in recipients to ensure he is notified of a private answer
            partner_ids = []
            if message_dict.pop('internal', False):
                subtype = 'mail.mt_note'
                if message_dict.get('parent_id'):
                    parent_message = self.env['mail.message'].sudo().browse(message_dict['parent_id'])
                    if parent_message.author_id:
                        partner_ids = [(4, parent_message.author_id.id)]
            else:
                subtype = 'mail.mt_comment'

            post_params = dict(subtype=subtype, partner_ids=partner_ids, **message_dict)
            if not hasattr(thread, 'message_post'):
                post_params['model'] = model
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
            message = bytes(message.data)
        # message_from_string parses from a *native string*, except apparently
        # sometimes message is ISO-8859-1 binary data or some shit and the
        # straightforward version (pycompat.to_native) won't work right ->
        # always encode message to bytes then use the relevant method
        # depending on ~python version
        if isinstance(message, pycompat.text_type):
            message = message.encode('utf-8')
        extract = getattr(email, 'message_from_bytes', email.message_from_string)
        msg_txt = extract(message)

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

    @api.multi
    def message_receive_bounce(self, email, partner, mail_id=None):
        """Called by ``message_process`` when a bounce email (such as Undelivered
        Mail Returned to Sender) is received for an existing thread. The default
        behavior is to check is an integer  ``message_bounce`` column exists.
        If it is the case, its content is incremented.

        :param mail_id: ID of the sent email that bounced. It may not exist anymore
                        but it could be usefull if the information was kept. This is
                        used notably in mass mailing.
        :param RecordSet partner: partner matching the bounced email address, if any
        :param string email: email that caused the bounce """
        if 'message_bounce' in self._fields:
            for record in self:
                record.message_bounce = record.message_bounce + 1

    def _message_extract_payload_postprocess(self, message, body, attachments):
        """ Perform some cleaning / postprocess in the body and attachments
        extracted from the email. Note that this processing is specific to the
        mail module, and should not contain security or generic html cleaning.
        Indeed those aspects should be covered by the html_sanitize method
        located in tools. """
        if not body:
            return body, attachments
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
            body = etree.tostring(root, pretty_print=False, encoding='UTF-8')
            body = pycompat.to_native(body)
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
            # message_from_string works on a native str
            message = pycompat.to_native(message)
            message = email.message_from_string(message)

        message_id = message['message-id']
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id.strip()

        if message.get('Subject'):
            msg_dict['subject'] = tools.decode_smtp_header(message.get('Subject'))

        # Envelope fields not stored in mail.message but made available for message_new()
        msg_dict['from'] = tools.decode_smtp_header(message.get('from'), quoted=True)
        msg_dict['to'] = tools.decode_smtp_header(message.get('to'), quoted=True)
        msg_dict['cc'] = tools.decode_smtp_header(message.get('cc'), quoted=True)
        msg_dict['email_from'] = tools.decode_smtp_header(message.get('from'), quoted=True)
        partner_ids = self._message_find_partners(message, ['To', 'Cc'])
        msg_dict['partner_ids'] = [(4, partner_id) for partner_id in partner_ids]

        if message.get('Date'):
            try:
                date_hdr = tools.decode_smtp_header(message.get('Date'))
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
            parent_ids = self.env['mail.message'].search([('message_id', '=', tools.decode_smtp_header(message['In-Reply-To'].strip()))], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id
                msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list = tools.mail_header_msgid_re.findall(tools.decode_smtp_header(message['References']))
            parent_ids = self.env['mail.message'].search([('message_id', 'in', [x.strip() for x in msg_list])], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id
                msg_dict['internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        return msg_dict

    # ------------------------------------------------------
    # Recipient management
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
            elif 'partner_email' in self._fields and record.partner_email:
                email_to = record.partner_email
            elif 'email' in self._fields:
                email_to = record.email
            res[record.id] = {'partner_ids': list(recipient_ids), 'email_to': email_to, 'email_cc': email_cc}
        return res

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

    def _search_on_user(self, email_address, extra_domain=[]):
        Users = self.env['res.users'].sudo()
        # exact, case-insensitive match
        partners = Users.search([('email', '=ilike', email_address)], limit=1).mapped('partner_id')
        if not partners:
            # if no match with addr-spec, attempt substring match within name-addr pair
            email_brackets = "<%s>" % email_address
            partners = Users.search([('email', 'ilike', email_brackets)], limit=1).mapped('partner_id')
        return partners.id

    def _search_on_partner(self, email_address, extra_domain=[]):
        Partner = self.env['res.partner'].sudo()
        # exact, case-insensitive match
        partners = Partner.search([('email', '=ilike', email_address)] + extra_domain, limit=1)
        if not partners:
            # if no match with addr-spec, attempt substring match within name-addr pair
            email_brackets = "<%s>" % email_address
            partners = Partner.search([('email', 'ilike', email_brackets)] + extra_domain, limit=1)
        return partners.id

    @api.multi
    def _find_partner_from_emails(self, emails, res_model=None, res_id=None, check_followers=True, force_create=False, exclude_aliases=True):
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
            :param boolean exclude_aliases: do not try to find a partner that could match an alias. Normally aliases
                                            should not be used as partner emails but it could be the case due to some
                                            strange manipulation
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

        partner_ids = []

        for contact in emails:
            partner_id = False
            email_address = tools.email_split(contact)
            if not email_address:
                partner_ids.append(partner_id)
                continue
            if exclude_aliases and self.env['mail.alias'].search([('alias_name', 'ilike', email_address)], limit=1):
                partner_ids.append(partner_id)
                continue

            email_address = email_address[0]
            # Escape special SQL characters in email_address to avoid invalid matches
            email_address = tools.email_escape_char(email_address)

            # first try: check in document's followers
            partner_id = next((partner.id for partner in followers if partner.email == email_address), False)
            # second try: check in partners that are also users
            if not partner_id:
                partner_id = self._search_on_user(email_address)
            # third try: check in partners
            if not partner_id:
                partner_id = self._search_on_partner(email_address)
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

    # ------------------------------------------------------
    # Post / Send message API
    # ------------------------------------------------------

    def _message_post_process_attachments(self, attachments, attachment_ids, message_data):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``,
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param dict message_data: model: the model of the attachments parent record,
          res_id: the id of the attachments parent record
        """
        IrAttachment = self.env['ir.attachment']
        m2m_attachment_ids = []
        cid_mapping = {}
        fname_mapping = {}
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
                cid = info and info.get('cid')
            else:
                continue
            if isinstance(content, pycompat.text_type):
                content = content.encode('utf-8')
            elif content is None:
                continue
            data_attach = {
                'name': name,
                'datas': base64.b64encode(content),
                'type': 'binary',
                'datas_fname': name,
                'description': name,
                'res_model': message_data['model'],
                'res_id': message_data['res_id'],
            }
            new_attachment = IrAttachment.create(data_attach)
            m2m_attachment_ids.append((4, new_attachment.id))
            if cid:
                cid_mapping[cid] = new_attachment
            fname_mapping[name] = new_attachment

        if cid_mapping and message_data.get('body'):
            root = lxml.html.fromstring(tools.ustr(message_data['body']))
            postprocessed = False
            for node in root.iter('img'):
                if node.get('src', '').startswith('cid:'):
                    cid = node.get('src').split('cid:')[1]
                    attachment = cid_mapping.get(cid)
                    if not attachment:
                        attachment = fname_mapping.get(node.get('data-filename'), '')
                    if attachment:
                        attachment.generate_access_token()
                        node.set('src', '/web/image/%s?access_token=%s' % (attachment.id, attachment.access_token))
                        postprocessed = True
            if postprocessed:
                body = lxml.html.tostring(root, pretty_print=False, encoding='UTF-8')
                message_data['body'] = body

        return m2m_attachment_ids

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, body='', subject=None,
                     message_type='notification', subtype=None,
                     parent_id=False, attachments=None,
                     notif_layout=False, add_sign=True, model_description=False,
                     mail_auto_delete=True, **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID.
            :param int thread_id: thread ID to post into, or list with one ID;
                if False/0, mail.message model will also be set as False
            :param str body: body of the message, usually raw HTML that will
                be sanitized
            :param str type: see mail_message.message_type field
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
            model = kwargs.get('model', False) if self._name == 'mail.thread' else self._name
            if model and model != self._name and hasattr(self.env[model], 'message_post'):
                return self.env[model].browse(self.ids).message_post(
                    body=body, subject=subject, message_type=message_type,
                    subtype=subtype, parent_id=parent_id, attachments=attachments,
                    notif_layout=notif_layout, add_sign=add_sign,
                    mail_auto_delete=mail_auto_delete, model_description=model_description, **kwargs)

        # 0: Find the message's author, because we need it for private discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.env['mail.message']._get_default_author().id

        # 2: Private message: add recipients (recipients and author of parent message) - current author
        #   + legacy-code management (! we manage only 4 and 6 commands)
        partner_ids = set()
        kwargs_partner_ids = kwargs.pop('partner_ids', [])
        for partner_id in kwargs_partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                partner_ids.add(partner_id[1])
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                partner_ids |= set(partner_id[2])
            elif isinstance(partner_id, pycompat.integer_types):
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
                partner_to_subscribe = [p for p in partner_ids if p in self._context.get('mail_post_autofollow_partner_ids')]
            self.message_subscribe(list(partner_to_subscribe))

        # _mail_flat_thread: automatically set free messages to the first posted message
        MailMessage = self.env['mail.message']
        if self._mail_flat_thread and model and not parent_id and self.ids:
            messages = MailMessage.search(['&', ('res_id', '=', self.ids[0]), ('model', '=', model)], order="id ASC", limit=1)
            parent_id = messages.ids and messages.ids[0] or False
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
            'channel_ids': kwargs.get('channel_ids', []),
            'add_sign': add_sign
        })
        if notif_layout:
            values['layout'] = notif_layout

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_post_process_attachments(attachments, kwargs.pop('attachment_ids', []), values)
        values['attachment_ids'] = attachment_ids

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        # canned_response_ids are added by js to be used by other computations (odoobot)
        # we need to pop it from values since it is not stored on mail.message
        canned_response_ids = values.pop('canned_response_ids', False)
        new_message = MailMessage.create(values)
        values['canned_response_ids'] = canned_response_ids
        self._message_post_after_hook(new_message, values, model_description=model_description, mail_auto_delete=mail_auto_delete)
        return new_message

    def _message_post_after_hook(self, message, msg_vals, model_description=False, mail_auto_delete=True):
        """ Hook to add custom behavior after having posted the message. Both
        message and computed value are given, to try to lessen query count by
        using already-computed values instead of having to rebrowse things. """
        # Set main attachment field if necessary
        attachment_ids = msg_vals['attachment_ids']
        if not self._abstract and attachment_ids and self.ids and not self.message_main_attachment_id:
            all_attachments = self.env['ir.attachment'].browse([attachment_tuple[1] for attachment_tuple in attachment_ids])
            prioritary_attachments = all_attachments.filtered(lambda x: x.mimetype.endswith('pdf')) \
                                     or all_attachments.filtered(lambda x: x.mimetype.startswith('image')) \
                                     or all_attachments
            self.sudo().write({'message_main_attachment_id': prioritary_attachments[0].id})
        # Notify recipients of the newly-created message (Inbox / Email + channels)
        if msg_vals.get('moderation_status') != 'pending_moderation':
            message._notify(
                self, msg_vals,
                force_send=self.env.context.get('mail_notify_force_send', True),
                send_after_commit=True,
                model_description=model_description,
                mail_auto_delete=mail_auto_delete,
            )

            # Post-process: subscribe author
            if msg_vals['author_id'] and msg_vals['model'] and self.ids and msg_vals['message_type'] != 'notification' and not self._context.get('mail_create_nosubscribe'):
                self._message_subscribe([msg_vals['author_id']])
        else:
            message._notify_pending_by_chat()

    @api.multi
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
        if isinstance(views_or_xmlid, pycompat.string_types):
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
        res_id = kwargs.get('res_id', self.ids and self.ids[0] or 0)
        res_ids = kwargs.get('res_id') and [kwargs['res_id']] or self.ids
        notif_layout = kwargs.pop('notif_layout', None)

        # Create the composer
        composer = self.env['mail.compose.message'].with_context(
            active_id=res_id,
            active_ids=res_ids,
            active_model=kwargs.get('model', self._name),
            default_composition_mode=kwargs['composition_mode'],
            default_model=kwargs.get('model', self._name),
            default_res_id=res_id,
            default_template_id=template_id,
            custom_layout=notif_layout,
        ).create(kwargs)
        # Simulate the onchange (like trigger in form the view) only
        # when having a template in single-email mode
        if template_id:
            update_values = composer.onchange_template_id(template_id, kwargs['composition_mode'], self._name, res_id)['value']
            composer.write(update_values)
        return composer.send_mail()

    def message_notify(self, partner_ids, body='', subject=False, **kwargs):
        """ Shortcut allowing to notify partners of messages not linked to
        any document. It pushes notifications on inbox or by email depending
        on the user configuration, like other notifications. """
        kw_author = kwargs.pop('author_id', False)
        if kw_author:
            author = self.env['res.partner'].sudo().browse(kw_author)
        else:
            author = self.env.user.partner_id
        if not author.email:
            raise exceptions.UserError(_("Unable to notify message, please configure the sender's email address."))
        email_from = formataddr((author.name, author.email))

        msg_values = {
            'subject': subject,
            'body': body,
            'author_id': author.id,
            'email_from': email_from,
            'message_type': 'notification',
            'partner_ids': partner_ids,
            'model': False,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        msg_values.update(kwargs)
        return self.env['mail.thread'].message_post(**msg_values)

    def _message_log(self, body='', subject=False, message_type='notification', **kwargs):
        """ Shortcut allowing to post note on a document. It does not perform
        any notification and pre-computes some values to have a short code
        as optimized as possible. This method is private as it does not check
        access rights and perform the message creation as sudo to speedup
        the log process. This method should be called within methods where
        access rights are already granted to avoid privilege escalation. """
        if len(self.ids) > 1:
            raise exceptions.Warning(_('Invalid record set: should be called as model (without records) or on single-record recordset'))

        kw_author = kwargs.pop('author_id', False)
        if kw_author:
            author = self.env['res.partner'].sudo().browse(kw_author)
        else:
            author = self.env.user.partner_id
        if not author.email:
            raise exceptions.UserError(_("Unable to log message, please configure the sender's email address."))
        email_from = formataddr((author.name, author.email))

        message_values = {
            'subject': subject,
            'body': body,
            'author_id': author.id,
            'email_from': email_from,
            'message_type': message_type,
            'model': kwargs.get('model', self._name),
            'res_id': self.ids[0] if self.ids else False,
            'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
            'record_name': False,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from, records=None)[False],
            'message_id': tools.generate_tracking_message_id('message-notify'),
        }
        message_values.update(kwargs)
        message = self.env['mail.message'].sudo().create(message_values)
        return message

    # ------------------------------------------------------
    # Followers API
    # ------------------------------------------------------

    @api.multi
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
        for name, field in self._fields.items():
            if name == 'user_id' and updated_values.get(name) and getattr(field, 'track_visibility', False):
                if field.comodel_name == 'res.users':
                    fnames.append(name)

        new_subscriptions = []
        user_ids = [updated_values[fname] for fname in fnames if updated_values[fname]]
        if user_ids:
            new_pids = self.env['res.partner'].sudo().search([('user_ids', 'in', user_ids), ('active', '=', True)]).ids
            for new_pid in new_pids:
                new_subscriptions.append((new_pid, default_subtype_ids, 'mail.message_user_assigned' if new_pid != self.env.user.partner_id.id else False))

        return new_subscriptions

    @api.multi
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
                partner_ids=[(4, pid) for pid in partner_ids],
                record_name=record.display_name,
                notif_layout='mail.mail_notification_light',
                model_description=model_description,
            )

    @api.multi
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
                partner = self.env['res.partner'].browse(pid, self._prefetch)
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
