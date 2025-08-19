# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import contextlib
import logging
import re
import textwrap
from binascii import Error as binascii_error
from collections import defaultdict
from lxml import html

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Command, Domain
from odoo.tools import clean_context, groupby, SQL
from odoo.tools.misc import OrderedSet
from odoo.addons.mail.tools.discuss import Store

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/\n]{3,}=*)\n*([\'"])(?: data-filename="([^"]*)")?', re.I)


class MailMessage(models.Model):
    """ Message model (from notifications to user input).

    Note:: State management / Error codes / Failure types summary

    * mail.notification
      * notification_status
        'ready', 'sent', 'bounce', 'exception', 'canceled'
      * notification_type
        'inbox', 'email', 'sms' (SMS addon), 'snail' (snailmail addon)
      * failure_type
        # generic
        unknown,
        # mail
        "mail_email_invalid", "mail_smtp", "mail_email_missing",
        "mail_from_invalid", "mail_from_missing",
        # sms (SMS addon)
        'sms_number_missing', 'sms_number_format', 'sms_credit',
        'sms_server', 'sms_acc'
        # snailmail (snailmail addon)
        'sn_credit', 'sn_trial', 'sn_price', 'sn_fields',
        'sn_format', 'sn_error'

    * mail.mail
      * state
        'outgoing', 'sent', 'received', 'exception', 'cancel'
      * failure_reason: text

    * sms.sms (SMS addon)
      * state
        'outgoing', 'sent', 'error', 'canceled'
      * error_code
        'sms_number_missing', 'sms_number_format', 'sms_credit',
        'sms_server', 'sms_acc',
        # mass mode specific codes
        'sms_blacklist', 'sms_duplicate'

    * snailmail.letter (snailmail addon)
      * state
        'pending', 'sent', 'error', 'canceled'
      * error_code
        'CREDIT_ERROR', 'TRIAL_ERROR', 'NO_PRICE_AVAILABLE', 'FORMAT_ERROR',
        'UNKNOWN_ERROR',

    See ``mailing.trace`` model in mass_mailing application for mailing trace
    information.
    """
    _name = 'mail.message'
    _inherit = ["bus.listener.mixin"]
    _description = 'Message'
    _order = 'id desc'
    _rec_name = 'subject'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        missing_author = 'author_id' in fields and 'author_id' not in res
        missing_email_from = 'email_from' in fields and 'email_from' not in res
        if missing_author or missing_email_from:
            author_id, email_from = self.env['mail.thread']._message_compute_author(res.get('author_id'), res.get('email_from'), raise_on_email=False)
            if missing_email_from:
                res['email_from'] = email_from
            if missing_author:
                res['author_id'] = author_id
        return res

    # content
    subject = fields.Char('Subject')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    body = fields.Html('Contents', default='', sanitize_style=True)
    preview = fields.Char(
        'Preview', compute='_compute_preview',
        help='The text-only beginning of the body used as email preview.')
    linked_message_ids = fields.Many2many("mail.message", compute="_compute_linked_message_ids")
    message_link_preview_ids = fields.One2many(
        "mail.message.link.preview", "message_id", groups="base.group_erp_manager"
    )
    reaction_ids = fields.One2many(
        'mail.message.reaction', 'message_id', string="Reactions",
        groups="base.group_system")
    # Attachments are linked to a document through model / res_id and to the message through this field.
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id',
        string='Attachments')
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', index='btree_not_null', ondelete='set null')
    child_ids = fields.One2many('mail.message', 'parent_id', 'Child Messages')
    # related document
    model = fields.Char('Related Document Model')
    res_id = fields.Many2oneReference('Related Document ID', model_field='model')
    record_name = fields.Char('Message Record Name', compute='_compute_record_name', store=False)
    record_alias_domain_id = fields.Many2one('mail.alias.domain', 'Alias Domain', ondelete='set null')
    record_company_id = fields.Many2one('res.company', 'Company', ondelete='set null')
    # characteristics
    message_type = fields.Selection([
        ('email', 'Incoming Email'),
        ('comment', 'Comment'),
        ('email_outgoing', 'Outgoing Email'),
        ('notification', 'System notification'),
        ('auto_comment', 'Automated Targeted Notification'),
        ('user_notification', 'User Specific Notification')],
        'Type', required=True, default='comment',
        help="Used to categorize message generator"
             "\n'email': generated by an incoming email e.g. mailgateway"
             "\n'comment': generated by user input e.g. through discuss or composer"
             "\n'email_outgoing': generated by a mailing"
             "\n'notification': generated by system e.g. tracking messages"
             "\n'auto_comment': generated by automated notification mechanism e.g. acknowledgment"
             "\n'user_notification': generated for a specific recipient"
        )
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', ondelete='set null', index=True)
    mail_activity_type_id = fields.Many2one(
        'mail.activity.type', 'Mail Activity Type',
        index='btree_not_null', ondelete='set null')
    is_internal = fields.Boolean('Employee Only', help='Hide to public / portal users, independently from subtype configuration.')
    # origin
    email_from = fields.Char('From', help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True, ondelete='set null',
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.avatar_128', depends=['author_id'], readonly=False)
    author_guest_id = fields.Many2one(string="Guest", comodel_name='mail.guest')
    is_current_user_or_guest_author = fields.Boolean(compute='_compute_is_current_user_or_guest_author')
    # recipients: include inactive partners (they may have been archived after
    # the message was sent, but they should remain visible in the relation)
    partner_ids = fields.Many2many('res.partner', string='Recipients', context={'active_test': False})
    # email recipients of incoming emails: comma separated list of emails (not necessarily normalized)
    incoming_email_to = fields.Text('Emails To')
    incoming_email_cc = fields.Char('Emails Cc')
    # list of partner having a notification. Caution: list may change over time because of notif gc cron.
    # mainly usefull for testing
    notified_partner_ids = fields.Many2many(
        'res.partner', 'mail_notification', string='Partners with Need Action',
        context={'active_test': False}, depends=['notification_ids'], copy=False)
    needaction = fields.Boolean(
        'Need Action', compute='_compute_needaction', search='_search_needaction')
    has_error = fields.Boolean(
        'Has error', compute='_compute_has_error', search='_search_has_error')
    # notifications
    notification_ids = fields.One2many(
        'mail.notification', 'mail_message_id', 'Notifications',
        bypass_search_access=True, copy=False, depends=['notified_partner_ids'])
    # user interface
    starred_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_starred_rel', string='Favorited By')
    pinned_at = fields.Datetime('Pinned', help='Datetime at which the message has been pinned')
    starred = fields.Boolean(
        'Starred', compute='_compute_starred', search='_search_starred', compute_sudo=False,
        help='Current user has a starred notification linked to this message')
    # tracking
    tracking_value_ids = fields.One2many(
        'mail.tracking.value', 'mail_message_id',
        string='Tracking values',
        groups="base.group_system",
        help='Tracked values are stored in a separate model. This field allow to reconstruct '
             'the tracking and to generate statistics on the model.')
    # mail gateway
    reply_to_force_new = fields.Boolean(
        'No threading for answers',
        help='If true, answers do not go in the original document discussion thread. Instead, it will check for the reply_to in tracking message-id and redirected accordingly. This has an impact on the generated message-id.')
    message_id = fields.Char('Message-Id', help='Message unique identifier', index='btree', readonly=True, copy=False)
    reply_to = fields.Char('Reply-To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    # send notification information (for resend / reschedule)
    email_layout_xmlid = fields.Char('Layout', copy=False)  # xml id of layout
    email_add_signature = fields.Boolean(default=True)
    # `test_adv_activity`, `test_adv_activity_full`, `test_message_assignation_inbox`,...
    # By setting an inverse for mail.mail_message_id, the number of SQL queries done by `modified` is reduced.
    # 'mail.mail' inherits from `mail.message`: `_inherits = {'mail.message': 'mail_message_id'}`
    # Therefore, when changing a field on `mail.message`, this triggers the modification of the same field on `mail.mail`
    # By setting up the inverse one2many, we avoid to have to do a search to find the mails linked to the `mail.message`
    # as the cache value for this inverse one2many is up-to-date.
    # Besides for new messages, and messages never sending emails, there was no mail, and it was searching for nothing.
    mail_ids = fields.One2many('mail.mail', 'mail_message_id', string='Mails', groups="base.group_system")

    _model_res_id_idx = models.Index("(model, res_id)")
    _model_res_id_id_idx = models.Index("(model, res_id, id)")

    @api.depends('body')
    def _compute_preview(self):
        """ Returns an un-formatted version of the message body. Output is capped
        at 100 chars with a ' [...]' suffix if applicable. It is the longest
        known mail client preview length (Outlook 2013)."""
        for message in self:
            plaintext_ct = tools.mail.html_to_inner_content(message.body)
            message.preview = textwrap.shorten(plaintext_ct, 190)

    @api.depends_context("uid")
    @api.depends("body")
    def _compute_linked_message_ids(self):
        """ Compute the linked messages from the body of the message."""
        message_ids_by_message = defaultdict(list)
        for message in self:
            if tools.is_html_empty(message.body):
                continue
            str_ids = html.fromstring(message.body).xpath(
                "//a[contains(@class, 'o_message_redirect') and @data-oe-model='mail.message']/@data-oe-id",
            )
            for str_id in str_ids:
                with contextlib.suppress(ValueError, TypeError):
                    message_ids_by_message[message].append(int(str_id))
        mids = [mid for mids in message_ids_by_message.values() for mid in mids]
        if not mids:
            self.linked_message_ids = self.env["mail.message"]
            return
        # Remove any potential sudo from the env as linked messages are user input, returning them
        # as sudo could lead to users being able to read any arbitrary message through this feature.
        # Only allowed messages for the current user are acceptable.
        linked_messages = self.sudo(False).search(Domain("id", "in", mids))
        for message in self:
            message.linked_message_ids = linked_messages.filtered(
                lambda m, message=message: m.id in message_ids_by_message[message],
            )

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        free = self.filtered(lambda m: not m.model or not m.res_id or m.model not in self.env)
        free.record_name = False
        # sudo here, as it behaves like a m2o -> can read message, can read name_get
        for message, record in (self - free)._record_by_message().items():
            try:
                message.record_name = record.sudo().display_name
            except MissingError:
                message.record_name = False

    @api.depends('author_id', 'author_guest_id')
    @api.depends_context('guest', 'uid')
    def _compute_is_current_user_or_guest_author(self):
        user = self.env.user
        guest = self.env['mail.guest']._get_guest_from_context()
        for message in self:
            if not user._is_public() and (message.author_id and message.author_id == user.partner_id):
                message.is_current_user_or_guest_author = True
            elif message.author_guest_id and message.author_guest_id == guest:
                message.is_current_user_or_guest_author = True
            else:
                message.is_current_user_or_guest_author = False

    def _compute_needaction(self):
        """ Need action on a mail.message = notified on my channel """
        my_messages = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('res_partner_id', '=', self.env.user.partner_id.id),
            ('is_read', '=', False)]).mapped('mail_message_id')
        for message in self:
            message.needaction = message in my_messages

    @api.model
    def _search_needaction(self, operator, operand):
        if operator not in ('in', 'not in'):
            return NotImplemented
        is_read = operator == 'not in'
        notification_ids = self.env['mail.notification']._search([('res_partner_id', '=', self.env.user.partner_id.id), ('is_read', '=', is_read)])
        return [('notification_ids', 'in', notification_ids)]

    def _compute_has_error(self):
        error_from_notification = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('notification_status', 'in', ('bounce', 'exception'))]).mapped('mail_message_id')
        for message in self:
            message.has_error = message in error_from_notification

    def _search_has_error(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        return [('notification_ids.notification_status', 'in', ('bounce', 'exception'))]

    @api.depends('starred_partner_ids')
    @api.depends_context('uid')
    def _compute_starred(self):
        """ Compute if the message is starred by the current user. """
        # TDE FIXME: use SQL
        starred = self.sudo().filtered(lambda msg: self.env.user.partner_id in msg.starred_partner_ids)
        for message in self:
            message.starred = message in starred

    @api.model
    def _search_starred(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        return [('starred_partner_ids', 'in', self.env.user.partner_id.ids)]

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs):
        """ Override that adds specific access rights of mail.message, to remove
        ids uid could not see according to our custom rules. Please refer to
        _check_access() for more details about those rules.

        Non employees users see only message with subtype (aka do not see
        internal logs).

        After having received ids of a classic search, keep only:
        - if author_id == pid, uid is the author, OR
        - uid belongs to a notified channel, OR
        - uid is in the specified recipients, OR
        - uid has a notification on the message
        - otherwise: remove the id
        """
        # Rules do not apply to administrator
        if self.env.is_superuser() or bypass_access:
            return super()._search(domain, offset, limit, order, bypass_access=True, **kwargs)

        # Non-employee see only messages with a subtype and not internal
        if not self.env.user._is_internal():
            domain = self._get_search_domain_share() & Domain(domain)

        # make the search query with the default rules
        query = super()._search(domain, offset, limit, order, **kwargs)

        # retrieve matching records and determine which ones are truly accessible
        self.flush_model(['model', 'res_id', 'author_id', 'message_type', 'partner_ids'])
        self.env['mail.notification'].flush_model(['mail_message_id', 'res_partner_id'])

        pid = self.env.user.partner_id.id
        ids = []
        allowed_ids = set()
        model_ids = defaultdict(lambda: defaultdict(set))

        rel_alias = query.make_alias(self._table, 'partner_ids')
        query.add_join("LEFT JOIN", rel_alias, 'mail_message_res_partner_rel', SQL(
            "%s = %s AND %s = %s",
            SQL.identifier(self._table, 'id'),
            SQL.identifier(rel_alias, 'mail_message_id'),
            SQL.identifier(rel_alias, 'res_partner_id'),
            pid,
        ))
        notif_alias = query.make_alias(self._table, 'notification_ids')
        query.add_join("LEFT JOIN", notif_alias, 'mail_notification', SQL(
            "%s = %s AND %s = %s",
            SQL.identifier(self._table, 'id'),
            SQL.identifier(notif_alias, 'mail_message_id'),
            SQL.identifier(notif_alias, 'res_partner_id'),
            pid,
        ))
        self.env.cr.execute(query.select(
            SQL.identifier(self._table, 'id'),
            SQL.identifier(self._table, 'model'),
            SQL.identifier(self._table, 'res_id'),
            SQL.identifier(self._table, 'author_id'),
            SQL.identifier(self._table, 'message_type'),
            SQL(
                "COALESCE(%s, %s)",
                SQL.identifier(rel_alias, 'res_partner_id'),
                SQL.identifier(notif_alias, 'res_partner_id'),
            ),
        ))
        for id_, model, res_id, author_id, message_type, partner_id in self.env.cr.fetchall():
            ids.append(id_)
            if author_id == pid:
                allowed_ids.add(id_)
            elif partner_id == pid:
                allowed_ids.add(id_)
            elif model and res_id and message_type != 'user_notification':
                model_ids[model][res_id].add(id_)

        allowed_ids.update(self._find_allowed_doc_ids(model_ids))
        allowed = self.browse(id_ for id_ in ids if id_ in allowed_ids)
        return allowed._as_query(order)

    def _get_search_domain_share(self):
        return Domain(['&', '&', ('is_internal', '=', False), ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)])

    @api.model
    def _find_allowed_doc_ids(self, model_ids):
        """ Filter out message user cannot read due to missing document access.

        :param dict model_ids: dictionary like {
            'document_model_name': {
                'document_id_1': set(message IDs),
                'document_id_2': set(message IDs),
            },
            [...]
        }

        :return: set of allowed message IDs to read, based on document check
        :rtype: set
        """
        IrModelAccess = self.env['ir.model.access']
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.items():
            if not IrModelAccess.check(doc_model, 'read', False):
                continue
            records_all = self.env[doc_model].with_context(active_test=False).search([('id', 'in', list(doc_dict))])
            allowed_documents = self.env[doc_model]
            # _mail_group_by_operation_for_mail_message_operation set prefetch to records_all.ids
            # hence should be good, no need to force it again
            operation_res_ids = records_all._mail_group_by_operation_for_mail_message_operation('read')
            # filter for each operation
            for record_operation, records in operation_res_ids.items():
                if record_operation == "read":  # already implied by 'search'
                    allowed_documents += records
                else:
                    allowed_documents += records._filtered_access(record_operation)
            allowed_ids |= {
                msg_id for document_id in allowed_documents.ids for msg_id in doc_dict[document_id]
            }
        return allowed_ids

    def _check_access(self, operation: str) -> tuple | None:
        """ Access rules of mail.message:
            - read: if
                - author_id == pid, uid is the author OR
                - create_uid == uid, uid is the creator OR
                - uid is in the recipients (partner_ids) OR
                - uid has been notified (needaction) OR
                - uid have read access to the related document if model, res_id
                - otherwise: raise
            - create: if
                - no model, no res_id (private message) OR
                - pid in message_follower_ids if model, res_id OR
                - uid can read the parent OR
                - uid have write or create access on the related document if model, res_id, OR
                - otherwise: raise
            - write: if
                - author_id == pid, uid is the author, OR
                - uid is in the recipients (partner_ids) OR
                - uid has write or create access on the related document if model, res_id
                - otherwise: raise
            - unlink: if
                - uid has write or create access on the related document
                - otherwise: raise

        Specific case: non employee users see only messages with subtype (aka do
        not see internal logs).
        """
        result = super()._check_access(operation)
        if not self:
            return result

        # discard forbidden records, and check remaining ones
        messages = self - result[0] if result else self
        if messages and (forbidden := messages._get_forbidden_access(operation)):
            if result:
                result = (result[0] + forbidden, result[1])
            else:
                result = (forbidden, lambda: forbidden._make_access_error(operation))
        return result

    def _get_forbidden_access(self, operation: str) -> api.Self:
        """ Return the subset of ``self`` that does not satisfy the specific
        conditions for messages.
        """
        forbidden = self.browse()

        # Non employees see only messages with a subtype (aka, not internal logs)
        if not self.env.user._is_internal():
            rows = self.env.execute_query(SQL(
                ''' SELECT message.id
                    FROM "mail_message" AS message
                    LEFT JOIN "mail_message_subtype" as subtype ON message.subtype_id = subtype.id
                    WHERE message.id = ANY (%s)
                        AND message.message_type = 'comment'
                        AND (message.is_internal IS TRUE OR message.subtype_id IS NULL OR subtype.internal IS TRUE)
                ''',
                self.ids,
            ))
            if rows:
                internal = self.browse(id_ for [id_] in rows)
                forbidden += internal
                self -= internal  # noqa: PLW0642
            if not self:
                return forbidden

        # Read the value of messages in order to determine their accessibility.
        # The values are put in 'messages_to_check', and entries are popped
        # once we know they are accessible. At the end, the remaining entries
        # are the invalid ones.
        self.flush_recordset(['model', 'res_id', 'author_id', 'create_uid', 'parent_id', 'message_type', 'partner_ids'])
        self.env['mail.notification'].flush_model(['mail_message_id', 'res_partner_id'])

        if operation in ('read', 'write'):
            query = SQL(
                """ SELECT m.id, m.model, m.res_id, m.author_id, m.create_uid, m.parent_id,
                        bool_or(partner_rel.res_partner_id IS NOT NULL OR needaction_rel.res_partner_id IS NOT NULL) AS notified,
                        m.message_type
                    FROM "mail_message" m
                    LEFT JOIN "mail_message_res_partner_rel" partner_rel
                        ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = %(pid)s
                    LEFT JOIN "mail_notification" needaction_rel
                        ON needaction_rel.mail_message_id = m.id AND needaction_rel.res_partner_id = %(pid)s
                    WHERE m.id = ANY(%(ids)s)
                    GROUP BY m.id
                """,
                pid=self.env.user.partner_id.id, ids=self.ids,
            )
        elif operation in ('create', 'unlink'):
            query = SQL(
                """ SELECT id, model, res_id, author_id, parent_id, message_type
                    FROM "mail_message"
                    WHERE id = ANY(%s)
                """, self.ids,
            )
        else:
            raise ValueError(_('Wrong operation name (%s)', operation))

        # trick: messages_to_check doesn't contain missing records from messages
        messages_to_check = {
            values['id']: values
            for values in self.env.execute_query_dict(query)
        }

        # Author condition (READ, WRITE, CREATE (private))
        partner_id = self.env.user.partner_id.id
        if operation == 'read':
            for mid, message in list(messages_to_check.items()):
                if (message.get('author_id') == partner_id
                        or message.get('create_uid') == self.env.uid):
                    messages_to_check.pop(mid)
        elif operation == 'write':
            for mid, message in list(messages_to_check.items()):
                if message.get('author_id') == partner_id:
                    messages_to_check.pop(mid)
        elif operation == 'create':
            for mid, message in list(messages_to_check.items()):
                if not self._is_thread_message_visible(vals=message):
                    messages_to_check.pop(mid)

        if not messages_to_check:
            return forbidden

        # Recipients condition, for read and write (partner_ids)
        # keep on top, usefull for systray notifications
        if operation in ('read', 'write'):
            for mid, message in list(messages_to_check.items()):
                if message.get('notified'):
                    messages_to_check.pop(mid)
            if not messages_to_check:
                return forbidden

        # CRUD: Access rights related to the document
        # {document_model_name: {document_id: message_ids}}
        model_docid_msgids = defaultdict(lambda: defaultdict(list))
        for mid, message in messages_to_check.items():
            if (message.get('model') and message.get('res_id') and
                    message.get('message_type') != 'user_notification'):
                model_docid_msgids[message['model']][message['res_id']].append(mid)

        for model, docid_msgids in model_docid_msgids.items():
            documents = self.env[model].browse(docid_msgids)
            # group documents per operation to check, based on mail.message access
            # note that some ids may be filtered out if (e.g. group limitation, ...)
            operation_res_ids = documents._mail_group_by_operation_for_mail_message_operation(operation)
            for record_operation, records in operation_res_ids.items():
                check_result = records._check_access(record_operation)
                forbidden_doc_ids = set(check_result[0]._ids) if check_result else set()
                for res_id in (r.id for r in records if r.id not in forbidden_doc_ids):
                    for mid in docid_msgids[res_id]:
                        messages_to_check.pop(mid)

        if not messages_to_check:
            return forbidden

        # Parent condition, for create (check for received notifications for the created message parent)
        if operation == 'create':
            parent_ids_msg_ids = defaultdict(list)
            for mid, message in messages_to_check.items():
                if message.get('parent_id'):
                    parent_ids_msg_ids[message['parent_id']].append(mid)
            if parent_ids_msg_ids:
                query = SQL(
                    """ SELECT m.id
                        FROM "mail_message" m
                        JOIN "mail_message_res_partner_rel" partner_rel
                            ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = %s
                        WHERE m.id = ANY(%s) """,
                    self.env.user.partner_id.id, list(parent_ids_msg_ids),
                )
                for [parent_id] in self.env.execute_query(query):
                    for mid in parent_ids_msg_ids[parent_id]:
                        messages_to_check.pop(mid)

            if not messages_to_check:
                return forbidden

            # Recipients condition for create (message_follower_ids)
            for model, docid_msgids in model_docid_msgids.items():
                domain = [
                    ('res_model', '=', model),
                    ('res_id', 'in', list(docid_msgids)),
                    ('partner_id', '=', self.env.user.partner_id.id),
                ]
                followers = self.env['mail.followers'].sudo().search_fetch(domain, ['res_id'])
                for follower in followers:
                    for mid in docid_msgids[follower.res_id]:
                        messages_to_check.pop(mid)

            if not messages_to_check:
                return forbidden

        forbidden += self.browse(messages_to_check)
        return forbidden

    def _make_access_error(self, operation: str) -> AccessError:
        return AccessError(_(
            "The requested operation cannot be completed due to security restrictions. "
            "Please contact your system administrator.\n\n"
            "(Document type: %(type)s, Operation: %(operation)s)\n\n"
            "Records: %(records)s, User: %(user)s",
            type=self._description,
            operation=operation,
            records=self.ids[:6],
            user=self.env.uid,
        ))

    @api.model
    def _get_with_access(self, message_id, mode="read", **kwargs):
        message = self.browse(message_id).exists()
        if not message:
            return message

        # sanity check on kwargs
        allowed_params = self.env[message.sudo().model or 'mail.thread']._get_allowed_access_params()
        if invalid := (set((kwargs or {}).keys()) - allowed_params):
            _logger.warning("Invalid parameters to _get_with_access: %s", invalid)

        if self.env.user._is_public() and self.env["mail.guest"]._get_guest_from_context():
            # Don't check_access_rights for public user with a guest, as the rules are
            # incorrect due to historically having no reason to allow operations on messages to
            # public user before the introduction of guests. Even with ignoring the rights,
            # check_access_rule and its sub methods are already covering all the cases properly.
            if not message.sudo(False)._get_forbidden_access(mode):
                return message
        else:
            if message.sudo(False).has_access(mode):
                return message

        if message.model and message.res_id:
            thread_su = self.env[message.model].browse(message.res_id).sudo()
            access_mode = thread_su._mail_get_operation_for_mail_message_operation(mode)[thread_su]
            if access_mode and self.env[message.model]._get_thread_with_access(message.res_id, mode=access_mode, **kwargs):
                return message

        return self.browse()

    @api.model_create_multi
    def create(self, vals_list):
        tracking_values_list = []
        for values in vals_list:
            if 'email_from' not in values:  # needed to compute reply_to
                _author_id, email_from = self.env['mail.thread']._message_compute_author(values.get('author_id'), email_from=None, raise_on_email=False)
                values['email_from'] = email_from
            if not values.get('message_id'):
                values['message_id'] = self._get_message_id(values)
            if 'reply_to' not in values:
                values['reply_to'] = self._get_reply_to(values)

            if not values.get('attachment_ids'):
                values['attachment_ids'] = []
            # extract base64 images
            if 'body' in values:
                Attachments = self.env['ir.attachment'].with_context(clean_context(self.env.context))
                data_to_url = {}
                def base64_to_boundary(match):
                    key = match.group(2)
                    if not data_to_url.get(key):
                        name = match.group(4) if match.group(4) else 'image%s' % len(data_to_url)
                        try:
                            attachment = Attachments.create({
                                'name': name,
                                'datas': match.group(2),
                                'res_model': values.get('model'),
                                'res_id': values.get('res_id'),
                            })
                        except binascii_error:
                            _logger.warning("Impossible to create an attachment out of badly formated base64 embedded image. Image has been removed.")
                            return match.group(3)  # group(3) is the url ending single/double quote matched by the regexp
                        else:
                            attachment.generate_access_token()
                            values['attachment_ids'].append((4, attachment.id))
                            data_to_url[key] = ['/web/image/%s?access_token=%s' % (attachment.id, attachment.access_token), name]
                    return '%s%s alt="%s"' % (data_to_url[key][0], match.group(3), data_to_url[key][1])
                values['body'] = _image_dataurl.sub(base64_to_boundary, values['body'] or '')

            # delegate creation of tracking after the create as sudo to avoid access rights issues
            tracking_values_list.append(values.pop('tracking_value_ids', False))

        messages = super().create(vals_list)

        # link back attachments to records, to filter out attachments linked to
        # the same records as the message (considered as ok if message is ok)
        # and check rights on other documents
        attachments_tocheck = self.env['ir.attachment']
        doc_to_attachment_ids = defaultdict(set)
        if all(isinstance(command, int) or command[0] in (4, 6)
               for values in vals_list
               for command in values['attachment_ids']):
            for values in vals_list:
                message_attachment_ids = set()
                for command in values['attachment_ids']:
                    if isinstance(command, int):
                        message_attachment_ids.add(command)
                    elif command[0] == 6:
                        message_attachment_ids |= set(command[2])
                    else:  # command[0] == 4:
                        message_attachment_ids.add(command[1])
                if message_attachment_ids:
                    key = (values.get('model'), values.get('res_id'))
                    doc_to_attachment_ids[key] |= message_attachment_ids

            attachment_ids_all = {
                attachment_id
                for doc_attachment_ids in doc_to_attachment_ids
                for attachment_id in doc_attachment_ids
            }
            AttachmentSudo = self.env['ir.attachment'].sudo().with_prefetch(list(attachment_ids_all))
            for (model, res_id), doc_attachment_ids in doc_to_attachment_ids.items():
                # check only attachments belonging to another model, access already
                # checked on message for other attachments
                attachments_tocheck += AttachmentSudo.browse(doc_attachment_ids).filtered(
                    lambda att: att.res_model != model or att.res_id != res_id
                ).sudo(False)
        else:
            attachments_tocheck = messages.attachment_ids  # fallback on read if any unknown command
        if attachments_tocheck:
            attachments_tocheck.check('read')

        for message, values, tracking_values_cmd in zip(messages, vals_list, tracking_values_list):
            if tracking_values_cmd:
                vals_lst = [dict(cmd[2], mail_message_id=message.id) for cmd in tracking_values_cmd if len(cmd) == 3 and cmd[0] == 0]
                other_cmd = [cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0]
                if vals_lst:
                    self.env['mail.tracking.value'].sudo().create(vals_lst)
                if other_cmd:
                    message.sudo().write({'tracking_value_ids': tracking_values_cmd})

            if message._is_thread_message_visible(vals=values):
                message._invalidate_documents(values.get('model'), values.get('res_id'))

        return messages

    def read(self, fields=None, load='_classic_read'):
        """ Override to explicitely call check_access(), that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        self.check_access('read')
        return super().read(fields=fields, load=load)

    def fetch(self, field_names=None):
        # This freaky hack is aimed at reading data without the overhead of
        # checking that "self" is accessible, which is already done above in
        # methods read() and _search(). It reproduces the existing behavior
        # before the introduction of method fetch(), where the low-lever
        # reading method _read() did not enforce any actual permission.
        self = self.sudo()
        return super().fetch(field_names)

    def write(self, vals):
        record_changed = 'model' in vals or 'res_id' in vals
        if record_changed and not self.env.is_system():
            raise AccessError(_("Only administrators can modify 'model' and 'res_id' fields."))
        if record_changed or 'message_type' in vals:
            self._invalidate_documents()
        res = super().write(vals)
        if vals.get('attachment_ids'):
            for mail in self:
                mail.attachment_ids.check(mode='read')
        if 'notification_ids' in vals or record_changed:
            self._invalidate_documents()
        return res

    def unlink(self):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        # the cache of the related document doesn't need to be invalidate (see @_invalidate_documents)
        # because the unlink method invalidates the whole cache anyway
        if not self:
            return True
        self.check_access('unlink')
        self.mapped('attachment_ids').filtered(
            lambda attach: attach.res_model == self._name and (attach.res_id in self.ids or attach.res_id == 0)
        ).unlink()
        messages_by_partner = defaultdict(lambda: self.env['mail.message'])
        partners_with_user = self.partner_ids.filtered('user_ids')
        for elem in self:
            for partner in (
                elem.partner_ids & partners_with_user | elem.notification_ids.author_id
            ):
                messages_by_partner[partner] |= elem
        # Notify front-end of messages deletion for partners having a user
        for partner, messages in messages_by_partner.items():
            partner._bus_send("mail.message/delete", {"message_ids": messages.ids})
        return super().unlink()

    def export_data(self, fields_to_export):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators are allowed to export mail message"))

        return super().export_data(fields_to_export)

    # ------------------------------------------------------
    # ACTIONS
    # ----------------------------------------------------

    def action_open_document(self):
        """ Opens the related record based on the model and ID """
        self.ensure_one()
        return {
            'res_id': self.res_id,
            'res_model': self.model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }

    # ------------------------------------------------------
    # DISCUSS API
    # ------------------------------------------------------

    @api.model
    def mark_all_as_read(self, domain=None):
        # not really efficient method: it does one db request for the
        # search, and one for each message in the result set is_read to True in the
        # current notifications from the relation.
        notif_domain = [
            ('res_partner_id', '=', self.env.user.partner_id.id),
            ('is_read', '=', False)]
        if domain:
            messages = self.search(domain)
            messages.set_message_done()
            return messages.ids

        notifications = self.env['mail.notification'].sudo().search_fetch(notif_domain, ['mail_message_id'])
        notifications.write({'is_read': True})

        self.env.user._bus_send(
            "mail.message/mark_as_read",
            {
                "message_ids": notifications.mail_message_id.ids,
                "needaction_inbox_counter": self.env.user.partner_id._get_needaction_count(),
            },
        )

    def set_message_done(self):
        """ Remove the needaction from messages for the current partner. """
        partner_id = self.env.user.partner_id
        notifications = self.env['mail.notification'].sudo().search_fetch([
            ('mail_message_id', 'in', self.ids),
            ('res_partner_id', '=', partner_id.id),
            ('is_read', '=', False),
        ], ['mail_message_id'])
        if not notifications:
            return
        notifications.write({'is_read': True})
        # notifies changes in messages through the bus.
        self.env.user._bus_send(
            "mail.message/mark_as_read",
            {
                "message_ids": notifications.mail_message_id.ids,
                "needaction_inbox_counter": self.env.user.partner_id._get_needaction_count(),
            },
        )

    @api.model
    def unstar_all(self):
        """ Unstar messages for the current partner. """
        starred_messages = self.search([("starred_partner_ids", "in", self.env.user.partner_id.id)])
        starred_messages.starred_partner_ids = [Command.unlink(self.env.user.partner_id.id)]
        self.env.user._bus_send(
            "mail.message/toggle_star", {"message_ids": starred_messages.ids, "starred": False}
        )

    def toggle_message_starred(self):
        """ Toggle messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.
        """
        self.ensure_one()
        # a user should always be able to star a message they can read
        self.check_access('read')
        starred = not self.starred
        if starred:
            self.starred_partner_ids = [Command.link(self.env.user.partner_id.id)]
        else:
            self.starred_partner_ids = [Command.unlink(self.env.user.partner_id.id)]
        self.env.user._bus_send(
            "mail.message/toggle_star", {"message_ids": [self.id], "starred": starred}
        )
        return Store().add(self, {"starred": self.starred}).get_result()

    @api.model
    def _message_fetch(self, domain, search_term=None, before=None, after=None, around=None, limit=30):
        res = {}
        domain = Domain(domain)
        if search_term:
            # we replace every space by a % to avoid hard spacing matching
            search_term = search_term.replace(" ", "%")
            domain &= Domain.OR([
                # sudo: access to attachment is allowed if you have access to the parent model
                [("attachment_ids", "in", self.env["ir.attachment"].sudo()._search([("name", "ilike", search_term)]))],
                [("body", "ilike", search_term)],
                [("subject", "ilike", search_term)],
                [("subtype_id.description", "ilike", search_term)],
            ])
            res["count"] = self.search_count(domain)
        if around is not None:
            messages_before = self.search(domain & Domain('id', '<=', around), limit=limit // 2, order="id DESC")
            messages_after = self.search(domain & Domain('id', '>', around), limit=limit // 2, order='id ASC')
            return {**res, "messages": (messages_after + messages_before).sorted('id', reverse=True)}
        if before:
            domain &= Domain('id', '<', before)
        if after:
            domain &= Domain('id', '>', after)
        res["messages"] = self.search(domain, limit=limit, order='id ASC' if after else 'id DESC')
        if after:
            res["messages"] = res["messages"].sorted('id', reverse=True)
        return res

    def _message_reaction(self, content, action, partner, guest, store: Store = None):
        self.ensure_one()
        # search for existing reaction
        domain = [
            ("message_id", "=", self.id),
            ("partner_id", "=", partner.id),
            ("guest_id", "=", guest.id),
            ("content", "=", content),
        ]
        reaction = self.env["mail.message.reaction"].search(domain)
        # create/unlink reaction if necessary
        if action == "add" and not reaction:
            create_values = {
                "message_id": self.id,
                "content": content,
                "partner_id": partner.id,
                "guest_id": guest.id,
            }
            self.env["mail.message.reaction"].create(create_values)
        if action == "remove" and reaction:
            reaction.unlink()
        if store:
            # fill the store to use for non logged in portal users in mail_message_reaction()
            self._reaction_group_to_store(store, content)
        # send the reaction group to bus for logged in users
        self._bus_send_reaction_group(content)

    def _bus_send_reaction_group(self, content):
        store = Store(bus_channel=self._bus_channel())
        self._reaction_group_to_store(store, content)
        store.bus_send()

    def _reaction_group_to_store(self, store: Store, content):
        group_domain = [("message_id", "=", self.id), ("content", "=", content)]
        reactions = self.env["mail.message.reaction"].search(group_domain)
        reaction_group = (
            Store.Many(reactions, mode="ADD")
            if reactions
            else [("DELETE", {"message": self.id, "content": content})]
        )
        store.add(self, {"reactions": reaction_group})

    # ------------------------------------------------------
    # STORE / NOTIFICATIONS
    # ------------------------------------------------------

    def _field_store_repr(self, field_name):
        """Return the default Store representation of the given field name, which can be passed as
        param to the various Store methods."""
        if field_name == "message_link_preview_ids":
            return [
                Store.Many(
                    "message_link_preview_ids",
                    value=lambda m: m.sudo()
                    .message_link_preview_ids.filtered(
                        lambda message_link_preview: not message_link_preview.is_hidden
                    )
                    .sorted(
                        lambda message_link_preview: (
                            message_link_preview.sequence,
                            message_link_preview.id,
                        )
                    ),
                )
            ]
        return [field_name]

    def _to_store_defaults(self, target: Store.Target):
        field_names = [
            # sudo: mail.message - reading attachments on accessible message is allowed
            Store.Many(
                "attachment_ids",
                sort="id",
                dynamic_fields=lambda m: m._get_store_attachment_fields(target),
                sudo=True,
            ),
            # sudo: mail.message: access to author_guest_id is allowed
            Store.One("author_guest_id", ["avatar_128", "name"], sudo=True),
            # sudo: mail.message: access to author_id is allowed
            Store.One(
                "author_id",
                ["avatar_128", "is_company", Store.One("main_user_id", "share")],
                dynamic_fields=lambda m: m._get_store_partner_name_fields(),
                sudo=True,
            ),
            "body",
            "create_date",
            "date",
            Store.Attr(
                "email_from",
                predicate=lambda m: target.is_internal(self.env)
                or (not m.author_id and not m.author_guest_id),
            ),
            "incoming_email_cc",
            "incoming_email_to",
            # sudo: mail.message - reading link preview on accessible message is allowed
            "message_format",
            "message_link_preview_ids",
            "message_type",
            "model",  # keep for iOS app
            # sudo: res.partner: reading limited data of recipients is acceptable
            Store.Many("partner_ids", ["avatar_128", "name"], sort="id", sudo=True),
            "pinned_at",
            # sudo: mail.message - reading reactions on accessible message is allowed
            Store.Attr("reactions", value=lambda m: Store.Many(m.sudo().reaction_ids)),
            "record_name",  # keep for iOS app
            "res_id",  # keep for iOS app
            "subject",
            # sudo: mail.message.subtype - reading subtype on accessible message is allowed
            Store.One("subtype_id", ["description"], sudo=True),
            "write_date",
            *self._get_store_linked_messages_fields(),
        ]
        if target.is_internal(self.env):
            # sudo - mail.notification: internal users can access notifications.
            field_names.append(
                Store.Many(
                    "notification_ids",
                    value=lambda m: m.sudo().notification_ids._filtered_for_web_client(),
                ),
            )
        return field_names

    def _to_store(self, store: Store, fields, *, format_reply=True, msg_vals=False, add_followers=False, followers=None):
        """Add the messages to the given store.

        :param format_reply: if True, also get data about the parent message if it exists.
            Only makes sense for discuss channel.

        :param msg_vals: dictionary of values used to create the message. If
          given it may be used to access values related to ``message`` without
          accessing it directly. It lessens query count in some optimized use
          cases by avoiding access message content in db;

        :param add_followers: if True, also add followers of the current target for each thread of
            each message. Only applicable if ``store.target`` is a specific user.

        :param followers: if given, use this pre-computed list of followers instead of fetching
            them. It lessen query count in some optimized use cases.
            Only applicable if ``add_followers`` is True.
        """
        if "message_format" not in fields:
            store.add_records_fields(self, fields)
            return
        fields.remove("message_format")
        # fetch scheduled notifications once, only if msg_vals is not given to
        # avoid useless queries when notifying Inbox right after a message_post
        scheduled_dt_by_msg_id = {}
        if msg_vals:
            scheduled_dt_by_msg_id = {msg.id: msg_vals.get("scheduled_date", False) for msg in self}
        elif self:
            schedulers = (
                self.env["mail.message.schedule"]
                .sudo()
                .search([("mail_message_id", "in", self.ids)])
            )
            for scheduler in schedulers:
                scheduled_dt_by_msg_id[scheduler.mail_message_id.id] = scheduler.scheduled_datetime
        record_by_message = self._record_by_message()
        records = record_by_message.values()
        non_channel_records = filter(lambda record: record._name != "discuss.channel", records)
        target_user = store.target.get_user(self.env)
        if target_user and add_followers and non_channel_records:
            if followers is None:
                domain = Domain.OR(
                    [("res_model", "=", model), ("res_id", "in", [r.id for r in records])]
                    for model, records in groupby(non_channel_records, key=lambda r: r._name)
                )
                domain &= Domain("partner_id", "=", target_user.partner_id.id)
                # sudo: mail.followers - reading followers of current partner
                followers = self.env["mail.followers"].sudo().search(domain)
            follower_by_record_and_partner = {
                (
                    self.env[follower.res_model].browse(follower.res_id),
                    follower.partner_id,
                ): follower
                for follower in followers
            }
        record_fields = [
            # sudo: mail.thread - if mentionned in a non accessible thread, name is allowed
            Store.Attr("display_name", sudo=True),
            Store.Attr(
                "module_icon",
                lambda record: modules.module.get_module_icon(self.env[record._name]._original_module),
                predicate=lambda record: self.env[record._name]._original_module,
            ),
        ]
        if target_user and add_followers and non_channel_records:
            record_fields.append(
                Store.One(
                    "selfFollower",
                    ["is_active", Store.One("partner_id", [])],
                    value=lambda r: follower_by_record_and_partner.get((r, target_user.partner_id)),
                ),
            )
        for record in records:
            store.add(record, record_fields, as_thread=True)
        if store.target.is_current_user(self.env):
            fields.append("starred")
        store.add(self, fields)
        for message in self:
            record = record_by_message.get(message)
            if record:
                if hasattr(record, "_message_compute_subject"):
                    # sudo: if mentionned in a non accessible thread, user should be able to see the subject
                    default_subject = record.sudo()._message_compute_subject()
                else:
                    default_subject = message.record_name
            else:
                default_subject = False
            data = {
                "default_subject": default_subject,
                "scheduledDatetime": scheduled_dt_by_msg_id.get(message.id, False),
                "thread": Store.One(record, [], as_thread=True),
            }

            if message.incoming_email_cc:
                data["incoming_email_cc"] = tools.mail.email_split_tuples(message.incoming_email_cc)
            if message.incoming_email_to:
                data["incoming_email_to"] = tools.mail.email_split_tuples(message.incoming_email_to)
            if store.target.is_current_user(self.env):
                # sudo: mail.message - filtering allowed tracking values
                displayed_tracking_ids = message.sudo().tracking_value_ids._filter_has_field_access(
                    self.env
                )
                if record and hasattr(record, "_track_filter_for_display"):
                    displayed_tracking_ids = record._track_filter_for_display(
                        displayed_tracking_ids
                    )
                # sudo: mail.message - checking whether there is a notification for the current user is acceptable
                notifications_partners = message.sudo().notification_ids.filtered(
                    lambda n: not n.is_read
                ).res_partner_id
                data["needaction"] = (
                    not self.env.user._is_public()
                    and self.env.user.partner_id in notifications_partners
                )
                data["trackingValues"] = displayed_tracking_ids._tracking_value_format()
            store.add(message, data)
        # Add extras at the end to guarantee order in result. In particular, the parent message
        # needs to be after the current message (client code assuming the first received message is
        # the one just posted for example, and not the message being replied to).
        self._extras_to_store(store, format_reply=format_reply)

    def _get_store_partner_name_fields(self):
        self.ensure_one()
        return ["name"]

    def _get_store_attachment_fields(self, target):
        self.ensure_one()
        if target.is_current_user(self.env) and self.is_current_user_or_guest_author:
            return self.env["ir.attachment"]._get_store_ownership_fields()
        return []

    def _get_store_linked_messages_fields(self):
        """Add the messages that are referenced by the current message's body to the given store.
        This method should only return message data that are not sensitive to be broadcasted to
        other users, as it doesn't check store.target by simplicity and the target might not
        necessarily have permission to read the linked messages."""
        record_by_message = self.linked_message_ids._record_by_message()
        return [
            Store.Many(
                "linked_message_ids",
                [
                    "model",
                    "res_id",
                    Store.Attr(
                        "thread",
                        lambda m: Store.One(
                            record_by_message.get(m),
                            # sudo: mail.thread - reading record name of accessible message is acceptable
                            [Store.Attr("display_name", sudo=True)],
                            as_thread=True,
                        ),
                    ),
                ],
                only_data=True,
            ),
        ]

    def _extras_to_store(self, store: Store, format_reply):
        pass

    def _message_notifications_to_store(self, store: Store):
        """Returns the current messages and their corresponding notifications in
        the format expected by the web client.

        Notifications hold the information about each recipient of a message: if
        the message was successfully sent or if an exception or bounce occurred.
        """
        store.add(
            self,
            [
                Store.One("author_id", []),
                Store.One("author_guest_id", []),
                "body",
                "date",
                "message_type",
                Store.Many(
                    "notification_ids",
                    value=lambda m: m.notification_ids._filtered_for_web_client(),
                ),
                Store.One(
                    "thread",
                    [
                        Store.Attr(
                            "modelName",
                            lambda thread: self.env["ir.model"]._get(thread._name).display_name,
                        ),
                        "display_name",
                    ],
                    as_thread=True,
                ),
            ],
        )

    def _notify_message_notification_update(self):
        """Send bus notifications to update status of notifications in the web
        client. Purpose is to send the updated status per author."""
        messages = self.env['mail.message']
        record_by_message = self._record_by_message()
        for message in self:
            # Check if user has access to the record before displaying a notification about it.
            # In case the user switches from one company to another, it might happen that they don't
            # have access to the record related to the notification. In this case, we skip it.
            # YTI FIXME: check allowed_company_ids if necessary
            if record := record_by_message.get(message):
                if record.has_access('read'):
                    messages += message
        messages_per_partner = defaultdict(lambda: self.env['mail.message'])
        for message in messages:
            if not self.env.user._is_public():
                messages_per_partner[self.env.user.partner_id] |= message
            if message.author_id and not any(user._is_public() for user in message.author_id.with_context(active_test=False).user_ids):
                messages_per_partner[message.author_id] |= message
        for partner, messages in messages_per_partner.items():
            if user := partner.main_user_id:
                store = Store(bus_channel=user)
                messages.with_user(user)._message_notifications_to_store(store)
                store.bus_send()

    def _bus_channel(self):
        return self.env.user

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _is_empty(self):
        self.ensure_one()
        return ((not self.body or tools.is_html_empty(self.body)) and
                (not self.subtype_id or not self.subtype_id.description) and
                not self.attachment_ids and
                not (self._has_field_access(self._fields['tracking_value_ids'], 'read') and self.tracking_value_ids))

    def _filter_empty(self):
        """ Return subset of "void" messages """
        return self.filtered(
            lambda msg: msg._is_empty()
        )

    @api.model
    def _get_reply_to(self, values):
        """ Return a specific reply_to for the document """
        author_id = values.get('author_id')
        model = values.get('model', self.env.context.get('default_model'))
        res_id = values.get('res_id', self.env.context.get('default_res_id')) or False
        email_from = values.get('email_from')
        message_type = values.get('message_type')
        records = None
        if self._is_thread_message(vals={'model': model, 'res_id': res_id, 'message_type': message_type}):
            records = self.env[model].browse([res_id])
        else:
            records = self.env[model] if model else self.env['mail.thread']
        return records.sudo()._notify_get_reply_to(default=email_from, author_id=author_id)[res_id]

    @api.model
    def _get_message_id(self, values):
        if values.get('reply_to_force_new', False) is True:
            message_id = tools.mail.generate_tracking_message_id('reply_to')
        elif self._is_thread_message(vals=values):
            message_id = tools.mail.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        else:
            message_id = tools.mail.generate_tracking_message_id('private')
        return message_id

    def _is_thread_message(self, vals=False, thread=None):
        """ Tool method to compute thread validity in notification methods. """
        vals = vals or {}
        res_model = vals['model'] if 'model' in vals else thread._name if thread else self.model
        res_id = vals['res_id'] if 'res_id' in vals else thread.ids[0] if thread and thread.ids else self.res_id
        return bool(res_id) if (res_model and res_model != 'mail.thread') else False

    def _is_thread_message_visible(self, vals=False, thread=None):
        """ In addition to being a thread message, it should not be a user specific
        notification that is recipient-specific. Used mainly for ACL purpose. """
        is_thread = self._is_thread_message(vals=vals, thread=thread)
        if is_thread:
            message_type = (vals or {}).get('message_type') or self.message_type
            return is_thread and message_type != 'user_notification'
        return is_thread

    def _invalidate_documents(self, model=None, res_id=None):
        """ Invalidate the cache of the documents followed by ``self``. """
        fnames = ['message_ids', 'message_needaction', 'message_needaction_counter']
        self.flush_recordset(['model', 'res_id'])
        for record in self:
            model = model or record.model
            res_id = res_id or record.res_id
            if model in self.pool and issubclass(self.pool[model], self.pool['mail.thread']):
                self.env[model].browse(res_id).invalidate_recordset(fnames)

    def _records_by_model_name(self):
        ids_by_model = defaultdict(OrderedSet)
        prefetch_ids_by_model = defaultdict(OrderedSet)
        prefetch_messages = self | self.browse(self._prefetch_ids)
        for message in prefetch_messages.filtered(lambda m: m.model and m.res_id):
            target = ids_by_model if message in self else prefetch_ids_by_model
            target[message.model].add(message.res_id)
        return {
            model_name: self.env[model_name].browse(ids)
            .with_prefetch(tuple(ids_by_model[model_name] | prefetch_ids_by_model[model_name]))
            for model_name, ids in ids_by_model.items()
        }

    def _record_by_message(self):
        records_by_model_name = self._records_by_model_name()
        return {
            message: self.env[message.model].browse(message.res_id)
            .with_prefetch(records_by_model_name[message.model]._prefetch_ids)
            for message in self.filtered(lambda m: m.model and m.res_id)
        }
