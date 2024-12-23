# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import dateutil
import email
import email.policy
import hashlib
import hmac
import json
import lxml
import logging
import pytz
import re
import time
import threading

from collections import namedtuple
from collections.abc import Iterable
from email import message_from_string
from email.message import EmailMessage
from xmlrpc import client as xmlrpclib

from lxml import etree
from markupsafe import Markup, escape
from requests import Session
from werkzeug import urls

from odoo import _, api, exceptions, fields, models, Command
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.web_push import push_to_end_point, DeviceUnreachableError
from odoo.exceptions import MissingError, AccessError
from odoo.osv import expression
from odoo.tools import (
    is_html_empty, html_escape, html2plaintext, parse_contact_from_email,
    clean_context, split_every, Query, SQL,
    ormcache, is_list_of,
)
from odoo.tools.mail import (
    append_content_to_html, decode_message_header, email_normalize,
    email_normalize_all, email_split,
    email_split_and_format, formataddr, html_sanitize,
    generate_tracking_message_id,
    unfold_references,
)

MAX_DIRECT_PUSH = 5

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
                resource. If set to False, the display of Chatter is done using
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
    _description = 'Email Thread'
    _mail_flat_thread = True  # flatten the discussion history
    _mail_post_access = 'write'  # access required on the document to post on it
    _primary_email = 'email'  # Must be set for the models that can be created by alias
    _Attachment = namedtuple('Attachment', ('fname', 'content', 'info'))

    message_is_follower = fields.Boolean(
        'Is Follower', compute='_compute_message_is_follower', search='_search_message_is_follower')
    message_follower_ids = fields.One2many(
        'mail.followers', 'res_id', string='Followers', groups='base.group_user')
    message_partner_ids = fields.Many2many(
        comodel_name='res.partner', string='Followers (Partners)',
        compute='_compute_message_partner_ids',
        inverse='_inverse_message_partner_ids',
        search='_search_message_partner_ids',
        groups='base.group_user',
    )
    message_ids = fields.One2many(
        'mail.message', 'res_id', string='Messages',
        domain=lambda self: [('message_type', '!=', 'user_notification')], auto_join=True)
    has_message = fields.Boolean(compute="_compute_has_message", search="_search_has_message", store=False)
    message_needaction = fields.Boolean(
        'Action Needed',
        compute='_compute_message_needaction', search='_search_message_needaction',
        help="If checked, new messages require your attention.")
    message_needaction_counter = fields.Integer(
        'Number of Actions', compute='_compute_message_needaction',
        help="Number of messages requiring action")
    message_has_error = fields.Boolean(
        'Message Delivery error',
        compute='_compute_message_has_error', search='_search_message_has_error',
        help="If checked, some messages have a delivery error.")
    message_has_error_counter = fields.Integer(
        'Number of errors', compute='_compute_message_has_error',
        help="Number of messages with delivery error")
    message_attachment_count = fields.Integer('Attachment Count', compute='_compute_message_attachment_count', groups="base.group_user")

    @api.depends('message_follower_ids')
    def _compute_message_partner_ids(self):
        for thread in self:
            thread.message_partner_ids = thread.message_follower_ids.mapped('partner_id')

    def _inverse_message_partner_ids(self):
        for thread in self:
            new_partners_ids = thread.message_partner_ids
            previous_partners_ids = thread.message_follower_ids.partner_id
            removed_partners_ids = previous_partners_ids - new_partners_ids
            added_patners_ids = new_partners_ids - previous_partners_ids
            if added_patners_ids:
                thread.message_subscribe(added_patners_ids.ids)
            if removed_partners_ids:
                thread.message_unsubscribe(removed_partners_ids.ids)

    @api.model
    def _search_message_partner_ids(self, operator, operand):
        """Search function for message_follower_ids"""
        neg = ''
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            neg = 'not '
            operator = expression.TERM_OPERATORS_NEGATION[operator]
        followers = self.env['mail.followers'].sudo()._search([
            ('res_model', '=', self._name),
            ('partner_id', operator, operand),
        ])
        # use `in` query to avoid reading thousands of potentially followed objects
        return [('id', neg + 'in', followers.subselect('res_id'))]

    @api.depends('message_follower_ids')
    def _compute_message_is_follower(self):
        followers = self.env['mail.followers'].sudo().search_fetch(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids), ('partner_id', '=', self.env.user.partner_id.id)],
            ['res_id'],
        )
        following_ids = set(followers.mapped('res_id'))
        for record in self:
            record.message_is_follower = record.id in following_ids

    @api.model
    def _search_message_is_follower(self, operator, operand):
        followers = self.env['mail.followers'].sudo().search_fetch(
            [('res_model', '=', self._name), ('partner_id', '=', self.env.user.partner_id.id)],
            ['res_id'],
        )
        # Cases ('message_is_follower', '=', True) or  ('message_is_follower', '!=', False)
        if (operator == '=' and operand) or (operator == '!=' and not operand):
            return [('id', 'in', followers.mapped('res_id'))]
        else:
            return [('id', 'not in', followers.mapped('res_id'))]

    def _compute_has_message(self):
        self.env['mail.message'].flush_model()
        self.env.cr.execute("""
            SELECT distinct res_id
              FROM mail_message mm
             WHERE res_id = any(%s)
               AND mm.model=%s
        """, [self.ids, self._name])
        channel_ids = {r[0] for r in self.env.cr.fetchall()}
        for record in self:
            record.has_message = record.id in channel_ids

    def _search_has_message(self, operator, value):
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            operator_new = 'in'
        else:
            operator_new = 'not in'
        return [('id', operator_new, SQL("(SELECT res_id FROM mail_message WHERE model = %s)", self._name))]

    def _compute_message_needaction(self):
        res = dict.fromkeys(self.ids, 0)
        if self.ids:
            # search for unread messages, directly in SQL to improve performances
            self._cr.execute(""" SELECT msg.res_id FROM mail_message msg
                                 RIGHT JOIN mail_notification rel
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
            self.env.cr.execute("""
                    SELECT msg.res_id, COUNT(msg.res_id)
                      FROM mail_message msg
                INNER JOIN mail_notification notif
                        ON notif.mail_message_id = msg.id
                     WHERE notif.notification_status in ('exception', 'bounce')
                       AND notif.author_id = %(author_id)s
                       AND msg.model = %(model_name)s
                       AND msg.res_id in %(res_ids)s
                       AND msg.message_type != 'user_notification'
                  GROUP BY msg.res_id
            """, {'author_id': self.env.user.partner_id.id, 'model_name': self._name, 'res_ids': tuple(self.ids)})
            res.update(self._cr.fetchall())

        for record in self:
            record.message_has_error_counter = res.get(record._origin.id, 0)
            record.message_has_error = bool(record.message_has_error_counter)

    @api.model
    def _search_message_has_error(self, operator, operand):
        message_ids = self.env['mail.message']._search([('has_error', operator, operand), ('author_id', '=', self.env.user.partner_id.id)])
        return [('message_ids', 'in', message_ids)]

    def _compute_message_attachment_count(self):
        read_group_var = self.env['ir.attachment']._read_group([('res_id', 'in', self.ids), ('res_model', '=', self._name)],
                                                              groupby=['res_id'],
                                                              aggregates=['__count'])

        attachment_count_dict = dict(read_group_var)
        for record in self:
            record.message_attachment_count = attachment_count_dict.get(record.id, 0)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ Chatter override :
            - subscribe uid
            - subscribe followers of parent
            - log a creation message
        """
        if self._context.get('tracking_disable'):
            threads = super(MailThread, self).create(vals_list)
            threads._track_discard()
            return threads

        threads = super(MailThread, self).create(vals_list)
        # subscribe uid unless asked not to
        if not self._context.get('mail_create_nosubscribe') and threads and self.env.user.active:
            self.env['mail.followers']._insert_followers(
                threads._name, threads.ids,
                self.env.user.partner_id.ids, subtypes=None,
                customer_ids=[],
                check_existing=False
            )

        # auto_subscribe: take values and defaults into account
        create_values_list = {}
        for thread, values in zip(threads, vals_list):
            create_values = dict(values)
            for key, val in self._context.items():
                if key.startswith('default_') and key[8:] not in create_values:
                    create_values[key[8:]] = val
            thread._message_auto_subscribe(create_values, followers_existing_policy='update')
            create_values_list[thread.id] = create_values

        # automatic logging unless asked not to (mainly for various testing purpose)
        if not self._context.get('mail_create_nolog'):
            threads_no_subtype = self.env[self._name]
            for thread in threads:
                subtype = thread._creation_subtype()
                if not subtype:
                    threads_no_subtype += thread
                    continue
                # if we have a subtype, post message to notify users from _message_auto_subscribe
                thread.sudo().message_post(
                    subtype_id=subtype.id, author_id=self.env.user.partner_id.id,
                    # summary="o_mail_notification" is used to hide the message body in the front-end
                    body=Markup('<div summary="o_mail_notification"><p>%s</p></div>') % thread._creation_message()
                )
            if threads_no_subtype:
                bodies = dict(
                    (thread.id, thread._creation_message())
                    for thread in threads_no_subtype)
                threads_no_subtype._message_log_batch(bodies=bodies)

        # post track template if a tracked field changed
        threads._track_discard()
        if not self._context.get('mail_notrack'):
            fnames = self._track_get_fields()
            for thread in threads:
                create_values = create_values_list[thread.id]
                changes = [fname for fname in fnames if create_values.get(fname)]
                # based on tracked field to stay consistent with write
                # we don't consider that a falsy field is a change, to stay consistent with previous implementation,
                # but we may want to change that behaviour later.
                if changes:
                    self.env.cr.precommit.add(thread._track_post_template_finalize)  # call to _track_post_template_finalize bound to this record
                    self.env.cr.precommit.data.setdefault(f'mail.tracking.create.{self._name}.{thread.id}', changes)
        return threads

    def write(self, values):
        if self._context.get('tracking_disable'):
            return super(MailThread, self).write(values)

        if not self._context.get('mail_notrack'):
            self._track_prepare(self._fields)

        # Perform write
        result = super(MailThread, self).write(values)

        # update followers
        self._message_auto_subscribe(values)

        return result

    def unlink(self):
        """ Override unlink to delete messages and followers. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        # discard pending tracking
        self._track_discard()
        self.env['mail.message'].sudo().search([('model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        res = super(MailThread, self).unlink()
        self.env['mail.followers'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        ).unlink()
        return res

    def copy_data(self, default=None):
        # avoid tracking multiple temporary changes during copy
        return super(MailThread, self.with_context(mail_notrack=True)).copy_data(default=default)

    @api.model
    def get_empty_list_help(self, help_message):
        """ Override of BaseModel.get_empty_list_help() to generate an help message
        that adds alias information. """
        model = self._context.get('empty_list_help_model')
        res_id = self._context.get('empty_list_help_id')
        document_name = self._context.get('empty_list_help_document_name', _('document'))
        nothing_here = is_html_empty(help_message)
        alias = None

        # specific res_id -> find its alias (i.e. section_id specified)
        if model and res_id:
            record = self.env[model].sudo().browse(res_id)
            # check that the alias effectively creates new records
            if ('alias_id' in record and record.alias_id and
                record.alias_id.alias_name and record.alias_id.alias_domain and
                record.alias_id.alias_model_id.model == self._name and
                record.alias_id.alias_force_thread_id == 0):
                alias = record.alias_id
        # no res_id or res_id not linked to an alias -> generic help message, take a generic alias of the model
        if not alias and model and self.env.company.alias_domain_id:
            aliases = self.env['mail.alias'].search([
                ("alias_domain_id", "=", self.env.company.alias_domain_id.id),
                ("alias_parent_model_id.model", "=", model),
                ("alias_name", "!=", False),
                ('alias_force_thread_id', '=', False),
                ('alias_parent_thread_id', '=', False)], order='id ASC')
            if aliases and len(aliases) == 1:
                alias = aliases[0]

        if alias:
            email_link = Markup("<a href='mailto:%s'>%s</a>") % (alias.display_name, alias.display_name)
            if nothing_here:
                dyn_help = _("Add a new %(document)s or send an email to %(email_link)s",
                             document=html_escape(document_name),
                             email_link=email_link,
                            )
                return super().get_empty_list_help(f"<p class='o_view_nocontent_smiling_face'>{dyn_help}</p>")
            # do not add alias two times if it was added previously
            if "oe_view_nocontent_alias" not in help_message:
                dyn_help = _("Create new %(document)s by sending an email to %(email_link)s",
                             document=html_escape(document_name),
                             email_link=email_link,
                            )
                return super().get_empty_list_help(f"{help_message}<p class='oe_view_nocontent_alias'>{dyn_help}</p>")

        if nothing_here:
            dyn_help = _("Create new %(document)s", document=html_escape(document_name))
            return super().get_empty_list_help(f"<p class='o_view_nocontent_smiling_face'>{dyn_help}</p>")

        return super().get_empty_list_help(help_message)

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if "form" in res["views"] and isinstance(self.env[self._name], self.env.registry['mail.activity.mixin']):
            res["models"][self._name]["has_activities"] = True
        return res

    def _condition_to_sql(self, alias: str, field_expr: str, operator: str, value, query: Query) -> SQL:
        if self.env.su or self.env.user._is_internal():
            return super()._condition_to_sql(alias, field_expr, operator, value, query)
        if field_expr != 'message_partner_ids':
            return super()._condition_to_sql(alias, field_expr, operator, value, query)
        user_partner = self.env.user.partner_id
        allow_partner_ids = set((user_partner | user_partner.commercial_partner_id).ids)
        if isinstance(value, Iterable) and not isinstance(value, str):
            operand = value
        else:
            operand = {value}
        if not allow_partner_ids.issuperset(operand):
            raise AccessError(self.env._("Portal users can only filter threads by themselves as followers."))
        return super(MailThread, self.sudo())._condition_to_sql(alias, field_expr, operator, value, query)

    # ------------------------------------------------------
    # MODELS / CRUD HELPERS
    # ------------------------------------------------------

    def _compute_field_value(self, field):
        if not self._context.get('tracking_disable') and not self._context.get('mail_notrack'):
            self._track_prepare(f.name for f in self.pool.field_computed[field] if f.store)

        return super()._compute_field_value(field)

    def _creation_subtype(self):
        """ Give the subtypes triggered by the creation of a record

        :returns: a subtype browse record (empty if no subtype is triggered)
        """
        return self.env['mail.message.subtype']

    def _creation_message(self):
        """ Get the creation message to log into the chatter at the record's creation.
        :returns: The message's body to log (either plain text or markup safe html).
        """
        self.ensure_one()
        doc_name = self.env['ir.model']._get(self._name).name
        return _('%s created', doc_name)

    @api.model
    def _get_mail_message_access(self, res_ids, operation, model_name=None):
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

    def _valid_field_parameter(self, field, name):
        # allow tracking on models inheriting from 'mail.thread'
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    def _fallback_lang(self):
        if not self._context.get("lang"):
            return self.with_context(lang=self.env.user.lang)
        return self

    def _check_can_update_message_content(self, messages):
        """" Checks that the current user can update the content of the message.
        Current heuristic is

          * if no tracking;
          * only for user generated content;
        """
        if messages.tracking_value_ids:
            raise exceptions.UserError(_("Messages with tracking values cannot be modified"))
        if any(message.message_type != 'comment' for message in messages):
            raise exceptions.UserError(_("Only messages type comment can have their content updated"))

    # ------------------------------------------------------
    # TRACKING / LOG
    # ------------------------------------------------------

    def _track_prepare(self, fields_iter):
        """ Prepare the tracking of ``fields_iter`` for ``self``.

        :param iter fields_iter: iterable of fields names to potentially track
        """
        fnames = self._track_get_fields().intersection(fields_iter)
        if not fnames:
            return
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(f'mail.tracking.{self._name}', {})
        for record in self:
            if not record.id:
                continue
            values = initial_values.setdefault(record.id, {})
            if values is not None:
                for fname in fnames:
                    values.setdefault(fname, record[fname])

    def _track_discard(self):
        """ Prevent any tracking of fields on ``self``. """
        if not self._track_get_fields():
            return
        self.env.cr.precommit.add(self._track_finalize)
        initial_values = self.env.cr.precommit.data.setdefault(f'mail.tracking.{self._name}', {})
        # disable tracking by setting initial values to None
        for id_ in self.ids:
            initial_values[id_] = None

    def _track_filter_for_display(self, tracking_values):
        """Filter out tracking values from being displayed."""
        self.ensure_one()
        return tracking_values

    def _track_finalize(self):
        """ Generate the tracking messages for the records that have been
        prepared with ``_tracking_prepare``.
        """
        initial_values = self.env.cr.precommit.data.pop(f'mail.tracking.{self._name}', {})
        ids = [id_ for id_, vals in initial_values.items() if vals]
        if not ids:
            return
        records = self.browse(ids).sudo()
        fnames = self._track_get_fields()
        context = clean_context(self._context)
        tracking = records.with_context(context)._message_track(fnames, initial_values)
        for record in records:
            changes, _tracking_value_ids = tracking.get(record.id, (None, None))
            record._message_track_post_template(changes)
        # this method is called after the main flush() and just before commit();
        # we have to flush() again in case we triggered some recomputations
        self.env.flush_all()

    def _track_set_author(self, author):
        """ Set the author of the tracking message. """
        if not self._track_get_fields():
            return
        authors = self.env.cr.precommit.data.setdefault(f'mail.tracking.author.{self._name}', {})
        for id_ in self.ids:
            authors[id_] = author

    def _track_post_template_finalize(self):
        """Call the tracking template method with right values from precommit."""
        self._message_track_post_template(self.env.cr.precommit.data.pop(f'mail.tracking.create.{self._name}.{self.id}', []))
        self.env.flush_all()

    def _track_set_log_message(self, message):
        """ Link tracking to a message logged as body, in addition to subtype
        description (if set) and tracking values that make the core content of
        tracking message. """
        if not self._track_get_fields():
            return
        body_values = self.env.cr.precommit.data.setdefault(f'mail.tracking.message.{self._name}', {})
        for id_ in self.ids:
            body_values[id_] = message

    def _track_get_default_log_message(self, tracked_fields):
        """Get a default log message based on the changed fields.

        :param List[str] tracked_fields: Name of the tracked fields being evaluated;

        :return str: A message to log when these changes happen for this record;
        """
        return ''

    @ormcache('self.env.uid', 'self.env.su')
    def _track_get_fields(self):
        """ Return the set of tracked fields names for the current model. """
        model_fields = {
            name
            for name, field in self._fields.items()
            if getattr(field, 'tracking', None)
        }

        return model_fields and set(self.fields_get(model_fields, attributes=()))

    def _track_subtype(self, initial_values):
        """ Give the subtypes triggered by the changes on the record according
        to values that have been updated.

        :param dict initial_values: original values of the record; only modified
          fields are present in the dict

        :returns: a subtype browse record or False if no subtype is triggered
        """
        self.ensure_one()
        return False

    def _message_track(self, fields_iter, initial_values_dict):
        """ Track updated values. Comparing the initial and current values of
        the fields given in tracked_fields, it generates a message containing
        the updated values. This message can be linked to a mail.message.subtype
        given by the ``_track_subtype`` method.

        :param iter fields_iter: iterable of field names to track
        :param dict initial_values_dict: mapping {record_id: initial_values}
          where initial_values is a dict {field_name: value, ... }
        :return: mapping {record_id: (changed_field_names, tracking_value_ids)}
            containing existing records only
        """
        if not fields_iter:
            return {}

        tracked_fields = self.fields_get(fields_iter, attributes=('string', 'type', 'selection', 'currency_field'))
        tracking = dict()
        for record in self:
            try:
                tracking[record.id] = record._mail_track(tracked_fields, initial_values_dict[record.id])
            except MissingError:
                continue

        # find content to log as body
        bodies = self.env.cr.precommit.data.pop(f'mail.tracking.message.{self._name}', {})
        authors = self.env.cr.precommit.data.pop(f'mail.tracking.author.{self._name}', {})
        for record in self:
            changes, tracking_value_ids = tracking.get(record.id, (None, None))
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtype = record._track_subtype(
                dict((col_name, initial_values_dict[record.id][col_name])
                     for col_name in changes)
            )
            author_id = authors[record.id].id if record.id in authors else None
            # _set_log_message takes priority over _track_get_default_log_message even if it's an empty string
            body = bodies[record.id] if record.id in bodies else record._track_get_default_log_message(changes)
            if subtype:
                if not subtype.exists():
                    _logger.debug('subtype "%s" not found' % subtype.name)
                    continue
                record.message_post(
                    body=body,
                    author_id=author_id,
                    subtype_id=subtype.id,
                    tracking_value_ids=tracking_value_ids
                )
            elif tracking_value_ids:
                record._message_log(
                    body=body,
                    author_id=author_id,
                    tracking_value_ids=tracking_value_ids
                )

        return tracking

    def _message_track_post_template(self, changes):
        """ Based on a tracking, post a message defined by ``_track_template``
        parameters. It allows to implement automatic post of messages based
        on templates (e.g. stage change triggering automatic email).

        :param dict changes: mapping {record_id: (changed_field_names, tracking_value_ids)}
            containing existing records only
        """
        if not self or not changes:
            return True
        # Clean the context to get rid of residual default_* keys
        # that could cause issues afterward during the mail.message
        # generation. Example: 'default_parent_id' would refer to
        # the parent_id of the current record that was used during
        # its creation, but could refer to wrong parent message id,
        # leading to a traceback in case the related message_id
        # doesn't exist
        cleaned_self = self.with_context(clean_context(self._context))._fallback_lang()
        try:
            templates = self._track_template(changes)
        except MissingError:
            if not self.exists():
                return
            raise

        default_composition_mode = 'mass_mail' if len(self) != 1 else 'comment'
        for (template, post_kwargs) in templates.values():
            if not template:
                continue

            composition_mode = post_kwargs.pop('composition_mode', default_composition_mode)
            post_kwargs.setdefault('message_type', 'auto_comment')
            if composition_mode == 'mass_mail':
                cleaned_self.message_mail_with_source(template, **post_kwargs)
            else:
                cleaned_self.message_post_with_source(template, **post_kwargs)
        return True

    def _track_template(self, changes):
        return dict()

    # ------------------------------------------------------
    # MAIL GATEWAY
    # ------------------------------------------------------

    def _routing_warn(self, error_message, message_id, route, raise_exception=True):
        """ Tools method used in _routing_check_route: whether to log a warning or raise an error """
        short_message = _("Mailbox unavailable - %s", error_message)
        full_message = ('Routing mail with Message-Id %s: route %s: %s' %
                        (message_id, route, error_message))
        _logger.info(full_message)
        if raise_exception:
            # sender should not see private diagnostics info, just the error
            raise ValueError(short_message)

    def _routing_create_bounce_email(self, email_from, body_html, message, **mail_values):
        bounce_to = decode_message_header(message, 'Return-Path') or email_from
        bounce_mail_values = {
            'author_id': False,
            'body_html': body_html,
            'subject': 'Re: %s' % message.get('subject'),
            'email_to': bounce_to,
            'auto_delete': True,
        }

        # find an email_from for the bounce email
        email_from = False
        if bounce_from := self.env.company.bounce_email:
            email_from = formataddr(('MAILER-DAEMON', bounce_from))
        if not email_from:
            catchall_aliases = self.env['mail.alias.domain'].search([]).mapped('catchall_email')
            if not any(catchall_email in message['To'] for catchall_email in catchall_aliases):
                email_from = decode_message_header(message, 'To')
        if not email_from:
            email_from = formataddr(('MAILER-DAEMON', self.env.user.email_normalized))

        bounce_mail_values['email_from'] = email_from
        bounce_mail_values.update(mail_values)
        self.env['mail.mail'].sudo().create(bounce_mail_values).send()

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
        bounced_msg_ids, bounced_message = message_dict['bounced_msg_ids'], message_dict['bounced_message']

        if bounced_email:
            bounced_model, bounced_res_id = bounced_message.model, bounced_message.res_id

            if bounced_model and bounced_model in self.env and bounced_res_id:
                bounced_record = self.env[bounced_model].sudo().browse(bounced_res_id).exists()

            bl_models = self.env['ir.model'].sudo().search(['&', ('is_mail_blacklist', '=', True), ('model', '!=', 'mail.thread.blacklist')])
            for model in [bl_model for bl_model in bl_models if bl_model.model in self.env]:  # transient test mode
                rec_bounce_w_email = self.env[model.model].sudo().search([('email_normalized', '=', bounced_email)])
                rec_bounce_w_email._message_receive_bounce(bounced_email, bounced_partner)
                bounced_record_done = bounced_record_done or (bounced_record and model.model == bounced_model and bounced_record in rec_bounce_w_email)

            # set record as bounced unless already done due to blacklist mixin
            if bounced_record and not bounced_record_done and isinstance(bounced_record, self.pool['mail.thread']):
                bounced_record._message_receive_bounce(bounced_email, bounced_partner)

            if bounced_partner and bounced_message:
                self.env['mail.notification'].sudo().search([
                    ('mail_message_id', '=', bounced_message.id),
                    ('res_partner_id', 'in', bounced_partner.ids)]
                ).write({
                    'failure_reason': html2plaintext(message_dict.get('body') or ''),
                    'failure_type': 'mail_bounce',
                    'notification_status': 'bounce',
                })

        if bounced_record:
            _logger.info('Routing mail from %s to %s with Message-Id %s: not routing bounce email from %s replying to %s (model %s ID %s)',
                         message_dict['email_from'], message_dict['to'], message_dict['message_id'], bounced_email, bounced_msg_ids, bounced_model, bounced_res_id)
        elif bounced_email:
            _logger.info('Routing mail from %s to %s with Message-Id %s: not routing bounce email from %s replying to %s (no document found)',
                         message_dict['email_from'], message_dict['to'], message_dict['message_id'], bounced_email, bounced_msg_ids)
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
            3 - if there is an alias, check alias_contact:
                'followers' and thread_id:
                    check on target document that the author is in the followers
                'followers' and alias_parent_thread_id:
                    check on alias parent document that the author is in the
                    followers
                'partners': check that author_id id set

        Note that this method also updates 'author_id' of message_dict as route
        links an incoming message to a record and linking email to partner is
        better done in a record's context.

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

        # Wrong model
        if not model:
            self._routing_warn(_('target model unspecified'), message_id, route, raise_exception)
            return ()
        if model not in self.env:
            self._routing_warn(_('unknown target model %s', model), message_id, route, raise_exception)
            return ()
        record_set = self.env[model].browse(thread_id) if thread_id else self.env[model]

        # Existing Document: check if exists and model accepts the mailgateway; if not, fallback on create if allowed
        if thread_id:
            if not record_set.exists():
                self._routing_warn(
                    _('reply to missing document (%(model)s,%(thread)s), fall back on document creation', model=model, thread=thread_id),
                    message_id,
                    route,
                    False
                )
                thread_id = None
            elif not hasattr(record_set, 'message_update'):
                self._routing_warn(_('reply to model %s that does not accept document update, fall back on document creation', model), message_id, route, False)
                thread_id = None

        # New Document: check model accepts the mailgateway
        if not thread_id and model and not hasattr(record_set, 'message_new'):
            self._routing_warn(_('model %s does not accept document creation', model), message_id, route, raise_exception)
            return ()

        # Update message author. We do it now because we need it for aliases (contact settings)
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
            error = obj._alias_get_error(message, message_dict, alias)
            if error:
                self._routing_warn(
                    _('alias %(name)s: %(error)s', name=alias.alias_name, error=error.message or _('unknown error')),
                    message_id,
                    route,
                    False
                )
                alias._alias_bounce_incoming_email(message, message_dict, set_invalid=error.is_config_error)
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
    def _detect_is_bounce(self, message, message_dict):
        """Return True if the given email is a bounce email.

        Bounce alias: if any To contains bounce_alias@domain
        Bounce message (not alias)
            See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
            As all MTA does not respect this RFC (googlemail is one of them),
            we also need to verify if the message come from "mailer-daemon"
        """
        # detection based on email_to
        bounce_aliases = self.env['mail.alias.domain'].search([]).mapped('bounce_email')
        email_to_list = [
            email_normalize(e) or e
            for e in email_split(message_dict['to'])
        ]
        if bounce_aliases and any(email in bounce_aliases for email in email_to_list):
            return True

        email_from = message_dict['email_from']
        email_from_localpart = (email_split(email_from) or [''])[0].split('@', 1)[0].lower()

        # detection based on email_from
        if email_from_localpart == 'mailer-daemon':
            return True

        # detection based on content type
        content_type = message.get_content_type()
        if content_type == 'multipart/report' or 'report-type=delivery-status' in content_type:
            return True

        return False

    @api.model
    def _detect_loop_sender_domain(self, email_from_normalized):
        """Return the domain to be used to detect duplicated records created by alias.

        :param email_from_normalized: FROM of the incoming email, normalized
        """
        primary_email = self._mail_get_primary_email_field()
        if primary_email:
            return [(primary_email, 'ilike', email_from_normalized)]

        _logger.info('Primary email missing on %s', self._name)

    @api.model
    def _detect_loop_sender(self, message, message_dict, routes):
        """This method returns True if the incoming email should be ignored.

        The goal of this method is to prevent loops which can occur if an auto-replier
        send emails to Odoo.
        """
        email_from = message_dict.get('email_from')
        if not email_from:
            return False

        email_from_normalized = email_normalize(email_from)

        if self.env['mail.gateway.allowed'].sudo().search_count(
           [('email_normalized', '=', email_from_normalized)]
        ):
            return False

        # Detect the email address sent to many emails
        get_param = self.env['ir.config_parameter'].sudo().get_param
        # Period in minutes in which we will look for <mail.mail>
        LOOP_MINUTES = int(get_param('mail.gateway.loop.minutes', 120))
        LOOP_THRESHOLD = int(get_param('mail.gateway.loop.threshold', 20))

        create_date_limit = self.env.cr.now() - datetime.timedelta(minutes=LOOP_MINUTES)
        author_id = message_dict.get('author_id')

        # Search only once per model
        model_res_ids = dict()
        for model, thread_id, *__ in routes or []:
            model_res_ids.setdefault(model, list()).append(thread_id)

        for model_name, thread_ids in model_res_ids.items():
            model = self.env[model_name]
            if not hasattr(model, '_detect_loop_sender_domain'):
                continue

            loop_new, loop_update = False, False
            search_new = 0 in thread_ids  # route creating new records = thread_id = 0
            doc_ids = list(filter(None, thread_ids))  # route updating records = thread_id set

            # search records created by email -> alias creating new records
            if search_new:
                base_domain = model._detect_loop_sender_domain(email_from_normalized)
                if base_domain:
                    mail_new_count = model.sudo().search_count(
                        expression.AND([
                            [('create_date', '>=', create_date_limit)],
                            base_domain,
                        ]),
                    )
                    loop_new = mail_new_count >= LOOP_THRESHOLD

            # search messages linked to email -> alias updating records
            if doc_ids and not loop_new:
                base_msg_domain = [('model', '=', model._name), ('res_id', 'in', doc_ids), ('create_date', '>=', create_date_limit)]
                if author_id:
                    msg_domain = expression.AND([[('author_id', '=', author_id)], base_msg_domain])
                else:
                    msg_domain = expression.AND([[('email_from', 'in', [email_from, email_from_normalized])], base_msg_domain])
                mail_update_groups = self.env['mail.message'].sudo()._read_group(msg_domain, ['res_id'], ['__count'])
                if mail_update_groups:
                    loop_update = any(
                        group[1] >= LOOP_THRESHOLD
                        for group in mail_update_groups
                    )

            if loop_new or loop_update:
                if loop_new:
                    _logger.info('--> ignored mail from %s to %s with Message-Id %s: created too many <%s>',
                                message_dict.get('email_from'), message_dict.get('to'), message_dict.get('message_id'), model)
                if loop_update:
                    _logger.info('--> ignored mail from %s to %s with Message-Id %s: too much replies on same <%s>',
                                message_dict.get('email_from'), message_dict.get('to'), message_dict.get('message_id'), model)
                body = self.env['ir.qweb']._render(
                    'mail.message_notification_limit_email',
                    {'email': message_dict.get('to')},
                    minimal_qcontext=True,
                    raise_if_not_found=False,
                )
                self._routing_create_bounce_email(
                    email_from, body, message,
                    # add a reference with a tag, to be able to ignore response to this email
                    references=f'{message_dict["message_id"]} {generate_tracking_message_id("loop-detection-bounce-email")}')
                return True

        return False

    @api.model
    def _detect_loop_headers(self, msg_dict):
        """Return True if the email must be ignored based on its headers."""
        references = unfold_references(msg_dict['references']) + [msg_dict['in_reply_to']]
        if references and any('-loop-detection-bounce-email@' in ref for ref in references):
            _logger.info('Email is a reply to the bounce notification, ignoring it.')
            return True

        return False

    @api.model
    def _detect_write_to_catchall(self, msg_dict):
        """Return True if directly contacts catchall."""
        # Note: tweaked in stable to avoid doing two times same search due to bugfix
        # (see odoo/odoo#161782), to clean when reaching master
        if self.env.context.get("mail_catchall_aliases"):
            catchall_aliases = self.env.context["mail_catchall_aliases"]
        else:
            catchall_aliases = self.env['mail.alias.domain'].search([]).mapped('catchall_email')

        email_to_list = [email_normalize(e) or e for e in email_split(msg_dict['to'])]
        # check it does not directly contact catchall; either (legacy) strict aka
        # all TOs belong are catchall, either (optional) any catchall in all TOs
        if self.env.context.get("mail_catchall_write_any_to"):
            return catchall_aliases and any(email_to in catchall_aliases for email_to in email_to_list)
        return (
            catchall_aliases and email_to_list and
            all(email_to in catchall_aliases for email_to in email_to_list)
        )

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
        if not isinstance(message, EmailMessage):
            raise TypeError('message must be an email.message.EmailMessage at this point')
        catchall_domains_allowed = list(filter(None, (self.env["ir.config_parameter"].sudo().get_param(
            "mail.catchall.domain.allowed") or '').split(',')))
        if catchall_domains_allowed:
            catchall_domains_allowed += self.env['mail.alias.domain'].search([]).mapped('name')

        def _filter_excluded_local_part(email):
            left, _at, domain = email.partition('@')
            if not domain:
                return False
            if catchall_domains_allowed and domain not in catchall_domains_allowed:
                return False
            return left

        fallback_model = model

        # handle bounce: verify whether this is a bounced email and use it to
        # collect bounce data and update notifications for customers
        if message_dict.get('is_bounce'):
            self._routing_handle_bounce(message, message_dict)
            return []
        self._routing_reset_bounce(message, message_dict)

        # get email.message.Message variables for future processing
        message_id = message_dict['message_id']

        # compute references to find if message is a reply to an existing thread
        thread_references = message_dict['references'] or message_dict['in_reply_to']
        msg_references = [r.strip() for r in unfold_references(thread_references) if 'reply_to' not in r]
        # avoid creating a gigantic query by limiting the number of references taken into account.
        # newer msg_ids are *appended* to References as per RFC5322 §3.6.4, so we should generally
        # find a match just with the last entry (equal to `In-Reply-To`). 32 refs seems large enough,
        # we've seen performance degrade with 100+ refs.
        msg_references = msg_references[-32:]
        replying_to_msg = self.env['mail.message'].sudo().search(
            [('message_id', 'in', msg_references)], limit=1, order='id desc'
        ) if msg_references else self.env['mail.message']
        is_a_reply, reply_model, reply_thread_id = bool(replying_to_msg), replying_to_msg.model, replying_to_msg.res_id

        # author and recipients
        email_from = message_dict['email_from']
        email_to_list = [e.lower() for e in email_split(message_dict['to'])]
        email_to_localparts = list(filter(None, (_filter_excluded_local_part(email_to) for email_to in email_to_list)))
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos_list = [e.lower() for e in email_split(message_dict['recipients'])]
        rcpt_tos_localparts = list(filter(None, (_filter_excluded_local_part(email_to) for email_to in rcpt_tos_list)))
        rcpt_tos_valid_list = list(rcpt_tos_list)

        # 1. Handle reply
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        if reply_model and reply_thread_id:
            reply_model_id = self.env['ir.model']._get_id(reply_model)
            other_model_aliases = self.env['mail.alias'].search([
                '&',
                ('alias_model_id', '!=', reply_model_id),
                '|',
                ('alias_full_name', 'in', email_to_list),
                '&', ('alias_name', 'in', email_to_localparts), ('alias_incoming_local', '=', True),
            ])
            if other_model_aliases:
                is_a_reply, reply_model, reply_thread_id = False, False, False
                rcpt_tos_valid_list = [
                    to
                    for to in rcpt_tos_valid_list
                    if (
                        to in other_model_aliases.mapped('alias_full_name')
                        or to.split('@', 1)[0] in other_model_aliases.filtered('alias_incoming_local').mapped('alias_name')
                    )
                ]
        rcpt_tos_valid_localparts = list(filter(None, (_filter_excluded_local_part(email_to) for email_to in rcpt_tos_valid_list)))

        if is_a_reply and reply_model:
            reply_model_id = self.env['ir.model']._get_id(reply_model)
            dest_aliases = self.env['mail.alias'].search([
                '&',
                ('alias_model_id', '=', reply_model_id),
                '|',
                ('alias_full_name', 'in', rcpt_tos_list),
                '&', ('alias_name', 'in', rcpt_tos_localparts), ('alias_incoming_local', '=', True),
            ], limit=1)

            user_id = self._mail_find_user_for_gateway(email_from, alias=dest_aliases).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (reply_model, reply_thread_id, custom_values, user_id, dest_aliases),
                raise_exception=False)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, message_dict['to'], message_id, reply_model, reply_thread_id, custom_values, self._uid)
                return [route]
            if route is False:
                return []

        # 2. Handle new incoming email by checking aliases and applying their settings
        # prefetch catchall aliases as they are used several times
        catchall_aliases = self.env['mail.alias.domain'].search([]).mapped('catchall_email')
        self = self.with_context(mail_catchall_aliases=catchall_aliases)
        if rcpt_tos_list:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if self._detect_write_to_catchall(message_dict):
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce',
                             email_from, message_dict['to'], message_id)
                body = self.env['ir.qweb']._render('mail.mail_bounce_catchall', {
                    'message': message,
                })
                self._routing_create_bounce_email(
                    email_from, body, message,
                    # add a reference with a tag, to be able to ignore response to this email
                    references=f'{message_id} {generate_tracking_message_id("loop-detection-bounce-email")}',
                    reply_to=self.env.company.email)
                return []

            dest_aliases = self.env['mail.alias'].search([
                '|',
                ('alias_full_name', 'in', rcpt_tos_valid_list),
                '&', ('alias_name', 'in', rcpt_tos_valid_localparts), ('alias_incoming_local', '=', True),
            ])
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = self._mail_find_user_for_gateway(email_from, alias=alias).id or self._uid
                    route = (alias.sudo().alias_model_id.model, alias.alias_force_thread_id, ast.literal_eval(alias.alias_defaults), user_id, alias)
                    AliasModel = self.env[route[0]] if route[0] in self.env and hasattr(self.env[route[0]], '_routing_check_route') else self
                    route = AliasModel._routing_check_route(message, message_dict, route, raise_exception=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, message_dict['to'], message_id, route)
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
                    email_from, message_dict['to'], message_id, fallback_model, thread_id, custom_values, user_id)
                return [route]

        # 4. Recipients contain catchall and unroutable emails -> bounce
        if rcpt_tos_list and self.with_context(mail_catchall_write_any_to=True)._detect_write_to_catchall(message_dict):
            _logger.info(
                'Routing mail from %s to %s with Message-Id %s: write to catchall + other unroutable emails, bounce',
                email_from, message_dict['to'], message_id
            )
            body = self.env['ir.qweb']._render('mail.mail_bounce_catchall', {
                'message': message,
            })
            self._routing_create_bounce_email(
                email_from, body, message,
                # add a reference with a tag, to be able to ignore response to this email
                references=f'{message_id} {generate_tracking_message_id("loop-detection-bounce-email")}',
                reply_to=self.env.company.email)
            return []

        # ValueError if no routes found and if no bounce occurred
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, message_dict['to'], message_id)
        )

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        self = self.with_context(attachments_mime_plainxml=True) # import XML attachments as text
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        original_partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes or ():
            subtype_id = False
            related_user = self.env['res.users'].browse(user_id)
            Model = self.env[model].with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
            if not (thread_id and hasattr(Model, 'message_update') or hasattr(Model, 'message_new')):
                raise ValueError(
                    "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" %
                    (message_dict['message_id'], model)
                )

            # disabled subscriptions during message_new/update to avoid having the system user running the
            # email gateway become a follower of all inbound messages
            ModelCtx = Model.with_user(related_user).sudo()
            if thread_id and hasattr(ModelCtx, 'message_update'):
                thread = ModelCtx.browse(thread_id)
                thread.message_update(message_dict)
            else:
                # if a new thread is created, parent is irrelevant
                message_dict.pop('parent_id', None)
                # Report failure/record success of message creation except if alias is not defined (fallback model case)
                try:
                    thread = ModelCtx.message_new(message_dict, custom_values)
                except Exception:
                    if alias:
                        with self.pool.cursor() as new_cr:
                            self.with_env(self.env(cr=new_cr)).env['mail.alias'].browse(alias.id
                            )._alias_bounce_incoming_email(message, message_dict, set_invalid=True)
                    raise
                else:
                    if alias and alias.alias_status != 'valid':
                        alias.alias_status = 'valid'
                thread_id = thread.id
                subtype_id = thread._creation_subtype().id

            # switch to odoobot for all incoming message creation
            # to have a high-privilege archived user so real_author_id is correctly computed
            thread_root = thread.with_user(self.env.ref('base.user_root'))
            # replies to internal message are considered as notes, but parent message
            # author is added in recipients to ensure they are notified of a private answer
            parent_message = False
            if message_dict.get('parent_id'):
                parent_message = self.env['mail.message'].sudo().browse(message_dict['parent_id'])
            partner_ids = []
            if not subtype_id:
                if message_dict.get('is_internal'):
                    subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
                    if parent_message and parent_message.author_id:
                        partner_ids = [parent_message.author_id.id]
                else:
                    subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

            post_params = dict(subtype_id=subtype_id, partner_ids=partner_ids, **message_dict)
            # remove computational values not stored on mail.message and avoid warnings when creating it
            for x in ('from', 'to', 'cc', 'recipients', 'references', 'in_reply_to', 'x_odoo_message_id',
                      'is_bounce', 'bounced_email', 'bounced_message', 'bounced_msg_ids', 'bounced_partner'):
                post_params.pop(x, None)
            new_msg = False
            if thread_root._name == 'mail.thread':  # message with parent_id not linked to record
                new_msg = thread_root.message_notify(**post_params)
            else:
                # if no author, skip any author subscribe check; otherwise message_post
                # checks anyway for real author and filters inactive (like odoobot)
                thread_root = thread_root.with_context(from_alias=True, mail_create_nosubscribe=not message_dict.get('author_id'))
                new_msg = thread_root.message_post(**post_params)

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
        message = email.message_from_bytes(message, policy=email.policy.SMTP)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg_dict = self.message_parse(message, save_original=save_original)
        if strip_attachments:
            msg_dict.pop('attachments', None)

        message_ids = [msg_dict['message_id']]
        if msg_dict.get('x_odoo_message_id'):
            message_ids.append(msg_dict['x_odoo_message_id'])
        existing_msg_ids = self.env['mail.message'].search([('message_id', 'in', message_ids)], limit=1)
        if existing_msg_ids:
            if msg_dict.get('x_odoo_message_id'):
                _logger.info('Ignored mail from %s to %s with Message-Id %s / Context Message-Id %s: found duplicated Message-Id during processing',
                             msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'), msg_dict.get('x_odoo_message_id'))
            else:
                _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                             msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return False

        if self._detect_loop_headers(msg_dict):
            _logger.info('Ignored mail from %s to %s with Message-Id %s: reply to a bounce notification detected by headers',
                             msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return

        # find possible routes for the message; note this also updates notably
        # 'author_id' of msg_dict
        routes = self.message_route(message, msg_dict, model, thread_id, custom_values)
        if self._detect_loop_sender(message, msg_dict, routes):
            return

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
        model_fields = self.fields_get()
        name_field = self._rec_name or 'name'
        if name_field in model_fields and not data.get(name_field):
            data[name_field] = msg_dict.get('subject', '')

        primary_email = self._mail_get_primary_email_field()
        if primary_email and msg_dict.get('email_from'):
            data[primary_email] = msg_dict['email_from']

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
        located in mail.

        :param string message: an email.message instance
        """
        body, attachments = payload_dict['body'], payload_dict['attachments']
        if not body.strip():
            return {'body': body, 'attachments': attachments}
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
            body = Markup(etree.tostring(root, pretty_print=False, encoding='unicode'))
        return {'body': body, 'attachments': attachments}

    def _message_parse_extract_payload(self, message: EmailMessage, message_dict: dict, save_original: bool = False):
        """Extract body as HTML and attachments from the mail message
        """
        attachments = []
        body = ''
        if save_original:
            attachments.append(self._Attachment('original_email.eml', message.as_string(), {}))

        # Be careful, content-type may contain tricky content like in the
        # following example so test the MIME type with startswith()
        #
        # Content-Type: multipart/related;
        #   boundary="_004_3f1e4da175f349248b8d43cdeb9866f1AMSPR06MB343eurprd06pro_";
        #   type="text/html"
        if message.get_content_maintype() == 'text':
            body = message.get_content()
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = append_content_to_html('', body, preserve=True)
            elif message.get_content_type() == 'text/html':
                # we only strip_classes here everything else will be done in by html field of mail.message
                body = html_sanitize(body, sanitize_tags=False, strip_classes=True)
        else:
            alternative = False
            mixed = False
            html = False
            for part in message.walk():
                if message_dict.get('is_bounce') and body:
                    # bounce email, keep only the first body and ignore
                    # the parent email that might be added at the end
                    # (e.g. for outlook / yahoo bounce email)
                    break
                if part.get_content_type() == 'binary/octet-stream':
                    _logger.warning("Message containing an unexpected Content-Type 'binary/octet-stream', assuming 'application/octet-stream'")
                    part.replace_header('Content-Type', 'application/octet-stream')
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_type() == 'multipart/mixed':
                    mixed = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container

                filename = part.get_filename()  # I may not properly handle all charsets
                if part.get_content_type().startswith('text/') and not part.get_param('charset'):
                    # for text/* with omitted charset, the charset is assumed to be ASCII by the `email` module
                    # although the payload might be in UTF8
                    part.set_charset('utf-8')
                encoding = part.get_content_charset()  # None if attachment

                # Correcting MIME type for PDF files
                if part.get('Content-Type', '').startswith('pdf;'):
                    part.replace_header('Content-Type', 'application/pdf' + part.get('Content-Type', '')[3:])

                content = part.get_content()
                info = {'encoding': encoding}
                # 0) Inline Attachments -> attachments, with a third part in the tuple to match cid / attachment
                if filename and part.get('content-id'):
                    info['cid'] = part.get('content-id').strip('><')
                    attachments.append(self._Attachment(filename, content, info))
                    continue
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    attachments.append(self._Attachment(filename or 'attachment', content, info))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and not (alternative and body):
                    body = append_content_to_html(body, content, preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    # multipart/alternative have one text and a html part, keep only the second
                    if alternative and not (html and mixed):
                        body = content
                    else:
                        # mixed allows several html parts, append html content
                        body = append_content_to_html(body, content, plaintext=False)
                    # TODO: maybe just setting to `True` is enough?
                    html = html or bool(content)
                    # we only strip_classes here everything else will be done in by html field of mail.message
                    body = html_sanitize(body, sanitize_tags=False, strip_classes=True)
                # 4) Anything else -> attachment
                else:
                    attachments.append(self._Attachment(filename or 'attachment', content, info))

        return self._message_parse_extract_payload_postprocess(message, {'body': body, 'attachments': attachments})

    def _message_parse_extract_bounce(self, email_message, message_dict):
        """ Parse email and extract bounce information to be used in future
        processing.

        :param email_message: an email.message instance;
        :param message_dict: dictionary holding already-parsed values;

        :return dict: bounce-related values will be added, containing

          * is_bounce: whether the email is recognized as a bounce email;
          * bounced_email: email that bounced (normalized);
          * bounce_partner: res.partner recordset whose email_normalized =
            bounced_email;
          * bounced_msg_ids: list of message_ID references (<...@myserver>) linked
            to the email that bounced;
          * bounced_message: if found, mail.message recordset matching bounced_msg_ids;
        """
        if not isinstance(email_message, EmailMessage):
            raise TypeError('message must be an email.message.EmailMessage at this point')

        is_bounce = self._detect_is_bounce(email_message, message_dict)
        if not is_bounce:
            return {'is_bounce': False}

        email_part = next((part for part in email_message.walk() if part.get_content_type() in {'message/rfc822', 'text/rfc822-headers'}), None)
        if not email_part:
            # In the case of a bounce message (e.g. bounce message of GMX), the "rfc822"
            # email part might not be always present. In that case we fallback to "multipart/report".
            email_part = next(
                (part for part in email_message.walk() if part.get_content_type() == 'multipart/report'),
                None,
            )

        dsn_part = next((part for part in email_message.walk() if part.get_content_type() == 'message/delivery-status'), None)

        bounced_email = False
        bounced_partner = self.env['res.partner'].sudo()
        if dsn_part and len(dsn_part.get_payload()) > 1:
            dsn = dsn_part.get_payload()[1]
            final_recipient_data = decode_message_header(dsn, 'Final-Recipient')
            # old servers may hold void or invalid Final-Recipient header
            if final_recipient_data and ";" in final_recipient_data:
                bounced_email = email_normalize(final_recipient_data.split(';', 1)[1].strip())
            if bounced_email:
                bounced_partner = self.env['res.partner'].sudo().search([('email_normalized', '=', bounced_email)])

        bounced_msg_ids = False
        bounced_message = self.env['mail.message'].sudo()
        if email_part:
            if email_part.get_content_type() == 'text/rfc822-headers':
                # Convert the message body into a message itself
                email_payload = message_from_string(email_part.get_content(), policy=email.policy.SMTP)
            else:
                email_payload = email_part.get_payload()[0]
            bounced_message, bounced_msg_ids = self._get_bounced_message_data(email_payload, message_dict)

        if bounced_message and not bounced_partner and len(bounced_message.notification_ids.res_partner_id) == 1:
            # if the original recipient was not found,
            # try to find the recipient based on parent <mail.message> notification
            bounced_partner = bounced_message.notification_ids.res_partner_id[0]
            bounced_email = bounced_partner.email

        return {
            'bounced_email': bounced_email,
            'bounced_partner': bounced_partner,
            'bounced_msg_ids': bounced_msg_ids,
            'bounced_message': bounced_message,
            'is_bounce': True,
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
              'is_bounce': True if it has been detected as a bounce email
              'parent_id': parent mail.message based on in_reply_to or references,
              'is_internal': answer to an internal message (note),
              'date': date,
              'attachments': [('file1', 'bytes'),
                              ('file2', 'bytes')}
            }
        """
        if not isinstance(message, EmailMessage):
            raise ValueError(_('Message should be a valid EmailMessage instance'))
        msg_dict = {'message_type': 'email'}

        message_id = message.get('Message-Id')
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['x_odoo_message_id'] = (message.get('X-Odoo-Message-Id') or '').strip()
        msg_dict['message_id'] = message_id.strip()

        if message.get('Subject'):
            msg_dict['subject'] = decode_message_header(message, 'Subject')

        email_from = decode_message_header(message, 'From', separator=',')
        email_cc = decode_message_header(message, 'cc', separator=',')
        email_from_list = email_split_and_format(email_from)
        email_cc_list = email_split_and_format(email_cc)
        msg_dict['email_from'] = email_from_list[0] if email_from_list else email_from
        msg_dict['from'] = msg_dict['email_from']  # compatibility for message_new
        msg_dict['cc'] = ','.join(email_cc_list) if email_cc_list else email_cc
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        msg_dict['recipients'] = ','.join(set(formatted_email
            for address in [
                decode_message_header(message, 'Delivered-To', separator=','),
                decode_message_header(message, 'To', separator=','),
                decode_message_header(message, 'Cc', separator=','),
                decode_message_header(message, 'Resent-To', separator=','),
                decode_message_header(message, 'Resent-Cc', separator=',')
            ] if address
            for formatted_email in email_split_and_format(address))
        )
        msg_dict['to'] = ','.join(set(formatted_email
            for address in [
                decode_message_header(message, 'Delivered-To', separator=','),
                decode_message_header(message, 'To', separator=',')
            ] if address
            for formatted_email in email_split_and_format(address))
        )
        partner_ids = [x.id for x in self._mail_find_partner_from_emails(email_split(msg_dict['recipients']), records=self) if x]
        msg_dict['partner_ids'] = partner_ids
        # compute references to find if email_message is a reply to an existing thread
        msg_dict['references'] = decode_message_header(message, 'References')
        msg_dict['in_reply_to'] = decode_message_header(message, 'In-Reply-To').strip()

        if message.get('Date'):
            try:
                date_hdr = decode_message_header(message, 'Date')
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
            msg_dict['date'] = fields.Datetime.to_string(stored_date)

        msg_dict.update(self._message_parse_extract_from_parent(self._get_parent_message(msg_dict)))
        msg_dict.update(self._message_parse_extract_bounce(message, msg_dict))
        msg_dict.update(self._message_parse_extract_payload(message, msg_dict, save_original=save_original))
        return msg_dict

    def _message_parse_extract_from_parent(self, parent_message):
        """Derive message values from the parent."""
        if parent_message:
            parent_is_internal = bool(parent_message.subtype_id and parent_message.subtype_id.internal)
            parent_is_auto_comment = parent_message.message_type == 'auto_comment'
            return {
                'parent_id': parent_message.id,
                'is_internal': parent_is_internal and not parent_is_auto_comment
            }
        return {}

    def _get_bounced_message_data(self, message, message_dict):
        """Find the original <mail.message> and the bounced email references based on an incoming email.

        :param message: The EmailMessage object, part of the incoming email
                First Content type: 'message/rfc822' or 'text/rfc822-headers'
        :param message_dict: The dict values already parsed
        :return:
            A tuple with
            - The <mail.message> (or empty recordset if nothing has been found)
            - The list of references ids used to find the bounced mail message
        """
        reference_ids = []
        headers = ('Message-Id', 'X-Odoo-Message-Id', 'X-Microsoft-Original-Message-ID')
        for header in headers:
            value = decode_message_header(message, header)
            references = unfold_references(value)
            reference_ids.extend([reference.strip() for reference in references])

        if reference_ids:
            bounced_message = self.env['mail.message'].search(
                [('message_id', 'in', reference_ids)],
                order='create_date DESC, id DESC', limit=1)

            if bounced_message:
                return bounced_message, reference_ids

        reference_ids.extend(unfold_references(message_dict['in_reply_to']))
        reference_ids.extend([r.strip() for r in unfold_references(message_dict['references'])])

        if message_dict.get('parent_id'):
            # Parent based on References, In-Reply-To, etc
            # has already been searched (see @_get_parent_message)
            bounced_message = self.env['mail.message'].browse(message_dict['parent_id'])
            return bounced_message, reference_ids

        return self.env['mail.message'], reference_ids

    def _get_parent_message(self, msg_dict):
        """Find the <mail.message> which is the parent of the given email.

        :param msg_dict: The dict values already parsed
        :return: The <mail.message> or None if nothing has been found
        """
        in_reply_to = msg_dict['in_reply_to']
        if in_reply_to:
            parent = self.env['mail.message'].search(
                [('message_id', '=', in_reply_to)],
                order='id DESC', limit=1)
            if parent:
                return parent

        msg_references = [r.strip() for r in unfold_references(msg_dict['references'])]
        if msg_references:
            # avoid creating a gigantic query by limiting the number of references taken into account.
            # newer msg_ids are *appended* to References as per RFC5322 §3.6.4, so we should generally
            # find a match just with the last entry (equal to `In-Reply-To`). 32 refs seems large enough,
            # we've seen performance degrade with 100+ refs.
            msg_references = msg_references[-32:]
            parent = self.env['mail.message'].search(
                [('message_id', 'in', msg_references)],
                order='id DESC', limit=1)
            if parent:
                return parent

        return None

    # ------------------------------------------------------
    # RECIPIENTS MANAGEMENT TOOLS
    # ------------------------------------------------------

    def _message_add_suggested_recipient(self, result, partner=None, email=None, lang=None, reason=''):
        """ Called by _message_get_suggested_recipients, to add a suggested
            recipient as a dictionary in the result list """
        self.ensure_one()
        partner_info = {}
        recipient_data = {'lang': lang, 'reason': reason}
        if email and not partner:
            # get partner info from email
            partner_info = self._message_partner_info_from_emails([email])[0]
            if partner_info.get('partner_id'):
                partner = self.env['res.partner'].sudo().browse([partner_info['partner_id']])[0]
        if email and email in [val['email'] for val in result if val.get('email')]:  # already existing email -> skip
            return result
        if partner and partner in self.message_partner_ids:  # recipient already in the followers -> skip
            return result
        if partner and partner.id in [val.get('partner_id', False) for val in result]:  # already existing partner ID -> skip
            return result
        if partner and partner.email:  # complete profile: id, name <email>
            email_normalized = ','.join(email_normalize_all(partner.email))
            recipient_data.update({'partner_id': partner.id, 'name': partner.name or '', 'email': email_normalized})
        elif partner:  # incomplete profile: id, name
            recipient_data.update({'partner_id': partner.id, 'name': partner.name})
        else:  # unknown partner, we are probably managing an email address
            _, parsed_email_normalized = parse_contact_from_email(email)
            partner_create_values = self._get_customer_information().get(parsed_email_normalized, {})
            name = partner_create_values.get('name') or partner_info.get('full_name') or email
            recipient_data.update({
                'name': name,
                'email': partner_info.get('full_name') or email,
                'create_values': partner_create_values,
            })
        result.append(recipient_data)
        return result

    def _message_get_suggested_recipients(self):
        """ Get suggested recipients to be managed by Chatter

        :returns: list of dictionaries (per suggested recipient) containing:
            * partner_id:       int: recipient partner id
            * name:             str: name of the recipient
            * email:            str: email of recipient
            * lang:             str: language code
            * reason:           str
            * create_values:    dict: data for unknown partner
        """
        self.ensure_one()
        result = []
        user_field = self._fields.get('user_id')
        if user_field and user_field.type == 'many2one' and user_field.comodel_name == 'res.users':
            thread = self.sudo()  # SUPERUSER because of a read on res.users that would crash otherwise
            if thread.user_id and thread.user_id.partner_id:
                thread._message_add_suggested_recipient(
                    result,
                    partner=thread.user_id.partner_id,
                    reason=self._fields['user_id'].string,
                )
        return result

    def _mail_search_on_user(self, normalized_emails, extra_domain=False):
        """ Find partners linked to users, given an email address that will
        be normalized. Search is done as sudo on res.users model to avoid domain
        on partner like ('user_ids', '!=', False) that would not be efficient. """
        domain = [('email_normalized', 'in', normalized_emails)]
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        partners = self.env['res.users'].sudo().search(domain).mapped('partner_id')
        # return a search on partner to filter results current user should not see (multi company for example)
        return self.env['res.partner'].search([('id', 'in', partners.ids)])

    def _mail_search_on_partner(self, normalized_emails, extra_domain=False):
        domain = [('email_normalized', 'in', normalized_emails)]
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return self.env['res.partner'].search(domain)

    def _mail_find_user_for_gateway(self, email_value, alias=None):
        """ Utility method to find user from email address that can create documents
        in the target model. Purpose is to link document creation to users whenever
        possible, for example when creating document through mailgateway.

        Heuristic

          * alias owner record: fetch in its followers for user with matching email;
          * find any user with matching emails;
          * try alias owner as fallback;

        Note that standard search order is applied.

        :param str email_value: will be sanitized and parsed to find email;
        :param mail.alias alias: optional alias. Used to fetch owner followers
          or fallback user (alias owner);

        :return res.user user: user matching email or void recordset if none found
        """
        # find normalized emails and exclude aliases (to avoid subscribing alias emails to records)
        normalized_email = email_normalize(email_value)
        if not normalized_email:
            return self.env['res.users']

        if self.env['mail.alias'].sudo().search_count([('alias_full_name', '=', email_value)]):
            return self.env['res.users']

        if alias and alias.alias_parent_model_id and alias.alias_parent_thread_id:
            followers = self.env['mail.followers'].search([
                ('res_model', '=', alias.alias_parent_model_id.sudo().model),
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
            std_users = self.env['res.users'].sudo().search([('email_normalized', '=', normalized_email)], limit=1)
            matching_user = std_users[0] if std_users else self.env['res.users']

        return matching_user

    @api.model
    def _mail_find_partner_from_emails(self, emails, records=None, force_create=False, extra_domain=False):
        """ Utility method to find partners from email addresses. If no partner is
        found, create new partners if force_create is enabled. Search heuristics

          * 0: clean incoming email list to use only normalized emails. Exclude
               those used in aliases to avoid setting partner emails to emails
               used as aliases;
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
        if records and isinstance(records, self.pool['mail.thread']):
            followers = records.mapped('message_partner_ids')
        else:
            followers = self.env['res.partner']

        # first, build a normalized email list and remove those linked to aliases
        # to avoid adding aliases as partners. In case of multi-email input, use
        # the first found valid one to be tolerant against multi emails encoding
        normalized_emails = [email_normalized
                             for email_normalized in (email_normalize(contact, strict=False) for contact in emails)
                             if email_normalized
                            ]
        matching_aliases = self.env['mail.alias'].sudo().search([('alias_full_name', 'in', normalized_emails)])
        if matching_aliases:
            normalized_emails = [email for email in normalized_emails if email not in matching_aliases.mapped('alias_full_name')]

        done_partners = [follower for follower in followers if follower.email_normalized in normalized_emails]
        remaining = [email for email in normalized_emails if email not in [partner.email_normalized for partner in done_partners]]

        user_partners = self._mail_search_on_user(remaining, extra_domain=extra_domain)
        done_partners += [user_partner for user_partner in user_partners]
        remaining = [email for email in normalized_emails if email not in [partner.email_normalized for partner in done_partners]]

        partners = self._mail_search_on_partner(remaining, extra_domain=extra_domain)
        done_partners += [partner for partner in partners]

        # prioritize current user if exists in list, and partners with matching company ids
        if company_fname := records and records._mail_get_company_field():
            def sort_key(p):
                return (
                    self.env.user.partner_id == p,           # prioritize user
                    p.company_id in records[company_fname],  # then partner associated w/ records
                    not p.company_id,                        # else pick partner w/out company_id
                )
        else:
            def sort_key(p):
                return (self.env.user.partner_id == p, not p.company_id)

        done_partners.sort(key=sort_key, reverse=True)  # reverse because False < True

        # iterate and keep ordering
        partners = []
        for contact in emails:
            normalized_email = email_normalize(contact, strict=False)
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

    def _get_customer_information(self):
        """ Get customer information that can be extracted from the records by
        normalized email.

        The goal of this method is to offer an extension point to subclasses
        for retrieving initial values from a record to populate related
        customers record (res_partner).

        :return dict: normalized email -> dict of initial res_partner values
        """
        return {}

    # ------------------------------------------------------------
    # MESSAGE POST MAIN
    # ------------------------------------------------------------

    def message_post(self, *,
                     body='', subject=None, message_type='notification',
                     email_from=None, author_id=None, parent_id=False,
                     subtype_xmlid=None, subtype_id=False, partner_ids=None,
                     attachments=None, attachment_ids=None, body_is_html=False,
                     **kwargs):
        """ Post a new message in an existing thread, returning the new mail.message.

        :param str|Markup body: body of the message, str content will be escaped, Markup
            for html body
        :param str subject: subject of the message
        :param str message_type: see mail_message.message_type field. Can be anything but
            user_notification, reserved for message_notify
        :param str email_from: from address of the author. See ``_message_compute_author``
            that uses it to make email_from / author_id coherent;
        :param int author_id: optional ID of partner record being the author. See
            ``_message_compute_author`` that uses it to make email_from / author_id coherent;
        :param int parent_id: handle thread formation
        :param str subtype_xmlid: optional xml id of a mail.message.subtype to
          fetch, will force value of subtype_id;
        :param int subtype_id: subtype_id of the message, used mainly for followers
            notification mechanism;
        :param list(int) partner_ids: partner_ids to notify in addition to partners
            computed based on subtype / followers matching;
        :param list(tuple(str,str), tuple(str,str, dict)) attachments : list of attachment
            tuples in the form ``(name,content)`` or ``(name,content, info)`` where content
            is NOT base64 encoded;
        :param list attachment_ids: list of existing attachments to link to this message
            Should not be a list of commands. Attachment records attached to mail
            composer will be attached to the related document.
        :param bool body_is_html: indicates body should be threated as HTML even if str
            to be used only for RPC calls

        Extra keyword arguments will be used either
          * as default column values for the new mail.message record if they match
            mail.message fields;
          * propagated to notification methods if not;

        :return record: newly create mail.message
        """
        self.ensure_one()  # should always be posted on a record, use message_notify if no record

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            forbidden_names={'model', 'res_id', 'subtype'}
        )
        if self._name == 'mail.thread' or not self.id:
            raise ValueError(_("Posting a message should be done on a business document. Use message_notify to send a notification to an user."))
        if message_type == 'user_notification':
            raise ValueError(_("Use message_notify to send a notification to an user."))
        if attachments:
            # attachments should be a list (or tuples) of 3-elements list (or tuple)
            format_error = not is_list_of(attachments, list) and not is_list_of(attachments, tuple)
            if not format_error:
                format_error = not all(len(attachment) in {2, 3} for attachment in attachments)
            if format_error:
                raise ValueError(
                    _('Posting a message should receive attachments as a list of list or tuples (received %(aids)s)',
                      aids=repr(attachment_ids),
                     )
                )
        if attachment_ids and not is_list_of(attachment_ids, int):
            raise ValueError(
                _('Posting a message should receive attachments records as a list of IDs (received %(aids)s)',
                  aids=repr(attachment_ids),
                 )
            )
        attachment_ids = list(attachment_ids or [])
        if partner_ids and not is_list_of(partner_ids, int):
            raise ValueError(
                _('Posting a message should receive partners as a list of IDs (received %(pids)s)',
                  pids=repr(partner_ids),
                 )
            )
        partner_ids = list(partner_ids or [])

        # split message additional values from notify additional values
        msg_kwargs = {key: val for key, val in kwargs.items()
                      if key in self.env['mail.message']._fields}
        notif_kwargs = {key: val for key, val in kwargs.items()
                        if key not in msg_kwargs}

        # Add lang to context immediately since it will be useful in various flows later
        self = self._fallback_lang()

        # Find the message's author
        guest = self.env['mail.guest']._get_guest_from_context()
        if not author_id and self.env.user._is_public() and guest:
            author_guest_id = guest.id
            author_id, email_from = False, False
        else:
            author_guest_id = False
            author_id, email_from = self._message_compute_author(author_id, email_from, raise_on_email=True)

        if subtype_xmlid:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        # automatically subscribe recipients if asked to
        if self._context.get('mail_post_autofollow') and partner_ids:
            self.message_subscribe(partner_ids=list(partner_ids))

        msg_values = dict(msg_kwargs)
        if 'email_add_signature' not in msg_values:
            msg_values['email_add_signature'] = True
        if not msg_values.get('record_name'):
            # use sudo as record access is not always granted (notably when replying
            # a notification) -> final check is done at message creation level
            msg_values['record_name'] = self.sudo().display_name
        if body_is_html and self.env.user._is_internal():
            _logger.warning("Posting HTML message using body_is_html=True, use a Markup object instead (user: %s)",
                self.env.user.id)
            body = Markup(body)
        msg_values.update({
            # author
            'author_id': author_id,
            'author_guest_id': author_guest_id,
            'email_from': email_from,
            # document
            'model': self._name,
            'res_id': self.id,
            # content
            'body': escape(body),  # escape if text, keep if markup
            'message_type': message_type,
            'parent_id': self._message_compute_parent_id(parent_id),
            'subject': subject or False,
            'subtype_id': subtype_id,
            # recipients
            'partner_ids': partner_ids,
        })
        # add default-like values afterwards, to avoid useless queries
        if 'record_alias_domain_id' not in msg_values:
            msg_values['record_alias_domain_id'] = self.sudo()._mail_get_alias_domains(default_company=self.env.company)[self.id].id
        if 'record_company_id' not in msg_values:
            msg_values['record_company_id'] = self._mail_get_companies(default=self.env.company)[self.id].id
        if 'reply_to' not in msg_values:
            msg_values['reply_to'] = self._notify_get_reply_to(default=email_from)[self.id]

        msg_values.update(
            self._process_attachments_for_post(attachments, attachment_ids, msg_values)
        )  # attachement_ids, body
        new_message = self._message_create([msg_values])

        # subscribe author(s) so that they receive answers; do it only when it is
        # a manual post by the author (aka not a system notification, not a message
        # posted 'in behalf of', and if still active).
        author_subscribe = (not self._context.get('mail_create_nosubscribe') and
                             msg_values['message_type'] != 'notification')
        if author_subscribe:
            real_author_id = False
            # if current user is active, they are the one doing the action and should
            # be notified of answers. If they are inactive they are posting on behalf
            # of someone else (a custom, mailgateway, ...) and the real author is the
            # message author. In any case avoid odoobot.
            if self.env.user.active:  # note that odoobot is always inactive, there is a python check
                real_author_id = self.env.user.partner_id.id
            elif msg_values['author_id']:
                author = self.env['res.partner'].browse(msg_values['author_id'])
                if author.active and author != self.env.ref('base.partner_root'):  # that happened :(
                    real_author_id = author.id
            if real_author_id:
                self._message_subscribe(partner_ids=[real_author_id])

        self._message_post_after_hook(new_message, msg_values)
        self._notify_thread(new_message, msg_values, **notif_kwargs)
        return new_message

    def _message_post_after_hook(self, message, msg_values):
        """ Hook to add custom behavior after having posted the message. Both
        message and computed value are given, to try to lessen query count by
        using already-computed values instead of having to rebrowse things. """
        return

    def _message_mail_after_hook(self, mails):
        """ Hook to add custom behavior after having sent an mass mailing.

        :param mail.mail mails: mail.mail records about to be sent"""
        return

    def _process_attachments_for_post(self, attachments, attachment_ids, message_values):
        """ Preprocess attachments for MailTread.message_post() or MailMail.create().
        Purpose is to

          * transfer attachments given by ``attachment_ids`` from the composer
            to the record (if any);
          * limit attachments manipulation when being a shared user: only those
            created by the user and linked to the composer are considered;
          * create attachments from ``attachments``. If those are linked to the
            content (body) through CIDs body is updated. CIDs are found and
            replaced by links to web/image as CIDs are not supported as it.

        Note that attachments are created/written in sudo as we consider at this
        point access is granted on related record and/or to post the linked
        message. The caller must verify the access rights accordingly. Indeed
        attachments rights are stricter than message rights which may lead to
        ACLs issues e.g. when posting on a readonly document or replying to
        a notification on a private document.

        :param list(tuple(str,str)) or list(tuple(str,str, dict)) attachments:
          list of attachment tuples in the form ``(name,content)`` or
          `(name,content, info)`` where content is NOT base64 encoded;
        :param list attachment_ids: list of existing attachments to link to this
          message;
        :param message_values: dictionary of values that will be used to create the
          message. It is used to find back record- or content- context;

        :return dict: new values for message: 'attachment_ids' and optionally
          'body' if CIDs have been transformed;
        """
        # allow calling as a model method using model/res_id
        if 'res_id' in message_values:
            model, res_id = message_values['model'], message_values['res_id']
        else:
            self.ensure_one()
            model, res_id = self._name, self.id
        body = ''
        if message_values.get('body'):
            # at this point, body should be valid Markup; other content will be
            # escaped to avoid any issue
            body = escape(message_values['body']) if not is_html_empty(message_values['body']) else ''

        m2m_attachment_ids = []
        if attachment_ids:
            # taking advantage of cache looks better in this case, to check
            filtered_attachment_ids = self.env['ir.attachment'].sudo().browse(attachment_ids).filtered(
                lambda a: a.res_model in ('mail.compose.message', 'mail.scheduled.message') and a.create_uid.id == self._uid)
            # update filtered (pending) attachments to link them to the proper record
            if filtered_attachment_ids:
                filtered_attachment_ids.write({'res_model': model, 'res_id': res_id})
            # prevent public and portal users from using attachments that are not theirs
            if not self.env.user._is_internal():
                attachment_ids = filtered_attachment_ids.ids

            m2m_attachment_ids += [Command.link(id) for id in attachment_ids]

        # Handle attachments parameter, that is a dictionary of attachments
        return_values = {}
        if attachments: # generate
            body_cids, body_filenames = set(), set()
            if body:
                root = lxml.html.fromstring(body)
                # first list all attachments that will be needed in body
                for node in root.iter('img'):
                    if node.get('src', '').startswith('cid:'):
                        body_cids.add(node.get('src').split('cid:')[1])
                    elif node.get('data-filename'):
                        body_filenames.add(node.get('data-filename'))

            attachement_values_list = []
            attachement_extra_list = []
            # generate values
            for attachment in attachments:
                if len(attachment) == 2:
                    name, content = attachment
                    cid = False
                    info = {}
                elif len(attachment) == 3:
                    name, content, info = attachment
                    cid = info and info.get('cid')
                else:
                    continue

                if isinstance(content, str):
                    encoding = info and info.get('encoding')
                    try:
                        content = content.encode(encoding or "utf-8")
                    except UnicodeEncodeError:
                        content = content.encode("utf-8")
                elif isinstance(content, EmailMessage):
                    content = content.as_bytes()
                elif content is None:
                    continue
                attachement_values = {
                    'name': name,
                    'datas': base64.b64encode(content),
                    'type': 'binary',
                    'description': name,
                    'res_model': model,
                    'res_id': res_id,
                }
                token = False
                if (cid and cid in body_cids) or (name and name in body_filenames):
                    token = self.env['ir.attachment']._generate_access_token()
                    attachement_values['access_token'] = token
                attachement_values_list.append(attachement_values)

                # keep cid, name list and token synced with attachement_values_list length to match ids latter
                attachement_extra_list.append((cid, name, token, info))

            new_attachments = self._create_attachments_for_post(attachement_values_list, attachement_extra_list)
            attach_cid_mapping, attach_name_mapping = {}, {}
            for attachment, (cid, name, token, _info) in zip(new_attachments, attachement_extra_list):
                if cid:
                    attach_cid_mapping[cid] = (attachment.id, token)
                if name:
                    attach_name_mapping[name] = (attachment.id, token)
                m2m_attachment_ids.append((4, attachment.id))

            # note: right know we are only taking attachments and ignoring attachment_ids.
            if (body_cids or body_filenames) and body:
                postprocessed = False
                for node in root.iter('img'):
                    att_id, token = False, False
                    if node.get('src', '').startswith('cid:'):
                        cid = node.get('src').split('cid:')[1]
                        att_id, token = attach_cid_mapping.get(cid, (False, False))
                    if (not att_id or not token) and node.get('data-filename'):
                        att_id, token = attach_name_mapping.get(node.get('data-filename'), (False, False))
                    if att_id and token:
                        node.set('src', f'/web/image/{att_id}?access_token={token}')
                        postprocessed = True
                if postprocessed:
                    # tostring being a raw string, we have to respect I/O and return
                    # a valid Markup
                    return_values['body'] = Markup(lxml.html.tostring(root, pretty_print=False, encoding='unicode'))
        return_values['attachment_ids'] = m2m_attachment_ids
        return return_values

    def _create_attachments_for_post(self, values_list, extra_list):
        """ Ease tweaking attachment creation when processing them in posting
        process. Mainly meant for stable version, to be cleaned when reaching
        master. """
        return self.env['ir.attachment'].sudo().create(values_list)

    def _process_attachments_for_template_post(self, mail_template):
        """ Model specific management of attachments used with template attachments
        generation in addition to reports. Only usage currently is for EDI in
        accounting.

        :param mail.template mail_template: a mail.template record used to generate
          message or emails on self;

        :return dict: a dictionary based on self.ids (optional). For each given
          key, value should be a dict holding 'attachments' and 'attachment_ids'
          keys;
        """
        return {}

    # ------------------------------------------------------------
    # MESSAGE POST API / WRAPPERS
    # ------------------------------------------------------------

    def message_mail_with_source(self, source_ref, render_values=None,
                                 message_type='notification',
                                 auto_commit=False,
                                 **kwargs):
        """ Send a mass mail on self, using an external source to render part
        of the content. It can be either a 'mail.template', either a view used
        to render the body using QWeb.

        SPOILER: this method currently calls a composer in a loop when using
        a view even if it is suboptimal. This is due to current composer
        implementation.. This will be cleaned soon to  optimize mass mailing
        through mail.thread and lessen usage of composer itself.

        Default values
          * subtype_id: will be False, forced by composer in mass mode;

        :param record/str source_ref: reference to a source for rendering.
          It can be one of
            * a MailTemplate record. It will be used to render the various
              message values (body, subject, recipients, ...). It should behave
              like using the mail composer with a template;
            * an IrUIView record. It will be used to render the content
              (body). Other fields are left to the caller and/or default values
              computation;
            * an XmlID of a MailTemplate or of an IrUiView: see above;
        :param dict render_values: additional rendering values for qweb context;

        :param str message_type: one of 'notification' or 'comment';
        :param bool auto_commit: auto commit after each batch of emails sent
          (see ``MailComposer._action_send_mail()``);
        :param dict kwargs: additional values given to the 'mail.compose.message'
          creation;

        :return: created mail.mail records, as sudo
        """
        template, view = self._get_source_from_ref(source_ref)

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            forbidden_names={'body', 'composition_mode', 'model', 'res_id', 'values'}
        )

        # with a view, render bodies in batch (template is managed by composer)
        bodies = self.env['mail.render.mixin']._render_template_qweb_view(
            view,
            self._name,
            self.ids,
            add_context=render_values,
        ) if view else {}

        # Prepare composer values for creation
        composer_values = {
            'composition_mode': 'mass_mail',
            'message_type': message_type,
            # subtype is not really used in mass mail mode as it is used mainly
            # when posting, but keep it in case it is used in post send
            'subtype_id': kwargs.pop('subtype_id', False) or self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            **kwargs,
        }
        composer_ctx = {
            'default_composition_mode': 'mass_mail',
            'default_model': self._name,
            'default_template_id': template.id if template else False,
        }

        mails_su = self.env['mail.mail'].sudo()
        for subset in [self] if template else self:
            composer_ctx['default_res_ids'] = subset.ids
            if not template:
                composer_values['body'] = bodies[subset.id]

            composer = self.env['mail.compose.message'].with_context(
                **composer_ctx
            ).create(composer_values)
            mails_as_sudo, _messages = composer._action_send_mail(auto_commit=auto_commit)
            mails_su += mails_as_sudo
        return mails_su

    def message_post_with_source(self, source_ref, render_values=None,
                                 message_type='notification',
                                 subtype_xmlid=False, subtype_id=False,
                                 **kwargs):
        """ Post a message on each record of self, using a view to render the
        body using QWeb.

        Default values
          * subtype_id: if not given, fallback on ``note`` to be consistent
            with what message_post does;

        :param record/str source_ref: reference to a source for rendering.
          It can be one of
            * a MailTemplate record. It will be used to render the various
              message values (body, subject, recipients, ...). It should behave
              like using the mail composer with a template;
            * an IrUIView record. It will be used to render the content
              (body). Other fields are left to the caller and/or default values
              computation;
            * an XmlID of a MailTemplate or of an IrUiView: see above
        :param dict render_values: additional rendering values for qweb context;

        :param str message_type: one of 'notification' or 'comment';
        :param str subtype_xmlid: optional xml id of a mail.message.subtype to
          fetch, will force value of subtype_id;
        :param int subtype_id: subtype_id of the message, used mainly for followers
            notification mechanism;
        :param dict kwargs: additional values given to the 'mail.compose.message'
          creation;

        :return: posted mail.message records
        """
        template, view = self._get_source_from_ref(source_ref)

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            forbidden_names={'body', 'composition_mode', 'model', 'res_id', 'values'}
        )

        # with a view, render bodies in batch (template is managed by composer)
        bodies = self.env['mail.render.mixin']._render_template_qweb_view(
            view,
            self._name,
            self.ids,
            add_context=render_values,
        ) if view else {}

        # Prepare composer values for creation
        if subtype_xmlid:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        messages_all = self.env['mail.message']
        for record in self:
            if template:
                composer = self.env['mail.compose.message'].with_context(
                    default_composition_mode='comment',
                    default_model=self._name,
                    default_res_ids=record.ids,
                    default_template_id=template.id,
                ).create({
                    'message_type': message_type,
                    'subtype_id': subtype_id,
                    **kwargs,
                })
                _mails_as_sudo, messages = composer._action_send_mail()
                messages_all += messages
            else:
                messages_all += record.message_post(
                    body=bodies[record.id],
                    message_type=message_type,
                    subtype_id=subtype_id,
                    **kwargs
                )
        return messages_all

    def message_notify(self, *,
                       body='', subject=False,
                       author_id=None, email_from=None,
                       model=False, res_id=False,
                       subtype_xmlid=None, subtype_id=False, partner_ids=False,
                       attachments=None, attachment_ids=None,
                       **kwargs):
        """ Shortcut allowing to notify partners of messages that should not be
        displayed on a document. It pushes notifications on inbox or by email
        depending on the user configuration, like other notifications.

        Default values
          * subtype_id: if not given, fallback on ``note`` to be consistent
            with what message_post does;

        :param str body: body of the message, usually raw HTML that will
          be sanitized
        :param str subject: subject of the message
        :param int author_id: optional ID of partner record being the author. See
          ``_message_compute_author`` that uses it to make email_from / author_id coherent;
        :param str email_from: from address of the author. See ``_message_compute_author``
          that uses it to make email_from / author_id coherent;
        :param str model: when invoked on MailThread directly, this method
          allows to push a notification on a given record (allows to notify
          on not thread-enabled records);
        :param int res_id: defines the record in combination with model;
        :param str subtype_xmlid: optional xml id of a mail.message.subtype to
          fetch, will force value of subtype_id;
        :param int subtype_id: subtype_id of the message, used mainly for followers
          notification mechanism;
        :param list(int) partner_ids: partner_ids to notify in addition to partners
            computed based on subtype / followers matching;
        :param list(tuple(str,str), tuple(str,str, dict)) attachments : list of attachment
            tuples in the form ``(name,content)`` or ``(name,content, info)`` where content
            is NOT base64 encoded;
        :param list attachment_ids: list of existing attachments to link to this message
            Should not be a list of commands. Attachment records attached to mail
            composer will be attached to the related document.

        Extra keyword arguments will be used either
          * as default column values for the new mail.message record if they match
            mail.message fields;
          * propagated to notification methods if not;

        :return: posted mail.message records
        """
        if self:
            self.ensure_one()
        if not partner_ids:
            _logger.warning('Message notify called without recipient_ids, skipping')
            return self.env['mail.message']

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            forbidden_names={'message_id', 'message_type', 'parent_id'}
        )
        if attachments:
            # attachments should be a list (or tuples) of 3-elements list (or tuple)
            valid = all(isinstance(attachment, (list, tuple)) and len(attachment) in (3, 2) for attachment in attachments)
            if not valid:
                raise ValueError(
                    _('Notification should receive attachments as a list of list or tuples (received %(aids)s)',
                      aids=repr(attachment_ids),
                     )
                )
        if attachment_ids and not is_list_of(attachment_ids, int):
            raise ValueError(
                _('Notification should receive attachments records as a list of IDs (received %(aids)s)',
                  aids=repr(attachment_ids),
                 )
            )
        if not is_list_of(partner_ids, int):
            raise ValueError(
                _('Notification should receive partners given as a list of IDs (received %(pids)s)',
                  pids=repr(partner_ids),
                 )
            )

        # split message additional values from notify additional values
        msg_kwargs = {key: val for key, val in kwargs.items() if key in self.env['mail.message']._fields}
        notif_kwargs = {key: val for key, val in kwargs.items() if key not in msg_kwargs}

        author_id, email_from = self._message_compute_author(author_id, email_from, raise_on_email=True)

        # allow to link a notification to a document that does not inherit from
        # MailThread by supporting model / res_id, but then both value should be set
        if not model or not res_id:
            model, res_id = False, False

        if subtype_xmlid:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id(subtype_xmlid)
        if not subtype_id:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        msg_values = {
            # author
            'author_id': author_id,
            'email_from': email_from,
            # document
            'model': self._name if self else model,
            'record_name': False,
            'res_id': self.id if self else res_id,
            # content
            'body': escape(body),  # escape if text, keep if markup
            'is_internal': True,
            'message_type': 'user_notification',
            'subject': subject,
            'subtype_id': subtype_id,
            # recipients
            'message_id': generate_tracking_message_id('message-notify'),
            'partner_ids': partner_ids,
            # notification
            'email_add_signature': True,
        }
        msg_values.update(msg_kwargs)
        # add default-like values afterwards, to avoid useless queries
        if self:
            if 'record_alias_domain_id' not in msg_values:
                msg_values['record_alias_domain_id'] = self._mail_get_alias_domains(default_company=self.env.company)[self.id].id
            if 'record_company_id' not in msg_values:
                msg_values['record_company_id'] = self._mail_get_companies(default=self.env.company)[self.id].id
        if 'reply_to' not in msg_values:
            msg_values['reply_to'] = self._notify_get_reply_to(default=email_from)[self.id if self else False]

        msg_values.update(
            self._process_attachments_for_post(attachments, attachment_ids, msg_values)
        )  # attachement_ids, body

        new_message = self._message_create([msg_values])
        self._fallback_lang()._notify_thread(new_message, msg_values, **notif_kwargs)
        return new_message

    def _message_log_with_view(self, view_ref, render_values=None,
                               message_type='notification', **kwargs):
        """ Log a message on each record of self, using a view to render the
        body using QWeb.

        :param str/int/record view_ref: source QWeb template. It should be an
          XmlID allowing to fetch an ``ir.ui.view``, or an ID of a view or
          an ``ir.ui.view`` record;
        :param dict render_values: additional rendering values for qweb context;
        :param str message_type: one of 'notification' or 'comment';
        :param kwargs: additional values propagated to ``_message_log``;

        :return: posted mail.message records (as sudo)
        """
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            forbidden_names={'body', 'bodies'}
        )

        # with a view, render bodies in batch (template is managed by composer)
        bodies = self.env['mail.render.mixin']._render_template_qweb_view(
            view_ref,
            self._name,
            self.ids,
            add_context=render_values,
        )

        return self._message_log_batch(
            bodies=bodies,
            message_type=message_type,
            **kwargs
        )

    def _message_log(self, *,
                     body='', subject=False,
                     author_id=None, email_from=None,
                     message_type='notification',
                     partner_ids=False,
                     attachment_ids=False, tracking_value_ids=False):
        """ Shortcut allowing to post note on a document. See ``_message_log_batch``
        for more details. """
        self.ensure_one()

        return self._message_log_batch(
            {self.id: body}, subject=subject,
            author_id=author_id, email_from=email_from,
            message_type=message_type,
            partner_ids=partner_ids,
            attachment_ids=attachment_ids, tracking_value_ids=tracking_value_ids
        )

    def _message_log_batch(self, bodies, subject=False,
                           author_id=None, email_from=None,
                           message_type='notification',
                           partner_ids=False,
                           attachment_ids=False, tracking_value_ids=False):
        """ Shortcut allowing to post notes on a batch of documents. It does not
        perform any notification and pre-computes some values to have a short code
        as optimized as possible. This method is private as it does not check
        access rights and perform the message creation as sudo to speedup
        the log process. This method should be called within methods where
        access rights are already granted to avoid privilege escalation.

        :param bodies: dict {record_id: body}
        :param list partner_ids: optional partners, not used in any notification
          mechanism. This is mainly used to link a log to a specific customer
          like SMS or WhatsApp log;
        :return: created messages (as sudo)
        """
        # protect against side-effect prone usage
        if len(self) > 1 and (attachment_ids or tracking_value_ids):
            raise ValueError(_('Batch log cannot support attachments or tracking values on more than 1 document'))

        author_id, email_from = self._message_compute_author(author_id, email_from, raise_on_email=False)

        base_message_values = {
            # author
            'author_id': author_id,
            'email_from': email_from,
            # document
            'model': self._name,
            'record_alias_domain_id': False,
            'record_company_id': False,
            'record_name': False,
            # content
            'attachment_ids': attachment_ids,
            'message_type': message_type,
            'is_internal': True,
            'subject': subject,
            'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            'tracking_value_ids': tracking_value_ids,
            # recipients
            'email_add_signature': False,  # False as no notification -> no need to compute signature
            'message_id': generate_tracking_message_id('message-notify'),  # why? this is all but a notify
            'partner_ids': partner_ids,
            'reply_to': self.env['mail.thread']._notify_get_reply_to(default=email_from)[False],
        }

        values_list = [dict(base_message_values,
                            res_id=record.id,
                            body=escape(bodies.get(record.id, '')))
                       for record in self]
        return self.sudo()._message_create(values_list)

    # ------------------------------------------------------------
    # MAIL.MESSAGE HELPERS
    # ------------------------------------------------------------

    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """ Tool method computing author information for messages. Purpose is
        to ensure maximum coherence between author / current user / email_from
        when sending emails.

        :param raise_on_email: if email_from is not found, raise an UserError

        :return tuple: res.partner ID (may be False or None), email_from
        """
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
        if not email_from and raise_on_email and not self.env.su:
            raise exceptions.UserError(_("Unable to send message, please configure the sender's email address."))

        return author_id, email_from

    def _message_compute_parent_id(self, parent_id):
        # parent management, depending on ``_mail_flat_thread``
        # ``_mail_flat_thread`` True: no free message. If no parent, find the first
        # posted message and attach new message to it. If parent, get back to the first
        # ancestor and attach it. We don't keep hierarchy (one level of threading).
        # ``_mail_flat_thread`` False: free message = new thread (think of mailing lists).
        # If parent get up one level to try to flatten threads without completely
        # removing hierarchy.
        MailMessage_sudo = self.env['mail.message'].sudo()
        if self._mail_flat_thread and not parent_id:
            parent_message = MailMessage_sudo.search([('res_id', '=', self.id), ('model', '=', self._name), ('message_type', '!=', 'user_notification')], order="id ASC", limit=1)
            # parent_message searched in sudo for performance, only used for id.
            # Note that with sudo we will match message with internal subtypes.
            parent_id = parent_message.id if parent_message else False
        elif parent_id:
            current_ancestor = MailMessage_sudo.search([('id', '=', parent_id), ('parent_id', '!=', False)])
            if self._mail_flat_thread:
                if current_ancestor:
                    # avoid loops when finding ancestors
                    processed_list = []
                    while (current_ancestor.parent_id and current_ancestor.parent_id not in processed_list):
                        processed_list.append(current_ancestor)
                        current_ancestor = current_ancestor.parent_id
                    parent_id = current_ancestor.id
            else:
                parent_id = current_ancestor.parent_id.id if current_ancestor.parent_id else parent_id
        return parent_id

    def _message_compute_subject(self):
        """ Get the default subject for a message posted in this record's
        discussion thread.

        :return str: default subject """
        self.ensure_one()
        return self.display_name

    def _message_create(self, values_list):
        """ Low-level helper to create mail.message records. It is mainly used
        to hide the cleanup of given values, for mail gateway or helpers."""
        values_list = [
            {
                key: val
                for key, val in values.items()
                if key not in self._get_message_create_ignore_field_names()
            }
            for values in values_list
        ]
        create_values_list = []

        # preliminary value safety check
        self._raise_for_invalid_parameters(
            {key for values in values_list for key in values.keys()},
            restricting_names=self._get_message_create_valid_field_names()
        )

        for values in values_list:
            create_values = dict(values)
            create_values['partner_ids'] = [Command.link(pid) for pid in (create_values.get('partner_ids') or [])]
            create_values_list.append(create_values)

        # remove context, notably for default keys, as this thread method is not
        # meant to propagate default values for messages, only for master records
        return self.env['mail.message'].with_context(
            clean_context(self.env.context)
        ).create(create_values_list)

    def _get_message_create_valid_field_names(self):
        """ Some fields should not be given when creating a mail.message from
        mail.thread main API methods (in addition to some API specific check).
        Those fields are generally used through UI or dedicated methods. We
        therefore give an allowed field names list. """
        return {
            'attachment_ids',
            'author_guest_id',
            'author_id',
            'body',
            'create_date',  # anyway limited to admins
            'date',
            'email_add_signature',
            'email_from',
            'email_layout_xmlid',
            'is_internal',
            'mail_activity_type_id',
            'mail_server_id',
            'message_id',
            'message_type',
            'model',
            'parent_id',
            'partner_ids',
            'record_alias_domain_id',
            'record_company_id',
            'record_name',
            'reply_to',
            'reply_to_force_new',
            'res_id',
            'subject',
            'subtype_id',
            'tracking_value_ids',
        }

    def _get_message_create_ignore_field_names(self):
        """Some fields should be silently ignored when creating a mail.message,
        without raising an exception. Those fields are generally handled in
        _message_post_after_hook, which also receives message values."""
        return set()

    def _get_source_from_ref(self, source_ref):
        """ From a source_reference, return either a mail template, either
        an ir ui view.

        :return tuple(template, view): one is a recordset (may be void if
          source_ref is a void recordset, or a singleton), the other one is
          False. Always only one is set, as source is either a template,
          either a view.
        """
        template, view = False, False
        if isinstance(source_ref, models.BaseModel):
            if source_ref._name == 'mail.template':
                template = source_ref
            elif source_ref._name == 'ir.ui.view':
                view = source_ref
            else:
                raise ValueError(
                    _('Invalid template or view source record %(svalue)s, is %(model)s instead',
                       svalue=source_ref,
                       model=source_ref._name,
                    ))
            if not template and not view:
                raise ValueError(
                    _('Mailing or posting with a source should not be called with an empty %(source_type)s',
                      source_type=_('template') if template is not False else _('view'))
                )
        elif isinstance(source_ref, str):
            try:
                res_model, res_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(
                    source_ref,
                    raise_if_not_found=True
                )
            except ValueError as e:
                raise ValueError(
                    _('Invalid template or view source Xml ID %(source_ref)s does not exist anymore',
                      source_ref=source_ref)
                ) from e
            if res_model == 'mail.template':
                template = self.env['mail.template'].browse(res_id)
            elif res_model == 'ir.ui.view':
                view = self.env['ir.ui.view'].browse(res_id)
            else:
                raise ValueError(
                    _('Invalid template or view source reference %(svalue)s, is %(model)s instead',
                       svalue=source_ref,
                       model=res_model,
                    ))
        else:
            raise ValueError(
                _('Invalid template or view source %(svalue)s (type %(stype)s), should be a record or an XMLID',
                  svalue=source_ref,
                  stype=type(source_ref),
                ))
        return template, view

    def _get_notify_valid_parameters(self):
        """ Several parameters exist for notification methods as business
        flows often want to customize the standard notification experience.
        In order to ease coding kwargs are frequently used. This method
        acts like a filter, allowing to spot parameters that are not
        supported. """
        return {
            'force_email_company',
            'force_email_lang',
            'force_send',
            'mail_auto_delete',
            'model_description',
            'notify_author',
            'resend_existing',
            'scheduled_date',
            'send_after_commit',
            'skip_existing',
            'subtitles',
        }

    @api.model
    def _is_notification_scheduled(self, notify_scheduled_date):
        """ Helper to check if notification are about to be scheduled. Eases
        overrides.

        :param notify_scheduled_date: value of 'scheduled_date' given in
          notification parameters: arbitrary datetime (as a date, datetime or
          a string), may be void. See 'MailMail._parse_scheduled_datetime()';

        :return bool: True if a valid datetime has been found and is in the
          future; False otherwise.
        """
        if notify_scheduled_date:
            parsed_datetime = self.env['mail.mail']._parse_scheduled_datetime(notify_scheduled_date)
            notify_scheduled_date = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False
        return notify_scheduled_date if notify_scheduled_date and notify_scheduled_date > self.env.cr.now() else False

    def _raise_for_invalid_parameters(self, parameter_names, forbidden_names=None, restricting_names=None):
        """ Helper to warn about invalid parameters (or fields).

        :param set parameter_names: a set of parameter names;
        :param set forbidden_names: set of parameter name that should not be
          present in parameter_names;
        :param set restricting_names: set of parameters restricting given
          parameter_names, parameters not belonging to this list are rejected;
        """
        if forbidden_names:
            conflicting_names = parameter_names & forbidden_names
        elif restricting_names:
            conflicting_names = parameter_names - restricting_names
        if conflicting_names:
            raise ValueError(
                _('Those values are not supported when posting or notifying: %(param_names)s',
                  param_names=', '.join(conflicting_names))
            )

    # ------------------------------------------------------
    # NOTIFICATION API
    # ------------------------------------------------------

    def _notify_cancel_by_type_generic(self, notification_type):
        """ Standard implementation for canceling notifications by type that cancels notifications
         * in 'bounce' and 'exception' status
         * of the current user
         * of the given type
         * for mail_message related to the model implemented by this class
         It also sends bus notifications to update status of notifications in the web client.
        """
        author_id = self.env.user.partner_id.id
        self._cr.execute("""
                    SELECT notif.id, msg.id
                      FROM mail_notification notif
                      JOIN mail_message msg ON notif.mail_message_id = msg.id
                      WHERE notif.notification_type = %(notification_type)s
                      AND notif.author_id = %(author_id)s
                      AND notif.notification_status IN ('bounce', 'exception')
                      AND msg.model = %(model_name)s
                """, {'model_name': self._name, 'author_id': author_id, 'notification_type': notification_type})
        records = self._cr.fetchall()
        if records:
            notif_ids, msg_ids = zip(*records)
            msg_ids = list(set(msg_ids))
            if notif_ids:
                self.env['mail.notification'].browse(notif_ids).sudo().write({'notification_status': 'canceled'})
            if msg_ids:
                self.env['mail.message'].browse(msg_ids)._notify_message_notification_update()
        return True

    @api.model
    def notify_cancel_by_type(self, notification_type):
        """ Subclasses must call this method and then
         * either call the standard implementation _notify_cancel_by_type_generic
         * or implements their own logic
        """
        if not self.env.user._is_internal():
            raise exceptions.AccessError(_("Access Denied"))
        self.browse().check_access('read')

        if notification_type == 'email':
            self._notify_cancel_by_type_generic('email')
        return True

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """ Main notification method. This method basically does two things

         * call ``_notify_get_recipients`` that computes recipients to
           notify based on message record or message creation values if given
           (to optimize performance if we already have data computed);
         * performs the notification process by calling the various notification
           methods implemented;

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        Kwargs allow to pass various parameters that are given to sub notification
        methods. See those methods for more details about supported parameters.
        Specific kwargs used in this method:

          * ``scheduled_date``: delay notification sending if set in the future.
            This is done using the ``mail.message.schedule`` intermediate model;

        :return: recipients data (see ``MailThread._notify_get_recipients()``)
        """
        # add lang to context immediately since it will be useful in various rendering later
        self = self._fallback_lang()
        self._raise_for_invalid_parameters(
            set(kwargs.keys()),
            restricting_names=self._get_notify_valid_parameters()
        )

        recipients_data = self._notify_get_recipients(message, msg_vals=msg_vals, **kwargs)
        if not recipients_data:
            return recipients_data
        # cache data fetched by manual query to avoid extra queries when reading user.partner_id
        for r in filter(lambda r: r["uid"], recipients_data):
            user = self.env["res.users"].browse(r["uid"])
            self.env.cache.insert_missing(user, user._fields["partner_id"], [r["id"]])
        # if scheduled for later: add in queue instead of generating notifications
        scheduled_date = self._is_notification_scheduled(kwargs.pop('scheduled_date', None))
        if scheduled_date:
            # send the message notifications at the scheduled date
            self.env['mail.message.schedule'].sudo().create({
                'scheduled_datetime': scheduled_date,
                'mail_message_id': message.id,
                'notification_parameters': json.dumps(kwargs),
            })
        else:
            # generate immediately the <mail.notification>
            # and send the <mail.mail>, <mail.push> and the <bus.bus> notifications
            self._notify_thread_by_inbox(message, recipients_data, msg_vals=msg_vals, **kwargs)
            self._notify_thread_by_email(message, recipients_data, msg_vals=msg_vals, **kwargs)
            self._notify_thread_by_web_push(message, recipients_data, msg_vals=msg_vals, **kwargs)

        return recipients_data

    def _notify_thread_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Notify recipients inbox of a message. It is done in two main steps

          * create inbox notifications for users;
          * send bus notifications;

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;
        """
        inbox_pids_uids = sorted(
            [(r["id"], r["uid"]) for r in recipients_data if r["id"] and r["notif"] == "inbox"]
        )
        if inbox_pids_uids:
            notif_create_values = [
                {
                    "author_id": message.author_id.id,
                    "mail_message_id": message.id,
                    "notification_status": "sent",
                    "notification_type": "inbox",
                    "res_partner_id": pid_uid[0],
                }
                for pid_uid in inbox_pids_uids
            ]
            # sudo: mail.notification - creating notifications is the purpose of notify methods
            self.env["mail.notification"].sudo().create(notif_create_values)
            users = self.env["res.users"].browse(i[1] for i in inbox_pids_uids if i[1])
            # sudo: mail.followers - reading followers of target users in batch to send it to them
            followers = self.env["mail.followers"].sudo().search(
                [
                    ("res_model", "=", message.model),
                    ("res_id", "=", message.res_id),
                    ("partner_id", "in", users.partner_id.ids),
                ]
            )
            for user in users:
                user._bus_send_store(
                    message.with_user(user).with_context(allowed_company_ids=[]),
                    msg_vals=msg_vals,
                    for_current_user=True,
                    add_followers=True,
                    followers=followers,
                    notification_type="mail.message/inbox",
                )

    def _notify_thread_by_email(self, message, recipients_data, msg_vals=False,
                                mail_auto_delete=True,  # mail.mail
                                model_description=False, force_email_company=False, force_email_lang=False,  # rendering
                                subtitles=None,  # rendering
                                resend_existing=False, force_send=True, send_after_commit=True,  # email send
                                 **kwargs):
        """ Method to send emails notifications linked to a message.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :param bool mail_auto_delete: delete notification emails once sent;

        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param record force_email_company: <res.company> record used when rendering
          notification layout. Otherwise computed based on current record;
        :param str force_email_lang: lang used when rendering content, used
          notably to compute model name or translate access buttons;
        :param list subtitles: optional list set as template value "subtitles";

        :param bool resend_existing: check for existing notifications to update
          based on mailed recipient, otherwise create new notifications;
        :param bool force_send: send emails directly instead of using queue;
        :param bool send_after_commit: if force_send, tells to send emails after
          the transaction has been committed using a post-commit hook;
        """
        partners_data = [r for r in recipients_data if r['notif'] == 'email']
        if not partners_data:
            return True

        base_mail_values = self._notify_by_email_get_base_mail_values(
            message,
            additional_values={'auto_delete': mail_auto_delete}
        )

        # Clean the context to get rid of residual default_* keys that could cause issues during
        # the mail.mail creation.
        # Example: 'default_state' would refer to the default state of a previously created record
        # from another model that in turns triggers an assignation notification that ends up here.
        # This will lead to a traceback when trying to create a mail.mail with this state value that
        # doesn't exist.
        SafeMail = self.env['mail.mail'].sudo().with_context(clean_context(self._context))
        SafeNotification = self.env['mail.notification'].sudo().with_context(clean_context(self._context))
        emails = self.env['mail.mail'].sudo()

        # loop on groups (customer, portal, user,  ... + model specific like group_sale_salesman)
        gen_batch_size = int(
            self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')
        ) or 50  # be sure to not have 0, as otherwise no iteration is done
        notif_create_values = []
        for _lang, render_values, recipients_group in self._notify_get_classified_recipients_iterator(
            message,
            partners_data,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            subtitles=subtitles,
        ):
            # generate notification email content
            mail_body = self._notify_by_email_render_layout(
                message,
                recipients_group,
                msg_vals=msg_vals,
                render_values=render_values,
            )
            recipients_ids = recipients_group['recipients_ids']

            # create email
            for recipients_ids_chunk in split_every(gen_batch_size, recipients_ids):
                mail_values = self._notify_by_email_get_final_mail_values(
                    recipients_ids_chunk,
                    base_mail_values,
                    additional_values={'body_html': mail_body}
                )
                new_email = SafeMail.create(mail_values)

                if new_email and recipients_ids_chunk:
                    tocreate_recipient_ids = list(recipients_ids_chunk)
                    if resend_existing:
                        existing_notifications = self.env['mail.notification'].sudo().search([
                            ('mail_message_id', '=', message.id),
                            ('notification_type', '=', 'email'),
                            ('res_partner_id', 'in', tocreate_recipient_ids)
                        ])
                        if existing_notifications:
                            tocreate_recipient_ids = [rid for rid in recipients_ids_chunk if rid not in existing_notifications.mapped('res_partner_id.id')]
                            existing_notifications.write({
                                'notification_status': 'ready',
                                'mail_mail_id': new_email.id,
                            })
                    notif_create_values += [{
                        'author_id': message.author_id.id,
                        'is_read': True,  # discard Inbox notification
                        'mail_mail_id': new_email.id,
                        'mail_message_id': message.id,
                        'notification_status': 'ready',
                        'notification_type': 'email',
                        'res_partner_id': recipient_id,
                    } for recipient_id in tocreate_recipient_ids]
                emails += new_email

        if notif_create_values:
            SafeNotification.create(notif_create_values)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.current_thread(), 'testing', False)
        if force_send := self.env.context.get('mail_notify_force_send', force_send):
            force_send_limit = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail.force.send.limit', 100))
            force_send = len(emails) < force_send_limit
        if force_send and (not self.pool._init or test_mode):
            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                emails.send_after_commit()
            else:
                emails.send()

        return True

    def _notify_get_classified_recipients_iterator(
            self, message, recipients_data, msg_vals=False,
            model_description=False, force_email_company=False, force_email_lang=False,  # rendering
            subtitles=None):
        """ Make groups of recipients, based on 'recipients_data' which is a list
        of recipients informations. Purpose of this method is to group them by
        main usage ('user', 'portal_user', 'follower', 'customer', ... see
        @_notify_get_recipients_classify) and lang. Each group is linked to
        an evaluation context to render the notification layout.

        :param message: ``mail.message`` record to notify;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param msg_vals: dictionary of values used to create the message. If
          given it may be used to access values related to ``message``;

        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param record force_email_company: <res.company> record used when rendering
          notification layout. Otherwise computed based on current record;
        :param str force_email_lang: when no specific lang is found this is the
          default lang to use notably to compute model name or translate access
          buttons;
        :param list subtitles: optional list set as template value "subtitles";

        :return: iterator based on recipients classified by lang, with their
          rendering evaluation context. Each item is a tuple containing (
            lang: used for rendering (customer language, forced email, default
              environment language,
            render_values: used to render the notification layout and translated
              using lang,
            recipients_group: a recipients group is a dict containing data
              defined in "_notify_get_recipients_groups" like {
              'active': if not, it is skipped in notification process (ease
                        inheritance to be already present);
              'button_access': main access document button information, {'url'
                               link of the access, 'title': link or button
                               string};
              'has_button_access': display access document main button in email;
              'notification_group_name': name of the group, to ease usage;
              'recipients_data': list of recipients data, following format used
                                 in '_notify_get_recipients'. It is fillup when
                                 evaluating groups;
              'recipients_ids': list of partner IDs, based on partner ID present in
                                recipients_data (allows mainly to speedup some
                                data computation);
           }
          );
        """
        lang_to_recipients = {}
        for data in recipients_data:
            # filter active lang
            if lang_code := data.get('lang'):
                lang_code = bool(self.env['res.lang']._lang_get(lang_code)) and lang_code
            lang_to_recipients.setdefault(
                lang_code or force_email_lang or self.env.lang,
                [],
            ).append(data)

        for lang, lang_recipients_data in lang_to_recipients.items():
            record_wlang = self.with_context(lang=lang)
            lang_model_description = model_description
            if not lang_model_description:
                lang_model_description = record_wlang._get_model_description(msg_vals and msg_vals.get('model') or message.model)
            recipients_groups_list = record_wlang._notify_get_recipients_classify(
                message,
                lang_recipients_data,
                lang_model_description,
                msg_vals=msg_vals,
            )
            render_values = record_wlang._notify_by_email_prepare_rendering_context(
                message,
                msg_vals=msg_vals,
                model_description=lang_model_description,
                force_email_company=force_email_company,
                force_email_lang=lang,
            ) # 10 queries
            if subtitles:
                render_values['subtitles'] = subtitles

            for recipients_group in recipients_groups_list:
                if not render_values['show_unfollow']:
                    render_values['show_unfollow'] = any(
                        r['is_follower']
                        for r in recipients_group['recipients_data']
                        if r['id'] and r['uid'] and not r['ushare']
                    )
                yield (lang, render_values, recipients_group)

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False,
                                                   model_description=False,
                                                   force_email_company=False,
                                                   force_email_lang=False):
        """ Prepare rendering context for notification email.

        Signature: if asked a default signature is computed based on author. Either
        it has an user and we use the user's signature. Either we do not find any
        user and we compute a default one based on the author's name.

        Company: either there is one defined on the record (company_id field set
        with a value), either we use env.company. A new parameter allows to force
        its value.

        Lang: when calling this method, ``_fallback_lang`` should already been
        called, or a lang set in context with another way. A wild guess is done
        based on templates to try to retrieve the recipient's language when a flow
        like "send by email" is performed. Lang is used to try to have the
        notification layout in the same language as the email content. A new
        parameter allows to force its value.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param record force_email_company: <res.company> record used when rendering
          notification layout. Otherwise computed based on current record;
        :param str force_email_lang: lang used when rendering content, used
          notably to compute model name or translate access buttons;

        :return: dictionary of values used when rendering notification layout;
        """
        msg_vals = msg_vals or {}

        lang = force_email_lang if force_email_lang else self.env.lang
        record_wlang = self.with_context(lang=lang)

        # compute send user and its related signature; try to use self.env.user instead of browsing
        # user_ids if they are the author will give a sudo user, improving access performances and cache usage.
        signature = ''
        email_add_signature = msg_vals['email_add_signature'] if 'email_add_signature' in msg_vals else message.email_add_signature
        if email_add_signature:
            author = message.env['res.partner'].browse(msg_vals['author_id']) if 'author_id' in msg_vals else message.author_id
            author_user = self.env.user if self.env.user.partner_id == author else author.user_ids[0] if author and author.user_ids else False
            if author_user:
                signature = author_user.signature

        if force_email_company:
            company = force_email_company
        else:
            company = record_wlang.company_id.sudo() if (
                record_wlang and 'company_id' in record_wlang and record_wlang.company_id
            ) else record_wlang.env.company
        if company.website:
            website_url = 'http://%s' % company.website if not company.website.lower().startswith(('http:', 'https:')) else company.website
        else:
            website_url = False

        # record, model
        if not model_description:
            model_description = record_wlang._get_model_description(msg_vals['model'] if 'model' in msg_vals else message.model)
        record_name = msg_vals['record_name'] if 'record_name' in msg_vals else message.record_name

        # tracking: in case of missing value, perform search (skip only if sure we don't have any)
        check_tracking = msg_vals.get('tracking_value_ids', True) if msg_vals else bool(self)
        tracking = []
        if check_tracking:
            tracking_values = self.env['mail.tracking.value'].sudo().search(
                [('mail_message_id', 'in', message.ids)]
            )._filter_has_field_access(self.env)
            if tracking_values and hasattr(record_wlang, '_track_filter_for_display'):
                tracking_values = record_wlang._track_filter_for_display(tracking_values)
            tracking = [
                (
                    fmt_vals['changedField'],
                    fmt_vals['oldValue']['value'],
                    fmt_vals['newValue']['value'],
                ) for fmt_vals in tracking_values._tracking_value_format()
            ]

        subtype_id = msg_vals['subtype_id'] if 'subtype_id' in msg_vals else message.subtype_id.id
        is_discussion = subtype_id == self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

        return {
            # message
            'is_discussion': is_discussion,
            'message': message,
            'subtype': message.subtype_id,
            'tracking_values': tracking,
            # record
            'model_description': model_description,
            'record': record_wlang,
            'record_name': record_name,
            'subtitles': [record_name],
            # user / environment
            'company': company,
            'email_add_signature': email_add_signature,
            'lang': lang,
            'show_unfollow': getattr(self, '_partner_unfollow_enabled', False),
            'signature': signature,
            'website_url': website_url,
            # tools
            'is_html_empty': is_html_empty,
        }

    def _notify_by_email_render_layout(self, message, recipients_group,
                                       msg_vals=False,
                                       render_values=None):
        """ Renders the email layout for a given recipients group which
        encapsulate the message body.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param dict recipients_group: a dict containing data for the recipients,
          see @ _notify_get_recipients_groups;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;
        :param dict render_values: values to render the notification layout;

        At this point expected values are
          render_values: company, is_discussion, lang, message, model_description,
                         record, record_name, signature, subtype, tracking_values,
                         website_url
          recipients_group: active, button_access, has_button_access,
                            notification_group_name, recipients

        :return str: rendered complete layout;
        """
        if render_values is None:
            render_values = {}
        msg_vals = msg_vals or {}

        email_layout_xmlid = msg_vals['email_layout_xmlid'] if 'email_layout_xmlid' in msg_vals else message.email_layout_xmlid
        template_xmlid = email_layout_xmlid if email_layout_xmlid else 'mail.mail_notification_layout'

        render_values = {**render_values, **recipients_group}
        mail_body = self.env['ir.qweb']._render(
            template_xmlid,
            render_values,
            minimal_qcontext=True,
            raise_if_not_found=False,
            lang=render_values.get('lang', self.env.lang),
        )
        if not mail_body:
            _logger.warning('QWeb template %s not found or is empty when sending notification emails. Sending without layouting.', template_xmlid)
            mail_body = message.body
        return mail_body

    def _notify_by_email_get_base_mail_values(self, message, additional_values=None):
        """ Return model-specific and message-related values to be used when
        creating notification emails. It serves as a common basis for all
        notification emails based on a given message.

        :param record message: <mail.message> record being notified;
        :param dict additional_values: optional additional values to add (ease
          custom calls and inheritance);

        :return: dictionary of values suitable for a <mail.mail> create;
        """
        mail_subject = message.subject
        if not mail_subject and self and hasattr(self, '_message_compute_subject'):
            mail_subject = self._message_compute_subject()
        if not mail_subject:
            mail_subject = message.record_name
        if mail_subject:
            # replace new lines by spaces to conform to email headers requirements
            mail_subject = ' '.join(mail_subject.splitlines())

        # compute references: set references to the parent and add current message just to
        # have a fallback in case replies mess with Messsage-Id in the In-Reply-To (e.g. amazon
        # SES SMTP may replace Message-Id and In-Reply-To refers an internal ID not stored in Odoo)
        message_sudo = message.sudo()
        if message_sudo.parent_id:
            references = f'{message_sudo.parent_id.message_id} {message_sudo.message_id}'
        else:
            references = message_sudo.message_id
        # prepare notification mail values
        base_mail_values = {
            'mail_message_id': message.id,
            'references': references,
        }
        if mail_subject != message.subject:
            base_mail_values['subject'] = mail_subject
        if additional_values:
            base_mail_values.update(additional_values)

        # prepare headers (as sudo as accessing mail.alias.domain, restricted)
        headers = {}
        if message_sudo.record_alias_domain_id.bounce_email:
            headers['Return-Path'] = message_sudo.record_alias_domain_id.bounce_email
        headers = self._notify_by_email_get_headers(headers=headers)
        if headers:
            base_mail_values['headers'] = repr(headers)
        return base_mail_values

    def _notify_by_email_get_final_mail_values(self, recipient_ids, mail_values,
                                               additional_values=None):
        """ Perform final formatting of values to create notification emails.
        Basic method just set the recipient partners as mail_mail recipients.
        Override to generate other mail values like email_to or email_cc.

        :param list recipient_ids: res.partner IDs to notify;
        :param dict mail_values: notification mail values;
        :param dict additional_values: optional additional values to add (ease
          custom calls and inheritance);

        :return: a new dictionary of values suitable for a <mail.mail> create;
        """
        final_mail_values = dict(mail_values)
        final_mail_values['recipient_ids'] = [Command.link(pid) for pid in recipient_ids]
        if additional_values:
            final_mail_values.update(additional_values)
        return final_mail_values

    def _notify_thread_by_web_push(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Method to send cloud notifications for every mention of a partner
        and every direct message. We have to take into account the risk of
        duplicated notifications in case of a mention in a channel of `chat` type.

        :param message: ``mail.message`` record to notify;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param msg_vals: dictionary of values used to create the message. If given it
          may be used to access values related to ``message`` without accessing it
          directly. It lessens query count in some optimized use cases by avoiding
          access message content in db;
        """
        partner_ids = self._notify_get_recipients_for_extra_notifications(message, recipients_data, msg_vals=msg_vals)
        devices, private_key, public_key = self._web_push_get_partners_parameters(partner_ids)
        if not devices:
            return
        payload = self._web_push_truncate_payload(self._notify_by_web_push_prepare_payload(message, msg_vals=msg_vals))
        self._web_push_send_notification(devices, private_key, public_key, payload=payload)

    def _web_push_get_partners_parameters(self, partner_ids):
        """
        :param partner_ids: IDs of the res.partners
        :returns: the `mail.push.device` records, the vapid private key and the vapid public key
        """
        devices_su = self.env["mail.push.device"].sudo()
        if not partner_ids:
            return devices_su, None, None
        vapid_private_key = self.env["ir.config_parameter"].sudo().get_param("mail.web_push_vapid_private_key")
        vapid_public_key = self.env["ir.config_parameter"].sudo().get_param("mail.web_push_vapid_public_key")
        if not vapid_private_key or not vapid_public_key:
            return devices_su, None, None
        return devices_su.search([("partner_id", "in", partner_ids)]), vapid_private_key, vapid_public_key

    def _web_push_send_notification(self, devices, private_key, public_key, payload_by_lang=None, payload=None):
        """
        :param payload: JSON serializable dict following the notification api specs https://notifications.spec.whatwg.org/#api
        :param payload_by_lang a dict mapping payload by lang, either this or payload must be provided
        """
        if len(devices) < MAX_DIRECT_PUSH:
            session = Session()
            devices_to_unlink = set()
            for device in devices:
                try:
                    push_to_end_point(
                        base_url=self.get_base_url(),
                        device={
                            'id': device.id,
                            'endpoint': device.endpoint,
                            'keys': device.keys
                        },
                        payload=json.dumps(payload_by_lang and payload_by_lang[device.partner_id.lang] or payload),
                        vapid_private_key=private_key,
                        vapid_public_key=public_key,
                        session=session,
                    )
                except DeviceUnreachableError:
                    devices_to_unlink.add(device.id)
                except Exception as e:  # pylint: disable=broad-except
                    # Avoid blocking the whole request just for a notification
                    _logger.error('An error occurred while contacting the endpoint: %s', e)

            # clean up obsolete devices
            if devices_to_unlink:
                devices_list = list(devices_to_unlink)
                self.env['mail.push.device'].sudo().browse(devices_list).unlink()

        else:
            self.env['mail.push'].sudo().create([{
                'mail_push_device_id': device.id,
                'payload': json.dumps(payload_by_lang and payload_by_lang[device.partner_id.lang] or payload),
            } for device in devices])
            self.env.ref('mail.ir_cron_web_push_notification')._trigger()

    def _notify_by_web_push_prepare_payload(self, message, msg_vals=False):
        """ Returns dictionary containing message information for a browser device.
        This info will be delivered to a browser device via its recorded endpoint.
        REM: It is having a limit of 4000 bytes (4kb)
        """
        msg_vals = msg_vals or {}
        author_id = msg_vals['author_id'] if 'author_id' in msg_vals else message.author_id.id
        model = msg_vals['model'] if 'model' in msg_vals else message.model
        title = msg_vals['record_name'] if 'record_name' in msg_vals else message.model
        res_id = msg_vals['res_id'] if 'res_id' in msg_vals else message.res_id
        body = msg_vals['body'] if 'body' in msg_vals else message.body
        if not model and body:
            model, res_id = self._extract_model_and_id(body)

        if author_id:
            author_name = self.env['res.partner'].browse(author_id).name
            title = "%s: %s" % (author_name, title)
            icon = "/web/image/res.partner/%d/avatar_128" % author_id
        else:
            icon = '/web/static/img/odoo-icon-192x192.png'

        return {
            'title': title,
            'options': {
                'body': html2plaintext(body) + self._generate_tracking_message(message),
                'icon': icon,
                'data': {
                    'model': model if model else '',
                    'res_id': res_id if res_id else '',
                }
            }
        }

    def _notify_get_recipients(self, message, msg_vals=False, **kwargs):
        """ Compute recipients to notify based on subtype and followers. This
        method returns data structured as expected for ``_notify_recipients``.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        Kwargs allow to pass various parameters that are used by sub notification
        methods. See those methods for more details about supported parameters.
        Specific kwargs used in this method:

          * ``notify_author``: allows to notify the author, which is False by
            default as we don't want people to receive their own content. It is
            used notably when impersonating partners or having automated
            notifications send by current user, targeting current user;
          * ``skip_existing``: check existing notifications and skip them in order
            to avoid having several notifications / partner as it would make
            constraints crash. This is disabled by default to optimize speed;

        TDE/XDO TODO: flag rdata directly, for example r['notif'] = 'ocn_client'
        and r['needaction']=False and correctly override _notify_get_recipients

        :return list recipients_data: list of recipients information (see
          ``MailFollowers._get_recipient_data()`` for more details) formatted
          like [
          {
            'active': partner.active;
            'email_normalized': partner.email_normalized;
            'id': id of the res.partner being recipient to notify;
            'is_follower': follows the message related document;
            'name': partner name;
            'lang': partner lang;
            'groups': res.group IDs if linked to a user;
            'notif': notification type, one of 'inbox', 'email', 'sms' (SMS App),
                'whatsapp (WhatsAapp);
            'share': is partner a customer (partner.partner_share);
            'type': partner usage ('customer', 'portal', 'user');
            'uid': user ID (in case of multiple users, internal then first found
                by ID);)
            'ushare': are users shared (if users, all users are shared);
          }, {...}]
        """
        msg_vals = msg_vals or {}
        msg_sudo = message.sudo()

        # get values from msg_vals or from message if msg_vals doen't exists
        pids = msg_vals['partner_ids'] if 'partner_ids' in msg_vals else msg_sudo.partner_ids.ids
        message_type = msg_vals['message_type'] if 'message_type' in msg_vals else msg_sudo.message_type
        subtype_id = msg_vals['subtype_id'] if 'subtype_id' in msg_vals else msg_sudo.subtype_id.id
        # is it possible to have record but no subtype_id ?
        recipients_data = []

        res = self.env['mail.followers']._get_recipient_data(self, message_type, subtype_id, pids)[self.id if self else 0]
        if not res:
            return recipients_data

        # notify author of its own messages, False by default
        notify_author = kwargs.get('notify_author') or self.env.context.get('mail_notify_author')
        real_author_id = False
        if not notify_author:
            if self.env.user.active:
                real_author_id = self.env.user.partner_id.id
            elif msg_vals.get('author_id'):
                real_author_id = msg_vals['author_id']
            else:
                real_author_id = message.author_id.id

        for pid, pdata in res.items():
            if pid and pid == real_author_id:
                continue
            if pdata['active'] is False:
                continue
            recipients_data.append(pdata)

        # avoid double notification (on demand due to additional queries)
        if kwargs.pop('skip_existing', False):
            pids = [r['id'] for r in recipients_data if r['id']]
            if pids:
                existing_notifications = self.env['mail.notification'].sudo().search([
                    ('res_partner_id', 'in', pids),
                    ('mail_message_id', 'in', message.ids)
                ])
                recipients_data = [
                    r for r in recipients_data
                    if r['id'] not in existing_notifications.res_partner_id.ids
                ]

        return recipients_data

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        """ Return groups used to classify recipients of a notification email.
        Groups is a list of tuple (group_name, group_func, group_data) where

         * 'group_name' is an identifier used only to be able to override and
           manipulate groups;
         * 'group_func' is a function pointer taking a partner data dict as
           parameter. It is called on recipients to know if they belong to
           the group. Only first matching group is kept, iterating on the
           group list in order.
         * 'group_data' is a dict containing parameters used in notification
           process like {
            'active': if not, it is skipped in notification process (ease
                      inheritance to be already present);
            'button_access': main access document button information, {'url'
                             link of the access, 'title': link or button
                             string};
            'has_button_access': display access document main button in email;
            'notification_group_name': name of the group, to ease usage;
            'recipients_data': list of recipients data, following format used
                               in '_notify_get_recipients'. It is fillup when
                               evaluating groups;
            'recipients_ids': list of partner IDs, based on partner ID present in
                              recipients_data (allows mainly to speedup some
                              data computation);
           }

        Default groups:

          * 'user': recipients linked to an internal user;
          * 'portal': recipients linked to a portal user;
          * 'follower': recipients (not internal/portal users) follower of the
            related record;
          * 'customer': other recipients (always partners);

        When having to find a group for recipients, the first matching one
        when iterating on groups is used. Reordering those groups is doable
        through override. Adding groups is a common override, to add specific
        buttons for users belonging to some user groups.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :return: list of groups definition
        """
        return [
            [
                'user',
                lambda pdata: pdata['type'] == 'user',
                {
                    'active': True,
                    'has_button_access': self.env['mail.message']._is_thread_message(vals=msg_vals, thread=self),
                }
            ], [
                'portal',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'follower',
                lambda pdata: pdata['is_follower'],
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'customer',
                lambda pdata: True,
                {
                    'active': True,
                    'has_button_access': False,
                }
            ],
        ]

    def _notify_get_recipients_groups_fillup(self, groups, model_description, msg_vals=False):
        """ Iterate on recipients groups (see '_notify_get_recipients_groups')
        and fill up the result with default values, allowing to compute links or
        titles once.

        :param list groups: recipients groups;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;

        :return: updated groups;
        """
        access_link = self._notify_get_action_link('view', **msg_vals)

        if model_description:
            view_title = _('View %s', model_description)
        else:
            view_title = _('View')

        is_thread_message = self.env['mail.message']._is_thread_message(vals=msg_vals, thread=self)

        # fill group_data with default_values if they are not complete
        for group_name, _group_func, group_data in groups:
            group_data.setdefault('active', True)
            group_data.setdefault('has_button_access', is_thread_message)
            group_data.setdefault('notification_group_name', group_name)
            group_data.setdefault('recipients_data', [])
            group_data.setdefault('recipients_ids', [])
            group_button_access = group_data.setdefault('button_access', {})
            group_button_access.setdefault('url', access_link)
            group_button_access.setdefault('title', view_title)

        return groups

    def _notify_get_recipients_classify(self, message, recipients_data,
                                        model_description, msg_vals=False):
        """ Classify recipients to be notified of a message in groups to have
        specific rendering depending on their group. For example users could
        have access to buttons customers should not have in their emails.
        Module-specific grouping should be done by overriding ``_notify_get_recipients_groups``
        method defined here-under.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :return list: list of groups (see '_notify_get_recipients_groups')
          with 'recipients' key filled with matching partners, like
            [{
                'active': True,
                'button_access': {'url': 'https://odoo.com/url', 'title': 'Title'},
                'has_button_access': False,
                'notification_group_name': 'user',
                'recipients_data': [{...}],
                'recipients_ids': [11],
             }, {...}]
        """
        # keep a local copy of msg_vals as it may be modified to include more
        # information about groups or links
        local_msg_vals = dict(msg_vals) if msg_vals else {}
        groups = self._notify_get_recipients_groups_fillup(
            self._notify_get_recipients_groups(
                message, model_description, msg_vals=local_msg_vals
            ),
            model_description,
            msg_vals=local_msg_vals
        )
        # sanitize groups
        for _group_name, _group_func, group_data in groups:
            if 'actions' in group_data:
                _logger.warning('Invalid usage of actions in notification groups')

        # classify recipients in each group
        for recipient_data in recipients_data:
            for _group_name, group_func, group_data in groups:
                if group_data['active'] and group_func(recipient_data):
                    group_data['recipients_data'].append(recipient_data)
                    if recipient_data['id']:
                        group_data['recipients_ids'].append(recipient_data['id'])
                    break

        # filter out groups without recipients
        return [
            group_data
            for _group_name, _group_func, group_data in groups
            if group_data['recipients_data']
        ]

    def _notify_get_recipients_for_extra_notifications(self, message, recipients_data, msg_vals=False):
        """ Never send to author and to people outside Odoo (email) except comments """
        notif_pids = []
        notif_pids_notinbox = []
        for recipient in (r for r in recipients_data if r['active'] and r['id']):
            notif_pids.append(recipient['id'])
            if recipient['notif'] != 'inbox':
                notif_pids_notinbox.append(recipient['id'])
        if not notif_pids:
            return []

        msg_vals = msg_vals or {}
        msg_type = msg_vals.get('message_type') or message.sudo().message_type
        author_ids = [msg_vals.get('author_id') or message.sudo().author_id.id]
        if msg_type in {'comment', 'whatsapp_message'}:
            return set(notif_pids) - set(author_ids)
        elif msg_type in ('notification', 'user_notification', 'email'):
            return (set(notif_pids) - set(author_ids) - set(notif_pids_notinbox))
        return []

    def _notify_get_action_link(self, link_type, **kwargs):
        """ Prepare link to an action: view document, follow document, ... """
        params = {
            'model': kwargs.get('model', self._name),
            'res_id': kwargs.get('res_id', self.ids and self.ids[0] or False),
        }
        # keep only accepted parameters:
        # - action (deprecated), token (assign), access_token (view)
        # - auth_signup: auth_signup_token and auth_login
        # - portal: pid, hash
        params.update(dict(
            (key, value)
            for key, value in kwargs.items()
            if key in ('action', 'token', 'access_token', 'auth_signup_token',
                       'auth_login', 'pid', 'hash')
        ))

        if link_type in ['view', 'unfollow']:
            base_link = '/mail/%s' % link_type
        elif link_type == 'controller':
            controller = kwargs.get('controller')
            params.pop('model')
            base_link = '%s' % controller
        else:
            raise NotImplementedError(f'Invalid notification link type {link_type}')

        if link_type not in ['view']:
            token = self._encode_link(base_link, params)
            params['token'] = token

        link = '%s?%s' % (base_link, urls.url_encode(params, sort=True))
        if self:
            link = self[0].get_base_url() + link

        return link

    # Notify tools and helpers
    # ------------------------------------------------------------

    @api.model
    def _encode_link(self, base_link, params):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params)))
        hm = hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha1).hexdigest()
        return hm

    @api.model
    def _extract_model_and_id(self, html_content):
        """
        Return the model and the id when is present in a link (HTML)
        :param msg_vals: see :meth:`._notify_thread_by_web_push`
        :return: a dict empty if no matches and a dict with these keys if match : model and res_id
        """
        regex = r"<a.+model=(?P<model>[\w.]+).+res_id=(?P<id>\d+).+>[\s\w\/\\.]+<\/a>"
        matches = re.finditer(regex, html_content)

        for match in matches:
            return match['model'], match['id']
        return None, None

    @api.model
    def _generate_tracking_message(self, message, return_line='\n'):
        """
        Format the tracking values like in the chatter
        :param message: current mail.message record
        :param return_line: type of return line
        :return: a string with the new text if there is one or more tracking value
        """
        tracking_message = ''
        if message.subtype_id and message.subtype_id.description:
            tracking_message = return_line + message.subtype_id.description + return_line

        for tracking in message.sudo().tracking_value_ids._filter_free_field_access():
            if tracking.field_id.ttype == 'boolean':
                old_value = str(bool(tracking.old_value_integer))
                new_value = str(bool(tracking.new_value_integer))
            else:
                old_value = tracking.old_value_char or str(tracking.old_value_integer)
                new_value = tracking.new_value_char or str(tracking.new_value_integer)

            tracking_message += tracking.field_id.field_description + ': ' + old_value
            if old_value != new_value:
                tracking_message += ' → ' + new_value
            tracking_message += return_line

        return tracking_message

    @api.model
    def _get_model_description(self, model_name):
        if not model_name:
            return False
        if not 'lang' in self.env.context:
            raise ValueError(_('At this point lang should be correctly set'))
        return self.env['ir.model']._get(model_name).display_name  # one query for display name

    @api.model
    def _web_push_truncate_payload(self, payload):
        """ Truncate body at 4096 bytes to avoid 413 error return code.
        :param dict payload: Current payload to trunc
        :return: The truncate payload;
        """
        payload_length = len(str(payload).encode())
        body = payload['options']['body']
        body_length = len(body)
        if payload_length > 4096:
            body_max_length = 4096 - payload_length - body_length
            payload['options']['body'] = body.encode()[:body_max_length].decode(errors="ignore")
        return payload

    # ------------------------------------------------------
    # FOLLOWERS API
    # ------------------------------------------------------

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        """ Main public API to add followers to a record set. Its main purpose is
        to perform access rights checks before calling ``_message_subscribe``. """
        if not self or not partner_ids:
            return True

        partner_ids = partner_ids or []
        adding_current = set(partner_ids) == set([self.env.user.partner_id.id])
        customer_ids = [] if adding_current else None

        if partner_ids and adding_current:
            try:
                self.check_access('read')
            except exceptions.AccessError:
                return False
        else:
            self.check_access('write')

        # filter inactive and private addresses
        if partner_ids and not adding_current:
            partner_ids = self.env['res.partner'].sudo().search([('id', 'in', partner_ids), ('active', '=', True)]).ids

        return self._message_subscribe(partner_ids, subtype_ids, customer_ids=customer_ids)

    def _message_subscribe(self, partner_ids=None, subtype_ids=None, customer_ids=None):
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
                self._name, self.ids,
                partner_ids, subtypes=None,
                customer_ids=customer_ids, check_existing=True, existing_policy='skip')
        else:
            self.env['mail.followers']._insert_followers(
                self._name, self.ids,
                partner_ids, subtypes=dict((pid, subtype_ids) for pid in partner_ids),
                customer_ids=customer_ids, check_existing=True, existing_policy='replace')

        return True

    def message_unsubscribe(self, partner_ids=None):
        """ Remove partners from the records followers. """
        # not necessary for computation, but saves an access right check
        if not partner_ids:
            return True
        # To support unfollowing a document in the inbox no matter the current
        # company, we allow internal users to unsubscribe themselves without
        # checking any rights.
        if set(partner_ids) != {self.env.user.partner_id.id}:
            self.check_access('write')
        elif not self.env.user._is_internal():
            self.check_access('read')
        self.env['mail.followers'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('partner_id', 'in', partner_ids),
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
        with tracking set. It is considered as being
        responsible for the document and therefore standard behavior is to
        subscribe the user and send them a notification.

        Override this method to change that behavior and/or to add people to
        notify, using possible custom notification.

        :param updated_values: see ``_message_auto_subscribe``
        :param default_subtype_ids: coming from ``_get_auto_subscription_subtypes``
        """
        fnames = []
        field = self._fields.get('user_id')
        user_id = updated_values.get('user_id')
        if field and user_id and field.comodel_name == 'res.users' and getattr(field, 'tracking', False):
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

        for record in self:
            model_description = self.env['ir.model']._get(record._name).display_name
            company = record.company_id.sudo() if 'company_id' in record else self.env.company
            values = {
                'access_link': record._notify_get_action_link('view'),
                'company': company,
                'model_description': model_description,
                'object': record,
            }
            assignation_msg = self.env['ir.qweb']._render(template, values, minimal_qcontext=True)
            assignation_msg = self.env['mail.render.mixin']._replace_local_links(assignation_msg)
            record.message_notify(
                subject=_('You have been assigned to %s', record.display_name),
                body=assignation_msg,
                partner_ids=partner_ids,
                record_name=record.display_name,
                email_layout_xmlid='mail.mail_notification_layout',
                model_description=model_description,
            )

    def _message_auto_subscribe(self, updated_values, followers_existing_policy='skip'):
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

        new_partner_subtypes = dict()

        # return data related to auto subscription based on subtype matching (aka:
        # default task subtypes or subtypes from project triggering task subtypes)
        updated_relation = dict()
        child_ids, def_ids, all_int_ids, parent, relation = self.env['mail.message.subtype']._get_auto_subscription_subtypes(self._name)

        # check effectively modified relation field
        for res_model, fnames in relation.items():
            for field in (fname for fname in fnames if updated_values.get(fname)):
                updated_relation.setdefault(res_model, set()).add(field)
        udpated_fields = [fname for fnames in updated_relation.values() for fname in fnames if updated_values.get(fname)]

        if udpated_fields:
            # fetch "parent" subscription data (aka: subtypes on project to propagate on task)
            doc_data = [(model, [updated_values[fname] for fname in fnames]) for model, fnames in updated_relation.items()]
            res = self.env['mail.followers']._get_subscription_data(doc_data, None, include_pshare=True, include_active=True)
            for _fol_id, _res_id, partner_id, subtype_ids, pshare, active in res:
                # use project.task_new -> task.new link
                sids = [parent[sid] for sid in subtype_ids if parent.get(sid)]
                # add checked subtypes matching model_name
                sids += [sid for sid in subtype_ids if sid not in parent and sid in child_ids]
                if partner_id and active:  # auto subscribe only active partners
                    if pshare:  # remove internal subtypes for customers
                        new_partner_subtypes[partner_id] = set(sids) - set(all_int_ids)
                    else:
                        new_partner_subtypes[partner_id] = set(sids)

        notify_data = dict()
        res = self._message_auto_subscribe_followers(updated_values, def_ids)
        for partner_id, sids, template in res:
            new_partner_subtypes.setdefault(partner_id, sids)
            if template:
                partner = self.env['res.partner'].browse(partner_id)
                lang = partner.lang if partner else None
                notify_data.setdefault((template, lang), list()).append(partner_id)

        self.env['mail.followers']._insert_followers(
            self._name, self.ids,
            list(new_partner_subtypes), subtypes=new_partner_subtypes,
            check_existing=True, existing_policy=followers_existing_policy)

        # notify people from auto subscription, for example like assignation
        for (template, lang), pids in notify_data.items():
            self.with_context(lang=lang)._message_auto_subscribe_notify(pids, template)

        return True

    @api.readonly
    def message_get_followers(self, after=None, limit=100, filter_recipients=False):
        self.ensure_one()
        store = Store()
        self._message_followers_to_store(store, after, limit, filter_recipients)
        return store.get_result()

    def _message_followers_to_store(self, store: Store, after=None, limit=100, filter_recipients=False, reset=False):
        self.ensure_one()
        domain = [
            ("res_id", "=", self.id),
            ("res_model", "=", self._name),
            ("partner_id", "!=", self.env.user.partner_id.id),
        ]
        if filter_recipients:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
            subtype_domain = [
                ("subtype_ids", "=", subtype_id),
                ("partner_id.active", "=", True),
            ]
            domain = expression.AND([domain, subtype_domain])
        if after:
            domain = expression.AND([domain, [("id", ">", after)]])
        store.add(
            self,
            {
                "recipients" if filter_recipients else "followers": Store.Many(
                    self.env["mail.followers"].search(domain, limit=limit, order="id ASC"),
                    mode="ADD" if not reset else "REPLACE",
                ),
            },
            as_thread=True,
        )

    # ------------------------------------------------------
    # THREAD MESSAGE UPDATE
    # ------------------------------------------------------

    def message_change_thread(self, new_thread, new_parent_message=False):
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
        subtype_comment = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

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
        msg_vals = {"res_id": new_thread.id, "model": new_thread._name}
        if new_parent_message:
            msg_vals["parent_id"] = new_parent_message.id
        msg_comment.sudo().write(msg_vals)

        # other than comment: reset subtype
        msg_vals["subtype_id"] = None
        msg_not_comment.sudo().write(msg_vals)
        return True

    def _message_update_content(self, message, body, attachment_ids=None, partner_ids=None,
                                strict=True, **kwargs):
        """ Update message content. Currently does not support attachments
        specific code (see ``_process_attachments_for_post``), to be added
        when necessary.

        Private method to use for tooling, do not expose to interface as editing
        messages should be avoided at all costs (think of: notifications already
        sent, ...).

        :param <mail.message> message: message to update, should be linked to self through
          model and res_id;
        :param str body: new body (None to skip its update);
        :param list attachment_ids: list of new attachments IDs, replacing old one (None
          to skip its update);
        :param list attachment_ids: list of new partner IDs that are mentioned;
        :param bool strict: whether to check for allowance before updating
          content. This should be skipped only when really necessary as it
          creates issues with already-sent notifications, lack of content
          tracking, ...

        Kwargs are supported, notably to match mail.message fields to update.
        See content of this method for more details about supported keys.
        """
        self.ensure_one()
        if strict:
            self._check_can_update_message_content(message.sudo())

        msg_values = {}
        if body is not None:
            msg_values["body"] = (
                # keep html if already Markup, otherwise escape
                escape(body) + Markup("<span class='o-mail-Message-edited'/>")
                if body or not message._filter_empty()
                else ""
            )
        if attachment_ids:
            msg_values.update(
                self._process_attachments_for_post([], attachment_ids, {
                    'body': body,
                    'model': self._name,
                    'res_id': self.id,
                })
            )
        elif attachment_ids is not None:  # None means "no update"
            message.attachment_ids._delete_and_notify()
        if partner_ids:
            msg_values.update({
                'partner_ids': list(partner_ids or [])
            })
        if msg_values:
            message.write(msg_values)

        if 'scheduled_date' in kwargs:
            # update scheduled datetime
            if kwargs['scheduled_date']:
                self.env['mail.message.schedule'].sudo()._update_message_scheduled_datetime(
                    message,
                    kwargs['scheduled_date']
                )
            # (re)send notifications
            else:
                self.env['mail.message.schedule'].sudo()._send_message_notifications(message)

        # cleanup related message data if the message is empty
        empty_messages = message.sudo()._filter_empty()
        empty_messages._cleanup_side_records()
        empty_messages.write({'pinned_at': None})
        res = [
            Store.Many("attachment_ids", sort="id"),
            "body",
            Store.Many("partner_ids", ["name", "write_date"], rename="recipients"),
            "pinned_at",
            "write_date",
        ]
        if body is not None:
            # sudo: mail.message.translation - discarding translations of message after editing it
            self.env["mail.message.translation"].sudo().search([("message_id", "=", message.id)]).unlink()
            res.append({"translationValue": False})
        message._bus_send_store(message, res)

    # ------------------------------------------------------
    # STORE
    # ------------------------------------------------------

    def _thread_to_store(self, store: Store, fields, *, request_list=None):
        store.add_records_fields(self, fields, as_thread=True)
        for thread in self:
            res = {}
            if request_list:
                res["hasReadAccess"] = True
                res["hasWriteAccess"] = False
                res["canPostOnReadonly"] = self._mail_post_access == "read"
                try:
                    thread.check_access("write")
                    res["hasWriteAccess"] = True
                except AccessError:
                    pass
            if (
                request_list
                and "activities" in request_list
                and isinstance(self.env[self._name], self.env.registry["mail.activity.mixin"])
            ):
                res["activities"] = Store.Many(thread.with_context(active_test=True).activity_ids)
            if request_list and "attachments" in request_list:
                res["attachments"] = Store.Many(thread._get_mail_thread_data_attachments())
                res["areAttachmentsLoaded"] = True
                res["isLoadingAttachments"] = False
            if request_list and "followers" in request_list:
                res["followersCount"] = self.env["mail.followers"].search_count(
                    [("res_id", "=", thread.id), ("res_model", "=", self._name)]
                )
                self_follower = self.env["mail.followers"].search(
                    [
                        ("res_id", "=", thread.id),
                        ("res_model", "=", self._name),
                        ["partner_id", "=", self.env.user.partner_id.id],
                    ]
                )
                res["selfFollower"] = Store.One(self_follower)
                thread._message_followers_to_store(store, reset=True)
                subtype_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment")
                res["recipientsCount"] = self.env["mail.followers"].search_count(
                    [
                        ("res_id", "=", thread.id),
                        ("res_model", "=", self._name),
                        ("partner_id", "!=", self.env.user.partner_id.id),
                        ("subtype_ids", "=", subtype_id),
                        ("partner_id.active", "=", True),
                    ]
                )
                thread._message_followers_to_store(store, filter_recipients=True, reset=True)
            if request_list and "scheduledMessages" in request_list:
                res["scheduledMessages"] = Store.Many(self.env['mail.scheduled.message'].search([
                    ['model', '=', self._name], ['res_id', '=', thread.id]
                ]))
            if request_list and "suggestedRecipients" in request_list:
                res["suggestedRecipients"] = thread._message_get_suggested_recipients()
            if res:
                store.add(thread, res, as_thread=True)

    def _get_mail_thread_data_attachments(self):
        self.ensure_one()
        res = self.env['ir.attachment'].search([('res_id', '=', self.id), ('res_model', '=', self._name)], order='id desc')
        if 'original_id' in self.env['ir.attachment']._fields:
            # If the image is SVG: We take the png version if exist otherwise we take the svg
            # If the image is not SVG: We take the original one if exist otherwise we take it
            svg_ids = res.filtered(lambda attachment: attachment.mimetype == 'image/svg+xml')
            non_svg_ids = res - svg_ids
            original_ids = res.mapped('original_id')
            res = res.filtered(lambda attachment: (attachment in svg_ids and attachment not in original_ids) or (attachment in non_svg_ids and attachment.original_id not in non_svg_ids))
        return res

    # ------------------------------------------------------
    # CONTROLLERS SECURITY HELPERS
    # ------------------------------------------------------

    def _get_allowed_message_post_params(self):
        return {"attachment_ids", "body", "email_add_signature", "message_type", "partner_ids", "subtype_xmlid"}

    @api.model
    def _get_thread_with_access(self, thread_id, mode="read", **kwargs):
        thread = self.browse(thread_id)
        if thread.exists() and thread.sudo(False).has_access(mode):
            return thread
        return self.browse()
