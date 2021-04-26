# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from binascii import Error as binascii_error
from collections import defaultdict
from operator import itemgetter

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import groupby

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/\n]{3,}=*)\n*([\'"])(?: data-filename="([^"]*)")?', re.I)


class Message(models.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _description = 'Message'
    _order = 'id desc'
    _rec_name = 'record_name'

    @api.model
    def default_get(self, fields):
        res = super(Message, self).default_get(fields)
        missing_author = 'author_id' in fields and 'author_id' not in res
        missing_email_from = 'email_from' in fields and 'email_from' not in res
        if missing_author or missing_email_from:
            author_id, email_from = self.env['mail.thread']._message_compute_author(res.get('author_id'), res.get('email_from'), raise_exception=False)
            if missing_email_from:
                res['email_from'] = email_from
            if missing_author:
                res['author_id'] = author_id
        return res

    # content
    subject = fields.Char('Subject')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    body = fields.Html('Contents', default='', sanitize_style=True)
    description = fields.Char(
        'Short description', compute="_compute_description",
        help='Message description: either the subject, or the beginning of the body')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id',
        string='Attachments',
        help='Attachments are linked to a document through model / res_id and to the message '
             'through this field.')
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', index=True, ondelete='set null',
        help="Initial thread message.")
    child_ids = fields.One2many('mail.message', 'parent_id', 'Child Messages')
    # related document
    model = fields.Char('Related Document Model', index=True)
    res_id = fields.Many2oneReference('Related Document ID', index=True, model_field='model')
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    # characteristics
    message_type = fields.Selection([
        ('email', 'Email'),
        ('comment', 'Comment'),
        ('notification', 'System notification'),
        ('user_notification', 'User Specific Notification')],
        'Type', required=True, default='email',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies",
        )
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', ondelete='set null', index=True)
    mail_activity_type_id = fields.Many2one(
        'mail.activity.type', 'Mail Activity Type',
        index=True, ondelete='set null')
    is_internal = fields.Boolean('Employee Only', help='Hide to public / portal users, independently from subtype configuration.')
    # origin
    email_from = fields.Char('From', help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True, ondelete='set null',
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.image_128', readonly=False)
    # recipients: include inactive partners (they may have been archived after
    # the message was sent, but they should remain visible in the relation)
    partner_ids = fields.Many2many('res.partner', string='Recipients', context={'active_test': False})
    # list of partner having a notification. Caution: list may change over time because of notif gc cron.
    # mainly usefull for testing
    notified_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_needaction_rel', string='Partners with Need Action',
        context={'active_test': False}, depends=['notification_ids'])
    needaction = fields.Boolean(
        'Need Action', compute='_get_needaction', search='_search_needaction',
        help='Need Action')
    has_error = fields.Boolean(
        'Has error', compute='_compute_has_error', search='_search_has_error',
        help='Has error')
    channel_ids = fields.Many2many(
        'mail.channel', 'mail_message_mail_channel_rel', string='Channels')
    # notifications
    notification_ids = fields.One2many(
        'mail.notification', 'mail_message_id', 'Notifications',
        auto_join=True, copy=False, depends=['notified_partner_ids'])
    # user interface
    starred_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_starred_rel', string='Favorited By')
    starred = fields.Boolean(
        'Starred', compute='_get_starred', search='_search_starred', compute_sudo=False,
        help='Current user has a starred notification linked to this message')
    # tracking
    tracking_value_ids = fields.One2many(
        'mail.tracking.value', 'mail_message_id',
        string='Tracking values',
        groups="base.group_no_one",
        help='Tracked values are stored in a separate model. This field allow to reconstruct '
             'the tracking and to generate statistics on the model.')
    # mail gateway
    no_auto_thread = fields.Boolean(
        'No threading for answers',
        help='Answers do not go in the original document discussion thread. This has an impact on the generated message-id.')
    message_id = fields.Char('Message-Id', help='Message unique identifier', index=True, readonly=1, copy=False)
    reply_to = fields.Char('Reply-To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    # moderation
    moderation_status = fields.Selection([
        ('pending_moderation', 'Pending Moderation'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')], string="Moderation Status", index=True)
    moderator_id = fields.Many2one('res.users', string="Moderated By", index=True)
    need_moderation = fields.Boolean('Need moderation', compute='_compute_need_moderation', search='_search_need_moderation')
    # keep notification layout informations to be able to generate mail again
    email_layout_xmlid = fields.Char('Layout', copy=False)  # xml id of layout
    add_sign = fields.Boolean(default=True)
    # `test_adv_activity`, `test_adv_activity_full`, `test_message_assignation_inbox`,...
    # By setting an inverse for mail.mail_message_id, the number of SQL queries done by `modified` is reduced.
    # 'mail.mail' inherits from `mail.message`: `_inherits = {'mail.message': 'mail_message_id'}`
    # Therefore, when changing a field on `mail.message`, this triggers the modification of the same field on `mail.mail`
    # By setting up the inverse one2many, we avoid to have to do a search to find the mails linked to the `mail.message`
    # as the cache value for this inverse one2many is up-to-date.
    # Besides for new messages, and messages never sending emails, there was no mail, and it was searching for nothing.
    mail_ids = fields.One2many('mail.mail', 'mail_message_id', string='Mails', groups="base.group_system")
    canned_response_ids = fields.One2many('mail.shortcode', 'message_ids', string="Canned Responses", store=False)

    def _compute_description(self):
        for message in self:
            if message.subject:
                message.description = message.subject
            else:
                plaintext_ct = '' if not message.body else tools.html2plaintext(message.body)
                message.description = plaintext_ct[:30] + '%s' % (' [...]' if len(plaintext_ct) >= 30 else '')

    def _get_needaction(self):
        """ Need action on a mail.message = notified on my channel """
        my_messages = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('res_partner_id', '=', self.env.user.partner_id.id),
            ('is_read', '=', False)]).mapped('mail_message_id')
        for message in self:
            message.needaction = message in my_messages

    @api.model
    def _search_needaction(self, operator, operand):
        is_read = False if operator == '=' and operand else True
        notification_ids = self.env['mail.notification']._search([('res_partner_id', '=', self.env.user.partner_id.id), ('is_read', '=', is_read)])
        return [('notification_ids', 'in', notification_ids)]

    def _compute_has_error(self):
        error_from_notification = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('notification_status', 'in', ('bounce', 'exception'))]).mapped('mail_message_id')
        for message in self:
            message.has_error = message in error_from_notification

    def _search_has_error(self, operator, operand):
        if operator == '=' and operand:
            return [('notification_ids.notification_status', 'in', ('bounce', 'exception'))]
        return ['!', ('notification_ids.notification_status', 'in', ('bounce', 'exception'))]  # this wont work and will be equivalent to "not in" beacause of orm restrictions. Dont use "has_error = False"

    @api.depends('starred_partner_ids')
    @api.depends_context('uid')
    def _get_starred(self):
        """ Compute if the message is starred by the current user. """
        # TDE FIXME: use SQL
        starred = self.sudo().filtered(lambda msg: self.env.user.partner_id in msg.starred_partner_ids)
        for message in self:
            message.starred = message in starred

    @api.model
    def _search_starred(self, operator, operand):
        if operator == '=' and operand:
            return [('starred_partner_ids', 'in', [self.env.user.partner_id.id])]
        return [('starred_partner_ids', 'not in', [self.env.user.partner_id.id])]

    def _compute_need_moderation(self):
        for message in self:
            message.need_moderation = False

    @api.model
    def _search_need_moderation(self, operator, operand):
        if operator == '=' and operand is True:
            return ['&', '&',
                    ('moderation_status', '=', 'pending_moderation'),
                    ('model', '=', 'mail.channel'),
                    ('res_id', 'in', self.env.user.moderation_channel_ids.ids)]

        # no support for other operators
        raise UserError(_('Unsupported search filter on moderation status'))

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    def init(self):
        self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to remove
        ids uid could not see according to our custom rules. Please refer to
        check_access_rule for more details about those rules.

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
        if self.env.is_superuser():
            return super(Message, self)._search(
                args, offset=offset, limit=limit, order=order,
                count=count, access_rights_uid=access_rights_uid)
        # Non-employee see only messages with a subtype and not internal
        if not self.env['res.users'].has_group('base.group_user'):
            args = expression.AND([self._get_search_domain_share(), args])
        # Perform a super with count as False, to have the ids, not a counter
        ids = super(Message, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=False, access_rights_uid=access_rights_uid)
        if not ids and count:
            return 0
        elif not ids:
            return ids

        pid = self.env.user.partner_id.id
        author_ids, partner_ids, channel_ids, allowed_ids = set([]), set([]), set([]), set([])
        model_ids = {}

        # check read access rights before checking the actual rules on the given ids
        super(Message, self.with_user(access_rights_uid or self._uid)).check_access_rights('read')

        self.flush(['model', 'res_id', 'author_id', 'message_type', 'partner_ids', 'channel_ids'])
        self.env['mail.notification'].flush(['mail_message_id', 'res_partner_id'])
        self.env['mail.channel'].flush(['channel_message_ids'])
        self.env['mail.channel.partner'].flush(['channel_id', 'partner_id'])
        for sub_ids in self._cr.split_for_in_conditions(ids):
            self._cr.execute("""
                SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.message_type,
                                COALESCE(partner_rel.res_partner_id, needaction_rel.res_partner_id),
                                channel_partner.channel_id as channel_id
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_res_partner_needaction_rel" needaction_rel
                ON needaction_rel.mail_message_id = m.id AND needaction_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = %%(pid)s

                WHERE m.id = ANY (%%(ids)s)""" % self._table, dict(pid=pid, ids=list(sub_ids)))
            for id, rmod, rid, author_id, message_type, partner_id, channel_id in self._cr.fetchall():
                if author_id == pid:
                    author_ids.add(id)
                elif partner_id == pid:
                    partner_ids.add(id)
                elif channel_id:
                    channel_ids.add(id)
                elif rmod and rid and message_type != 'user_notification':
                    model_ids.setdefault(rmod, {}).setdefault(rid, set()).add(id)

        allowed_ids = self._find_allowed_doc_ids(model_ids)

        final_ids = author_ids | partner_ids | channel_ids | allowed_ids

        if count:
            return len(final_ids)
        else:
            # re-construct a list based on ids, because set did not keep the original order
            id_list = [id for id in ids if id in final_ids]
            return id_list

    @api.model
    def _find_allowed_model_wise(self, doc_model, doc_dict):
        doc_ids = list(doc_dict)
        allowed_doc_ids = self.env[doc_model].with_context(active_test=False).search([('id', 'in', doc_ids)]).ids
        return set([message_id for allowed_doc_id in allowed_doc_ids for message_id in doc_dict[allowed_doc_id]])

    @api.model
    def _find_allowed_doc_ids(self, model_ids):
        IrModelAccess = self.env['ir.model.access']
        allowed_ids = set()
        for doc_model, doc_dict in model_ids.items():
            if not IrModelAccess.check(doc_model, 'read', False):
                continue
            allowed_ids |= self._find_allowed_model_wise(doc_model, doc_dict)
        return allowed_ids

    def check_access_rule(self, operation):
        """ Access rules of mail.message:
            - read: if
                - author_id == pid, uid is the author OR
                - uid is in the recipients (partner_ids) OR
                - uid has been notified (needaction) OR
                - uid is member of a listern channel (channel_ids.partner_ids) OR
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
                - uid is moderator of the channel and moderation_status is pending_moderation OR
                - uid has write or create access on the related document if model, res_id and moderation_status is not pending_moderation
                - otherwise: raise
            - unlink: if
                - uid is moderator of the channel and moderation_status is pending_moderation OR
                - uid has write or create access on the related document if model, res_id and moderation_status is not pending_moderation
                - otherwise: raise

        Specific case: non employee users see only messages with subtype (aka do
        not see internal logs).
        """
        def _generate_model_record_ids(msg_val, msg_ids):
            """ :param model_record_ids: {'model': {'res_id': (msg_id, msg_id)}, ... }
                :param message_values: {'msg_id': {'model': .., 'res_id': .., 'author_id': ..}}
            """
            model_record_ids = {}
            for id in msg_ids:
                vals = msg_val.get(id, {})
                if vals.get('model') and vals.get('res_id'):
                    model_record_ids.setdefault(vals['model'], set()).add(vals['res_id'])
            return model_record_ids

        if self.env.is_superuser():
            return
        # Non employees see only messages with a subtype (aka, not internal logs)
        if not self.env['res.users'].has_group('base.group_user'):
            self._cr.execute('''SELECT DISTINCT message.id, message.subtype_id, subtype.internal
                                FROM "%s" AS message
                                LEFT JOIN "mail_message_subtype" as subtype
                                ON message.subtype_id = subtype.id
                                WHERE message.message_type = %%s AND
                                    (message.is_internal IS TRUE OR message.subtype_id IS NULL OR subtype.internal IS TRUE) AND
                                    message.id = ANY (%%s)''' % (self._table), ('comment', self.ids,))
            if self._cr.fetchall():
                raise AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)', self._description, operation)
                    + ' - ({} {}, {} {})'.format(_('Records:'), self.ids[:6], _('User:'), self._uid)
                )

        # Read mail_message.ids to have their values
        message_values = dict((message_id, {}) for message_id in self.ids)

        self.flush(['model', 'res_id', 'author_id', 'parent_id', 'moderation_status', 'message_type', 'partner_ids', 'channel_ids'])
        self.env['mail.notification'].flush(['mail_message_id', 'res_partner_id'])
        self.env['mail.channel'].flush(['channel_message_ids', 'moderator_ids'])
        self.env['mail.channel.partner'].flush(['channel_id', 'partner_id'])
        self.env['res.users'].flush(['moderation_channel_ids'])

        if operation == 'read':
            self._cr.execute("""
                SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id,
                                COALESCE(partner_rel.res_partner_id, needaction_rel.res_partner_id),
                                channel_partner.channel_id as channel_id, m.moderation_status,
                                m.message_type as message_type
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_res_partner_needaction_rel" needaction_rel
                ON needaction_rel.mail_message_id = m.id AND needaction_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = %%(pid)s
                WHERE m.id = ANY (%%(ids)s)""" % self._table, dict(pid=self.env.user.partner_id.id, ids=self.ids))
            for mid, rmod, rid, author_id, parent_id, partner_id, channel_id, moderation_status, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False,
                    'notified': any((message_values[mid].get('notified'), partner_id, channel_id)),
                    'message_type': message_type,
                }
        elif operation == 'write':
            self._cr.execute("""
                SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id, m.moderation_status,
                                COALESCE(partner_rel.res_partner_id, needaction_rel.res_partner_id),
                                channel_partner.channel_id as channel_id, channel_moderator_rel.res_users_id as moderator_id,
                                m.message_type as message_type
                FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_res_partner_needaction_rel" needaction_rel
                ON needaction_rel.mail_message_id = m.id AND needaction_rel.res_partner_id = %%(pid)s
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = %%(pid)s
                LEFT JOIN "mail_channel" moderated_channel
                ON m.moderation_status = 'pending_moderation' AND m.res_id = moderated_channel.id
                LEFT JOIN "mail_channel_moderator_rel" channel_moderator_rel
                ON channel_moderator_rel.mail_channel_id = moderated_channel.id AND channel_moderator_rel.res_users_id = %%(uid)s
                WHERE m.id = ANY (%%(ids)s)""" % self._table, dict(pid=self.env.user.partner_id.id, uid=self.env.user.id, ids=self.ids))
            for mid, rmod, rid, author_id, parent_id, moderation_status, partner_id, channel_id, moderator_id, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id,
                    'notified': any((message_values[mid].get('notified'), partner_id, channel_id)),
                    'message_type': message_type,
                }
        elif operation == 'create':
            self._cr.execute("""SELECT DISTINCT id, model, res_id, author_id, parent_id, moderation_status, message_type FROM "%s" WHERE id = ANY (%%s)""" % self._table, (self.ids,))
            for mid, rmod, rid, author_id, parent_id, moderation_status, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False,
                    'message_type': message_type,
                }
        else:  # unlink
            self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id, m.moderation_status, channel_moderator_rel.res_users_id as moderator_id, m.message_type as message_type
                FROM "%s" m
                LEFT JOIN "mail_channel" moderated_channel
                ON m.moderation_status = 'pending_moderation' AND m.res_id = moderated_channel.id
                LEFT JOIN "mail_channel_moderator_rel" channel_moderator_rel
                ON channel_moderator_rel.mail_channel_id = moderated_channel.id AND channel_moderator_rel.res_users_id = (%%s)
                WHERE m.id = ANY (%%s)""" % self._table, (self.env.user.id, self.ids,))
            for mid, rmod, rid, author_id, parent_id, moderation_status, moderator_id, message_type in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id,
                    'message_type': message_type,
                }

        # Author condition (READ, WRITE, CREATE (private))
        author_ids = []
        if operation == 'read':
            author_ids = [mid for mid, message in message_values.items()
                          if message.get('author_id') and message.get('author_id') == self.env.user.partner_id.id]
        elif operation == 'write':
            author_ids = [mid for mid, message in message_values.items()
                          if message.get('moderation_status') != 'pending_moderation' and message.get('author_id') == self.env.user.partner_id.id]
        elif operation == 'create':
            author_ids = [mid for mid, message in message_values.items()
                          if not self.is_thread_message(message)]

        # Moderator condition: allow to WRITE, UNLINK if moderator of a pending message
        moderator_ids = []
        if operation in ['write', 'unlink']:
            moderator_ids = [mid for mid, message in message_values.items() if message.get('moderator_id')]
        messages_to_check = self.ids
        messages_to_check = set(messages_to_check).difference(set(author_ids), set(moderator_ids))
        if not messages_to_check:
            return

        # Recipients condition, for read and write (partner_ids)
        # keep on top, usefull for systray notifications
        notified_ids = []
        model_record_ids = _generate_model_record_ids(message_values, messages_to_check)
        if operation in ['read', 'write']:
            notified_ids = [mid for mid, message in message_values.items() if message.get('notified')]

        messages_to_check = set(messages_to_check).difference(set(notified_ids))
        if not messages_to_check:
            return

        # CRUD: Access rights related to the document
        document_related_ids = []
        document_related_candidate_ids = [mid for mid, message in message_values.items()
                if (message.get('model') and message.get('res_id') and
                    message.get('message_type') != 'user_notification' and
                    (message.get('moderation_status') != 'pending_moderation' or operation not in ['write', 'unlink']))]
        model_record_ids = _generate_model_record_ids(message_values, document_related_candidate_ids)
        for model, doc_ids in model_record_ids.items():
            DocumentModel = self.env[model]
            if hasattr(DocumentModel, '_get_mail_message_access'):
                check_operation = DocumentModel._get_mail_message_access(doc_ids, operation)  ## why not giving model here?
            else:
                check_operation = self.env['mail.thread']._get_mail_message_access(doc_ids, operation, model_name=model)
            records = DocumentModel.browse(doc_ids)
            records.check_access_rights(check_operation)
            mids = records.browse(doc_ids)._filter_access_rules(check_operation)
            document_related_ids += [
                mid for mid, message in message_values.items()
                if (message.get('model') == model and
                    message.get('res_id') in mids.ids and
                    message.get('message_type') != 'user_notification' and
                    (message.get('moderation_status') != 'pending_moderation' or
                    operation not in ['write', 'unlink']))]

        messages_to_check = messages_to_check.difference(set(document_related_ids))

        if not messages_to_check:
            return

        # Parent condition, for create (check for received notifications for the created message parent)
        notified_ids = []
        if operation == 'create':
            # TDE: probably clean me
            parent_ids = [message.get('parent_id') for message in message_values.values()
                          if message.get('parent_id')]
            self._cr.execute("""SELECT DISTINCT m.id, partner_rel.res_partner_id, channel_partner.partner_id FROM "%s" m
                LEFT JOIN "mail_message_res_partner_rel" partner_rel
                ON partner_rel.mail_message_id = m.id AND partner_rel.res_partner_id = (%%s)
                LEFT JOIN "mail_message_mail_channel_rel" channel_rel
                ON channel_rel.mail_message_id = m.id
                LEFT JOIN "mail_channel" channel
                ON channel.id = channel_rel.mail_channel_id
                LEFT JOIN "mail_channel_partner" channel_partner
                ON channel_partner.channel_id = channel.id AND channel_partner.partner_id = (%%s)
                WHERE m.id = ANY (%%s)""" % self._table, (self.env.user.partner_id.id, self.env.user.partner_id.id, parent_ids,))
            not_parent_ids = [mid[0] for mid in self._cr.fetchall() if any([mid[1], mid[2]])]
            notified_ids += [mid for mid, message in message_values.items()
                             if message.get('parent_id') in not_parent_ids]

        messages_to_check = messages_to_check.difference(set(notified_ids))
        if not messages_to_check:
            return

        # Recipients condition for create (message_follower_ids)
        if operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                followers = self.env['mail.followers'].sudo().search([
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ])
                fol_mids = [follower.res_id for follower in followers]
                notified_ids += [mid for mid, message in message_values.items()
                                 if message.get('model') == doc_model and
                                 message.get('res_id') in fol_mids and
                                 message.get('message_type') != 'user_notification'
                                 ]

        messages_to_check = messages_to_check.difference(set(notified_ids))
        if not messages_to_check:
            return

        if not self.browse(messages_to_check).exists():
            return
        raise AccessError(
            _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)', self._description, operation)
            + ' - ({} {}, {} {})'.format(_('Records:'), list(messages_to_check)[:6], _('User:'), self._uid)
        )

    @api.model_create_multi
    def create(self, values_list):
        tracking_values_list = []
        for values in values_list:
            if 'email_from' not in values:  # needed to compute reply_to
                author_id, email_from = self.env['mail.thread']._message_compute_author(values.get('author_id'), email_from=None, raise_exception=False)
                values['email_from'] = email_from
            if not values.get('message_id'):
                values['message_id'] = self._get_message_id(values)
            if 'reply_to' not in values:
                values['reply_to'] = self._get_reply_to(values)
            if 'record_name' not in values and 'default_record_name' not in self.env.context:
                values['record_name'] = self._get_record_name(values)

            if 'attachment_ids' not in values:
                values['attachment_ids'] = []
            # extract base64 images
            if 'body' in values:
                Attachments = self.env['ir.attachment']
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
                values['body'] = _image_dataurl.sub(base64_to_boundary, tools.ustr(values['body']))

            # delegate creation of tracking after the create as sudo to avoid access rights issues
            tracking_values_list.append(values.pop('tracking_value_ids', False))

        messages = super(Message, self).create(values_list)

        check_attachment_access = []
        if all(isinstance(command, int) or command[0] in (4, 6) for values in values_list for command in values.get('attachment_ids')):
            for values in values_list:
                for command in values.get('attachment_ids'):
                    if isinstance(command, int):
                        check_attachment_access += [command]
                    elif command[0] == 6:
                        check_attachment_access += command[2]
                    else:  # command[0] == 4:
                        check_attachment_access += [command[1]]
        else:
            check_attachment_access = messages.mapped('attachment_ids').ids  # fallback on read if any unknow command
        if check_attachment_access:
            self.env['ir.attachment'].browse(check_attachment_access).check(mode='read')

        for message, values, tracking_values_cmd in zip(messages, values_list, tracking_values_list):
            if tracking_values_cmd:
                vals_lst = [dict(cmd[2], mail_message_id=message.id) for cmd in tracking_values_cmd if len(cmd) == 3 and cmd[0] == 0]
                other_cmd = [cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0]
                if vals_lst:
                    self.env['mail.tracking.value'].sudo().create(vals_lst)
                if other_cmd:
                    message.sudo().write({'tracking_value_ids': tracking_values_cmd})

            if message.is_thread_message(values):
                message._invalidate_documents(values.get('model'), values.get('res_id'))

        return messages

    def read(self, fields=None, load='_classic_read'):
        """ Override to explicitely call check_access_rule, that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        self.check_access_rule('read')
        return super(Message, self).read(fields=fields, load=load)

    def write(self, vals):
        record_changed = 'model' in vals or 'res_id' in vals
        if record_changed or 'message_type' in vals:
            self._invalidate_documents()
        res = super(Message, self).write(vals)
        if vals.get('attachment_ids'):
            for mail in self:
                mail.attachment_ids.check(mode='read')
        if 'notification_ids' in vals or record_changed:
            self._invalidate_documents()
        return res

    def unlink(self):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        if not self:
            return True
        self.check_access_rule('unlink')
        self.mapped('attachment_ids').filtered(
            lambda attach: attach.res_model == self._name and (attach.res_id in self.ids or attach.res_id == 0)
        ).unlink()
        for elem in self:
            if elem.is_thread_message():
                elem._invalidate_documents()
        return super(Message, self).unlink()

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators are allowed to use grouped read on message model"))

        return super(Message, self)._read_group_raw(
            domain=domain, fields=fields, groupby=groupby, offset=offset,
            limit=limit, orderby=orderby, lazy=lazy,
        )

    def export_data(self, fields_to_export, raw_data=False):
        if not self.env.is_admin():
            raise AccessError(_("Only administrators are allowed to export mail message"))

        return super(Message, self).export_data(fields_to_export, raw_data)

    # ------------------------------------------------------
    # DISCUSS API
    # ------------------------------------------------------

    @api.model
    def mark_all_as_read(self, domain=None):
        # not really efficient method: it does one db request for the
        # search, and one for each message in the result set is_read to True in the
        # current notifications from the relation.
        partner_id = self.env.user.partner_id.id
        notif_domain = [
            ('res_partner_id', '=', partner_id),
            ('is_read', '=', False)]
        if domain:
            messages = self.search(domain)
            messages.set_message_done()
            return messages.ids

        notifications = self.env['mail.notification'].sudo().search(notif_domain)
        notifications.write({'is_read': True})

        ids = [n['mail_message_id'] for n in notifications.read(['mail_message_id'])]

        notification = {'type': 'mark_as_read', 'message_ids': [id[0] for id in ids], 'needaction_inbox_counter': self.env.user.partner_id.get_needaction_count()}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', partner_id), notification)

        return ids

    def set_message_done(self):
        """ Remove the needaction from messages for the current partner. """
        partner_id = self.env.user.partner_id

        notifications = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('res_partner_id', '=', partner_id.id),
            ('is_read', '=', False)])

        if not notifications:
            return

        # notifies changes in messages through the bus.  To minimize the number of
        # notifications, we need to group the messages depending on their channel_ids
        groups = []
        messages = notifications.mapped('mail_message_id')
        current_channel_ids = messages[0].channel_ids
        current_group = []
        for record in messages:
            if record.channel_ids == current_channel_ids:
                current_group.append(record.id)
            else:
                groups.append((current_group, current_channel_ids))
                current_group = [record.id]
                current_channel_ids = record.channel_ids

        groups.append((current_group, current_channel_ids))
        current_group = [record.id]
        current_channel_ids = record.channel_ids

        notifications.write({'is_read': True})

        for (msg_ids, channel_ids) in groups:
            # channel_ids in result is deprecated and will be removed in a future version
            notification = {'type': 'mark_as_read', 'message_ids': msg_ids, 'channel_ids': [c.id for c in channel_ids], 'needaction_inbox_counter': self.env.user.partner_id.get_needaction_count()}
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', partner_id.id), notification)

    @api.model
    def unstar_all(self):
        """ Unstar messages for the current partner. """
        partner_id = self.env.user.partner_id.id

        starred_messages = self.search([('starred_partner_ids', 'in', partner_id)])
        starred_messages.write({'starred_partner_ids': [(3, partner_id)]})

        ids = [m.id for m in starred_messages]
        notification = {'type': 'toggle_star', 'message_ids': ids, 'starred': False}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

    def toggle_message_starred(self):
        """ Toggle messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.
        """
        # a user should always be able to star a message he can read
        self.check_access_rule('read')
        starred = not self.starred
        if starred:
            self.sudo().write({'starred_partner_ids': [(4, self.env.user.partner_id.id)]})
        else:
            self.sudo().write({'starred_partner_ids': [(3, self.env.user.partner_id.id)]})

        notification = {'type': 'toggle_star', 'message_ids': [self.id], 'starred': starred}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

    # --------------------------------------------------
    # MODERATION API
    # --------------------------------------------------

    def moderate(self, decision, **kwargs):
        """ Moderate messages. A check is done on moderation status of the
        current user to ensure we only moderate valid messages. """
        moderated_channels = self.env.user.moderation_channel_ids
        to_moderate = [message.id for message in self
                       if message.model == 'mail.channel' and
                       message.res_id in moderated_channels.ids and
                       message.moderation_status == 'pending_moderation']
        if to_moderate:
            self.browse(to_moderate)._moderate(decision, **kwargs)

    def _moderate(self, decision, **kwargs):
        """ :param decision
                 * accept       - moderate message and broadcast that message to followers of relevant channels.
                 * reject       - message will be deleted from the database without broadcast
                                  an email sent to the author with an explanation that the moderators can edit.
                 * discard      - message will be deleted from the database without broadcast.
                 * allow        - add email address to white list people of specific channel,
                                  so that next time if a message come from same email address on same channel,
                                  it will be automatically broadcasted to relevant channels without any approval from moderator.
                 * ban          - add email address to black list of emails for the specific channel.
                                  From next time, a person sending a message using that email address will not need moderation.
                                  message_post will not create messages with the corresponding expeditor.
        """
        if decision == 'accept':
            self._moderate_accept()
        elif decision == 'reject':
            self._moderate_send_reject_email(kwargs.get('title'), kwargs.get('comment'))
            self._moderate_discard()
        elif decision == 'discard':
            self._moderate_discard()
        elif decision == 'allow':
            channels = self.env['mail.channel'].browse(self.mapped('res_id'))
            for channel in channels:
                channel._update_moderation_email(
                    list({message.email_from for message in self if message.res_id == channel.id}),
                    'allow'
                )
            self._search_from_same_authors()._moderate_accept()
        elif decision == 'ban':
            channels = self.env['mail.channel'].browse(self.mapped('res_id'))
            for channel in channels:
                channel._update_moderation_email(
                    list({message.email_from for message in self if message.res_id == channel.id}),
                    'ban'
                )
            self._search_from_same_authors()._moderate_discard()

    def _moderate_accept(self):
        self.write({
            'moderation_status': 'accepted',
            'moderator_id': self.env.uid
        })
        # proceed with notification process to send notification emails and Inbox messages
        for message in self:
            if message.is_thread_message(): # note, since we will only intercept _notify_thread for message posted on channel,
                # message will always be a thread_message. This check should always be true.
                self.env[message.model].browse(message.res_id)._notify_thread(message)

    def _moderate_send_reject_email(self, subject, comment):
        for msg in self:
            if not msg.email_from:
                continue
            body_html = tools.append_content_to_html('<div>%s</div>' % tools.ustr(comment), msg.body, plaintext=False)
            vals = {
                'subject': subject,
                'body_html': body_html,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.user.email_formatted or self.env.company.catchall_formatted,
                'email_to': msg.email_from,
                'auto_delete': True,
                'state': 'outgoing'
            }
            self.env['mail.mail'].sudo().create(vals)

    def _search_from_same_authors(self):
        """ Returns all pending moderation messages that have same email_from and
        same res_id as given recordset. """
        messages = self.env['mail.message'].sudo()
        for message in self:
            messages |= messages.search([
                ('moderation_status', '=', 'pending_moderation'),
                ('email_from', '=', message.email_from),
                ('model', '=', 'mail.channel'),
                ('res_id', '=', message.res_id)
            ])
        return messages

    def _moderate_discard(self):
        """ Notify deletion of messages to their moderators and authors and then delete them.
        """
        channel_ids = self.mapped('res_id')
        moderators = self.env['mail.channel'].browse(channel_ids).mapped('moderator_ids')
        authors = self.mapped('author_id')
        partner_to_pid = {}
        for moderator in moderators:
            partner_to_pid.setdefault(moderator.partner_id.id, set())
            partner_to_pid[moderator.partner_id.id] |= set([message.id for message in self if message.res_id in moderator.moderation_channel_ids.ids])
        for author in authors:
            partner_to_pid.setdefault(author.id, set())
            partner_to_pid[author.id] |= set([message.id for message in self if message.author_id == author])

        notifications = []
        for partner_id, message_ids in partner_to_pid.items():
            notifications.append([
                (self._cr.dbname, 'res.partner', partner_id),
                {'type': 'deletion', 'message_ids': sorted(list(message_ids))}  # sorted to make deterministic for tests
            ])
        self.env['bus.bus'].sendmany(notifications)
        self.unlink()

    def _notify_pending_by_chat(self):
        """ Generate the bus notifications for the given message and send them
        to the appropriate moderators and the author (if the author has not been
        elected moderator meanwhile). The author notification can be considered
        as a feedback to the author.
        """
        self.ensure_one()
        message = self.message_format()[0]
        partners = self.env['mail.channel'].browse(self.res_id).mapped('moderator_ids.partner_id')
        notifications = []
        for partner in partners:
            notifications.append([
                (self._cr.dbname, 'res.partner', partner.id),
                {'type': 'moderator', 'message': message}
            ])
        if self.author_id not in partners:
            notifications.append([
                (self._cr.dbname, 'res.partner', self.author_id.id),
                {'type': 'author', 'message': message}
            ])
        self.env['bus.bus'].sendmany(notifications)

    @api.model
    def _notify_moderators(self):
        """ Push a notification (Inbox/email) to moderators having messages
        waiting for moderation. This method is called once a day by a cron.
        """
        channels = self.env['mail.channel'].browse(self.search([('moderation_status', '=', 'pending_moderation')]).mapped('res_id'))
        moderators_to_notify = channels.mapped('moderator_ids')
        template = self.env.ref('mail.mail_channel_notify_moderation', raise_if_not_found=False)
        if not template:
            _logger.warning('Template "mail.mail_channel_notify_moderation" was not found. Cannot send reminder notifications.')
            return
        MailThread = self.env['mail.thread'].with_context(mail_notify_author=True)
        for moderator in moderators_to_notify:
            MailThread.message_notify(
                partner_ids=moderator.partner_id.ids,
                subject=_('Message are pending moderation'),  # tocheck: target language
                body=template._render({'record': moderator.partner_id}, engine='ir.qweb', minimal_qcontext=True),
                email_from=moderator.company_id.catchall_formatted or moderator.company_id.email_formatted,
            )

    # ------------------------------------------------------
    # MESSAGE READ / FETCH / FAILURE API
    # ------------------------------------------------------

    def _message_format(self, fnames):
        """Reads values from messages and formats them for the web client."""
        self.check_access_rule('read')
        vals_list = self._read_format(fnames)
        safari = request and request.httprequest.user_agent.browser == 'safari'

        thread_ids_by_model_name = defaultdict(set)
        for message in self:
            if message.model and message.res_id:
                thread_ids_by_model_name[message.model].add(message.res_id)

        for vals in vals_list:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)

            # Author
            if message_sudo.author_id:
                author = (message_sudo.author_id.id, message_sudo.author_id.display_name)
            else:
                author = (0, message_sudo.email_from)

            # Attachments
            main_attachment = self.env['ir.attachment']
            if message_sudo.attachment_ids and message_sudo.res_id and issubclass(self.pool[message_sudo.model], self.pool['mail.thread']):
                main_attachment = self.env[message_sudo.model].sudo().browse(message_sudo.res_id).message_main_attachment_id
            attachment_ids = []
            for attachment in message_sudo.attachment_ids:
                attachment_ids.append({
                    'checksum': attachment.checksum,
                    'id': attachment.id,
                    'filename': attachment.name,
                    'name': attachment.name,
                    'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
                    'is_main': main_attachment == attachment,
                    'res_id': attachment.res_id,
                    'res_model': attachment.res_model,
                })

            # Tracking values
            tracking_value_ids = []
            for tracking in message_sudo.tracking_value_ids:
                groups = tracking.field_groups
                if not groups or self.env.is_superuser() or self.user_has_groups(groups):
                    tracking_value_ids.append({
                        'id': tracking.id,
                        'changed_field': tracking.field_desc,
                        'old_value': tracking.get_old_display_value()[0],
                        'new_value': tracking.get_new_display_value()[0],
                        'field_type': tracking.field_type,
                    })

            if message_sudo.model and message_sudo.res_id:
                record_name = self.env[message_sudo.model] \
                    .browse(message_sudo.res_id) \
                    .sudo() \
                    .with_prefetch(thread_ids_by_model_name[message_sudo.model]) \
                    .display_name
            else:
                record_name = False

            vals.update({
                'author_id': author,
                'notifications': message_sudo.notification_ids._filtered_for_web_client()._notification_format(),
                'attachment_ids': attachment_ids,
                'tracking_value_ids': tracking_value_ids,
                'record_name': record_name,
            })

        return vals_list

    def message_fetch_failed(self):
        """Returns all messages, sent by the current user, that have errors, in
        the format expected by the web client."""
        messages = self.search([
            ('has_error', '=', True),
            ('author_id', '=', self.env.user.partner_id.id),
            ('res_id', '!=', 0),
            ('model', '!=', False),
            ('message_type', '!=', 'user_notification')
        ])
        return messages._message_notification_format()

    @api.model
    def message_fetch(self, domain, limit=20, moderated_channel_ids=None):
        """ Get a limited amount of formatted messages with provided domain.
            :param domain: the domain to filter messages;
            :param limit: the maximum amount of messages to get;
            :param list(int) moderated_channel_ids: if set, it contains the ID
              of a moderated channel. Fetched messages should include pending
              moderation messages for moderators. If the current user is not
              moderator, it should still get self-authored messages that are
              pending moderation;
            :returns list(dict).
        """
        messages = self.search(domain, limit=limit)
        if moderated_channel_ids:
            # Split load moderated and regular messages, as the ORed domain can
            # cause performance issues on large databases.
            moderated_messages_dom = [
                ('model', '=', 'mail.channel'),
                ('res_id', 'in', moderated_channel_ids),
                '|',
                ('author_id', '=', self.env.user.partner_id.id),
                ('moderation_status', '=', 'pending_moderation'),
            ]
            messages |= self.search(moderated_messages_dom, limit=limit)
            # Truncate the results to `limit`
            messages = messages.sorted(key='id', reverse=True)[:limit]
        return messages.message_format()

    def message_format(self):
        """ Get the message values in the format for web client. Since message values can be broadcasted,
            computed fields MUST NOT BE READ and broadcasted.
            :returns list(dict).
             Example :
                {
                    'body': HTML content of the message
                    'model': u'res.partner',
                    'record_name': u'Agrolait',
                    'attachment_ids': [
                        {
                            'file_type_icon': u'webimage',
                            'id': 45,
                            'name': u'sample.png',
                            'filename': u'sample.png'
                        }
                    ],
                    'needaction_partner_ids': [], # list of partner ids
                    'res_id': 7,
                    'tracking_value_ids': [
                        {
                            'old_value': "",
                            'changed_field': "Customer",
                            'id': 2965,
                            'new_value': "Axelor"
                        }
                    ],
                    'author_id': (3, u'Administrator'),
                    'email_from': 'sacha@pokemon.com' # email address or False
                    'subtype_id': (1, u'Discussions'),
                    'channel_ids': [], # list of channel ids
                    'date': '2015-06-30 08:22:33',
                    'partner_ids': [[7, "Sacha Du Bourg-Palette"]], # list of partner name_get
                    'message_type': u'comment',
                    'id': 59,
                    'subject': False
                    'is_note': True # only if the message is a note (subtype == note)
                    'is_discussion': False # only if the message is a discussion (subtype == discussion)
                    'is_notification': False # only if the message is a note but is a notification aka not linked to a document like assignation
                    'moderation_status': 'pending_moderation'
                }
        """
        vals_list = self._message_format(self._get_message_format_fields())

        com_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')
        note_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

        for vals in vals_list:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)
            notifs = message_sudo.notification_ids.filtered(lambda n: n.res_partner_id)
            vals.update({
                'needaction_partner_ids': notifs.filtered(lambda n: not n.is_read).res_partner_id.ids,
                'history_partner_ids': notifs.filtered(lambda n: n.is_read).res_partner_id.ids,
                'is_note': message_sudo.subtype_id.id == note_id,
                'is_discussion': message_sudo.subtype_id.id == com_id,
                'subtype_description': message_sudo.subtype_id.description,
                'is_notification': vals['message_type'] == 'user_notification',
            })
            if vals['model'] and self.env[vals['model']]._original_module:
                vals['module_icon'] = modules.module.get_module_icon(self.env[vals['model']]._original_module)
        return vals_list

    def _get_message_format_fields(self):
        return [
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
            'channel_ids', 'partner_ids',  # recipients
            'starred_partner_ids',  # list of partner ids for whom the message is starred
            'moderation_status',
        ]

    def _message_notification_format(self):
        """Returns the current messages and their corresponding notifications in
        the format expected by the web client.

        Notifications hold the information about each recipient of a message: if
        the message was successfully sent or if an exception or bounce occurred.
        """
        return [{
            'id': message.id,
            'res_id': message.res_id,
            'model': message.model,
            'res_model_name': message.env['ir.model']._get(message.model).display_name,
            'date': message.date,
            'message_type': message.message_type,
            'notifications': message.notification_ids._filtered_for_web_client()._notification_format(),
        } for message in self]

    def _notify_message_notification_update(self):
        """Send bus notifications to update status of notifications in the web
        client. Purpose is to send the updated status per author."""
        messages = self.env['mail.message']
        for message in self:
            # Check if user has access to the record before displaying a notification about it.
            # In case the user switches from one company to another, it might happen that he doesn't
            # have access to the record related to the notification. In this case, we skip it.
            # YTI FIXME: check allowed_company_ids if necessary
            if message.model and message.res_id:
                record = self.env[message.model].browse(message.res_id)
                try:
                    record.check_access_rights('read')
                    record.check_access_rule('read')
                except AccessError:
                    continue
                else:
                    messages |= message
        updates = [[
            (self._cr.dbname, 'res.partner', author.id),
            {'type': 'message_notification_update', 'elements': self.env['mail.message'].concat(*author_messages)._message_notification_format()}
        ] for author, author_messages in groupby(messages.sorted('author_id'), itemgetter('author_id'))]
        self.env['bus.bus'].sendmany(updates)

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    @api.model
    def _get_record_name(self, values):
        """ Return the related document name, using name_get. It is done using
            SUPERUSER_ID, to be sure to have the record name correctly stored. """
        model = values.get('model', self.env.context.get('default_model'))
        res_id = values.get('res_id', self.env.context.get('default_res_id'))
        if not model or not res_id or model not in self.env:
            return False
        return self.env[model].sudo().browse(res_id).display_name

    @api.model
    def _get_reply_to(self, values):
        """ Return a specific reply_to for the document """
        model = values.get('model', self._context.get('default_model'))
        res_id = values.get('res_id', self._context.get('default_res_id')) or False
        email_from = values.get('email_from')
        message_type = values.get('message_type')
        records = None
        if self.is_thread_message({'model': model, 'res_id': res_id, 'message_type': message_type}):
            records = self.env[model].browse([res_id])
        else:
            records = self.env[model] if model else self.env['mail.thread']
        return records._notify_get_reply_to(default=email_from)[res_id]

    @api.model
    def _get_message_id(self, values):
        if values.get('no_auto_thread', False) is True:
            message_id = tools.generate_tracking_message_id('reply_to')
        elif self.is_thread_message(values):
            message_id = tools.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        else:
            message_id = tools.generate_tracking_message_id('private')
        return message_id

    def is_thread_message(self, vals=None):
        if vals:
            res_id = vals.get('res_id')
            model = vals.get('model')
            message_type = vals.get('message_type')
        else:
            self.ensure_one()
            res_id = self.res_id
            model = self.model
            message_type = self.message_type
        return res_id and model and message_type != 'user_notification'

    def _invalidate_documents(self, model=None, res_id=None):
        """ Invalidate the cache of the documents followed by ``self``. """
        for record in self:
            model = model or record.model
            res_id = res_id or record.res_id
            if issubclass(self.pool[model], self.pool['mail.thread']):
                self.env[model].invalidate_cache(fnames=[
                    'message_ids',
                    'message_unread',
                    'message_unread_counter',
                    'message_needaction',
                    'message_needaction_counter',
                ], ids=[res_id])

    def _get_search_domain_share(self):
        return ['&', '&', ('is_internal', '=', False), ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)]
