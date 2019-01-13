# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from operator import itemgetter
from email.utils import formataddr
from openerp.http import request

from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.exceptions import UserError, AccessError
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

    _message_read_limit = 30

    @api.model
    def _get_default_from(self):
        if self.env.user.email:
            return formataddr((self.env.user.name, self.env.user.email))
        raise UserError(_("Unable to post message, please configure the sender's email address."))

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    # content
    subject = fields.Char('Subject')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    body = fields.Html('Contents', default='', sanitize_style=True)
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
    res_id = fields.Integer('Related Document ID', index=True)
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    # characteristics
    message_type = fields.Selection([
        ('email', 'Email'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='email',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies",
        oldname='type')
    subtype_id = fields.Many2one('mail.message.subtype', 'Subtype', ondelete='set null', index=True)
    mail_activity_type_id = fields.Many2one(
        'mail.activity.type', 'Mail Activity Type',
        index=True, ondelete='set null')
    # origin
    email_from = fields.Char(
        'From', default=_get_default_from,
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True,
        ondelete='set null', default=_get_default_author,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.image_small', readonly=False)
    # recipients: include inactive partners (they may have been archived after
    # the message was sent, but they should remain visible in the relation)
    partner_ids = fields.Many2many('res.partner', string='Recipients',
        context={'active_test': False})
    needaction_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_needaction_rel', string='Partners with Need Action',
        context={'active_test': False})
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
        auto_join=True, copy=False)
    # user interface
    starred_partner_ids = fields.Many2many(
        'res.partner', 'mail_message_res_partner_starred_rel', string='Favorited By')
    starred = fields.Boolean(
        'Starred', compute='_get_starred', search='_search_starred',
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
    #keep notification layout informations to be able to generate mail again
    layout = fields.Char('Layout', copy=False)  # xml id of layout
    add_sign = fields.Boolean(default=True)

    @api.multi
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
        if operator == '=' and operand:
            return ['&', ('notification_ids.res_partner_id', '=', self.env.user.partner_id.id), ('notification_ids.is_read', '=', False)]
        return ['&', ('notification_ids.res_partner_id', '=', self.env.user.partner_id.id), ('notification_ids.is_read', '=', True)]

    @api.multi
    def _compute_has_error(self):
        error_from_notification = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids),
            ('email_status', 'in', ('bounce', 'exception'))]).mapped('mail_message_id')
        for message in self:
            message.has_error = message in error_from_notification

    @api.multi
    def _search_has_error(self, operator, operand):
        if operator == '=' and operand:
            return ['&', ('notification_ids.email_status', 'in', ('bounce', 'exception')), ('author_id', '=', self.env.user.partner_id.id)]
        return ['!', '&', ('notification_ids.email_status', 'in', ('bounce', 'exception')), ('author_id', '=', self.env.user.partner_id.id)]  # this wont work and will be equivalent to "not in" beacause of orm restrictions. Dont use "has_error = False"

    @api.depends('starred_partner_ids')
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

    @api.multi
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
        return ValueError(_('Unsupported search filter on moderation status'))

    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------

    @api.model
    def mark_all_as_read(self, channel_ids=None, domain=None):
        """ Remove all needactions of the current partner. If channel_ids is
            given, restrict to messages written in one of those channels. """
        partner_id = self.env.user.partner_id.id
        delete_mode = not self.env.user.share  # delete employee notifs, keep customer ones
        if not domain and delete_mode:
            query = "DELETE FROM mail_message_res_partner_needaction_rel WHERE res_partner_id IN %s"
            args = [(partner_id,)]
            if channel_ids:
                query += """
                    AND mail_message_id in
                        (SELECT mail_message_id
                        FROM mail_message_mail_channel_rel
                        WHERE mail_channel_id in %s)"""
                args += [tuple(channel_ids)]
            query += " RETURNING mail_message_id as id"
            self._cr.execute(query, args)
            self.invalidate_cache()

            ids = [m['id'] for m in self._cr.dictfetchall()]
        else:
            # not really efficient method: it does one db request for the
            # search, and one for each message in the result set to remove the
            # current user from the relation.
            msg_domain = [('needaction_partner_ids', 'in', partner_id)]
            if channel_ids:
                msg_domain += [('channel_ids', 'in', channel_ids)]
            unread_messages = self.search(expression.AND([msg_domain, domain]))
            notifications = self.env['mail.notification'].sudo().search([
                ('mail_message_id', 'in', unread_messages.ids),
                ('res_partner_id', '=', self.env.user.partner_id.id),
                ('is_read', '=', False)])
            if delete_mode:
                notifications.unlink()
            else:
                notifications.write({'is_read': True})
            ids = unread_messages.mapped('id')

        notification = {'type': 'mark_as_read', 'message_ids': ids, 'channel_ids': channel_ids}
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), notification)

        return ids

    @api.multi
    def set_message_done(self):
        """ Remove the needaction from messages for the current partner. """
        partner_id = self.env.user.partner_id
        delete_mode = not self.env.user.share  # delete employee notifs, keep customer ones

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

        if delete_mode:
            notifications.unlink()
        else:
            notifications.write({'is_read': True})

        for (msg_ids, channel_ids) in groups:
            notification = {'type': 'mark_as_read', 'message_ids': msg_ids, 'channel_ids': [c.id for c in channel_ids]}
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

    @api.multi
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

    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record as super user}
        """
        # 1. Aggregate partners (author_id and partner_ids), attachments and tracking values
        partners = self.env['res.partner'].sudo()
        attachments = self.env['ir.attachment']
        message_ids = list(message_tree.keys())
        for message in message_tree.values():
            if message.author_id:
                partners |= message.author_id
            if message.subtype_id and message.partner_ids:  # take notified people of message with a subtype
                partners |= message.partner_ids
            elif not message.subtype_id and message.partner_ids:  # take specified people of message without a subtype (log)
                partners |= message.partner_ids
            if message.needaction_partner_ids:  # notified
                partners |= message.needaction_partner_ids
            if message.attachment_ids:
                attachments |= message.attachment_ids
        # Read partners as SUPERUSER -> message being browsed as SUPERUSER it is already the case
        partners_names = partners.name_get()
        partner_tree = dict((partner[0], partner) for partner in partners_names)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments_data = attachments.sudo().read(['id', 'datas_fname', 'name', 'mimetype'])
        safari = request and request.httprequest.user_agent.browser == 'safari'
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['datas_fname'],
            'name': attachment['name'],
            'mimetype': 'application/octet-stream' if safari and attachment['mimetype'] and 'video' in attachment['mimetype'] else attachment['mimetype'],
        }) for attachment in attachments_data)

        # 3. Tracking values
        tracking_values = self.env['mail.tracking.value'].sudo().search([('mail_message_id', 'in', message_ids)])
        message_to_tracking = dict()
        tracking_tree = dict.fromkeys(tracking_values.ids, False)
        for tracking in tracking_values:
            message_to_tracking.setdefault(tracking.mail_message_id.id, list()).append(tracking.id)
            tracking_tree[tracking.id] = {
                'id': tracking.id,
                'changed_field': tracking.field_desc,
                'old_value': tracking.get_old_display_value()[0],
                'new_value': tracking.get_new_display_value()[0],
                'field_type': tracking.field_type,
            }

        # 4. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            if message.subtype_id:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            else:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            # we read customer_email_status before filtering inactive user because we don't want to miss a red enveloppe
            customer_email_status = (
                (all(n.email_status == 'sent' for n in message.notification_ids) and 'sent') or
                (any(n.email_status == 'exception' for n in message.notification_ids) and 'exception') or
                (any(n.email_status == 'bounce' for n in message.notification_ids) and 'bounce') or
                'ready'
            )
            customer_email_data = []
            def filter_notification(notif):
                return (
                    (notif.email_status in ('bounce', 'exception', 'canceled') or notif.res_partner_id.partner_share) and
                    notif.res_partner_id.active
                )
            for notification in message.notification_ids.filtered(filter_notification):
                customer_email_data.append((partner_tree[notification.res_partner_id.id][0], partner_tree[notification.res_partner_id.id][1], notification.email_status))

            has_access_to_model = message.model and self.env[message.model].check_access_rights('read', raise_exception=False)
            main_attachment = has_access_to_model and message.res_id and self.env[message.model].search([('id', '=',message.res_id)]) and getattr(self.env[message.model].browse(message.res_id), 'message_main_attachment_id')
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachments_tree[attachment.id]['is_main'] = main_attachment == attachment
                    attachment_ids.append(attachments_tree[attachment.id])
            tracking_value_ids = []
            for tracking_value_id in message_to_tracking.get(message_id, list()):
                if tracking_value_id in tracking_tree:
                    tracking_value_ids.append(tracking_tree[tracking_value_id])

            message_dict.update({
                'author_id': author,
                'partner_ids': partner_ids,
                'customer_email_status': customer_email_status,
                'customer_email_data': customer_email_data,
                'attachment_ids': attachment_ids,
                'tracking_value_ids': tracking_value_ids,
            })

        return True

    @api.multi
    def message_fetch_failed(self):
        messages = self.search([('has_error', '=', True), ('author_id.id', '=', self.env.user.partner_id.id), ('res_id', '!=', 0), ('model', '!=', False)])
        return messages._format_mail_failures()

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
            moderated_messages_dom = [('model', '=', 'mail.channel'),
                                      ('res_id', 'in', moderated_channel_ids),
                                      '|',
                                      ('author_id', '=', self.env.user.partner_id.id),
                                      ('need_moderation', '=', True)]
            messages |= self.search(moderated_messages_dom, limit=limit)
            # Truncate the results to `limit`
            messages = messages.sorted(key='id', reverse=True)[:limit]
        return messages.message_format()

    @api.multi
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
        message_values = self.read([
            'id', 'body', 'date', 'author_id', 'email_from',  # base message fields
            'message_type', 'subtype_id', 'subject',  # message specific
            'model', 'res_id', 'record_name',  # document related
            'channel_ids', 'partner_ids',  # recipients
            'starred_partner_ids',  # list of partner ids for whom the message is starred
            'moderation_status',
        ])
        message_tree = dict((m.id, m) for m in self.sudo())
        self._message_read_dict_postprocess(message_values, message_tree)

        # add subtype data (is_note flag, is_discussion flag , subtype_description). Do it as sudo
        # because portal / public may have to look for internal subtypes
        subtype_ids = [msg['subtype_id'][0] for msg in message_values if msg['subtype_id']]
        subtypes = self.env['mail.message.subtype'].sudo().browse(subtype_ids).read(['internal', 'description','id'])
        subtypes_dict = dict((subtype['id'], subtype) for subtype in subtypes)

        com_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')
        note_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

        # fetch notification status
        notif_dict = {}
        notifs = self.env['mail.notification'].sudo().search([('mail_message_id', 'in', list(mid for mid in message_tree)), ('is_read', '=', False)])
        for notif in notifs:
            mid = notif.mail_message_id.id
            if not notif_dict.get(mid):
                notif_dict[mid] = {'partner_id': list()}
            notif_dict[mid]['partner_id'].append(notif.res_partner_id.id)

        for message in message_values:
            message['needaction_partner_ids'] = notif_dict.get(message['id'], dict()).get('partner_id', [])
            message['is_note'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['id'] == note_id
            message['is_discussion'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['id'] == com_id
            message['is_notification'] = message['is_note'] and not message['model'] and not message['res_id']
            message['subtype_description'] = message['subtype_id'] and subtypes_dict[message['subtype_id'][0]]['description']
            if message['model'] and self.env[message['model']]._original_module:
                message['module_icon'] = modules.module.get_module_icon(self.env[message['model']]._original_module)
        return message_values

    @api.multi
    def _format_mail_failures(self):
        """
        A shorter message to notify a failure update
        """
        failures_infos = []
        # for each channel, build the information header and include the logged partner information
        for message in self:
            info = {
                'message_id': message.id,
                'record_name': message.record_name,
                'model_name': self.env['ir.model']._get(message.model).display_name,
                'uuid': message.message_id,
                'res_id': message.res_id,
                'model': message.model,
                'last_message_date': message.date,
                'module_icon': '/mail/static/src/img/smiley/mailfailure.jpg',
                'notifications': dict((notif.res_partner_id.id, (notif.email_status, notif.res_partner_id.name)) for notif in message.notification_ids)
            }
            failures_infos.append(info)
        return failures_infos

    @api.multi
    def _notify_failure_update(self):
        authors = {}
        for author, author_messages in groupby(self, itemgetter('author_id')):
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', author.id),
                {'type': 'mail_failure', 'elements': self.env['mail.message'].concat(*author_messages)._format_mail_failures()}
            )

    #------------------------------------------------------
    # mail_message internals
    #------------------------------------------------------

    @api.model_cr
    def init(self):
        self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        if not self._cr.fetchone():
            self._cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")

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
        if self._uid == SUPERUSER_ID:
            return super(Message, self)._search(
                args, offset=offset, limit=limit, order=order,
                count=count, access_rights_uid=access_rights_uid)
        # Non-employee see only messages with a subtype (aka, no internal logs)
        if not self.env['res.users'].has_group('base.group_user'):
            args = ['&', '&', ('subtype_id', '!=', False), ('subtype_id.internal', '=', False)] + list(args)
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
        super(Message, self.sudo(access_rights_uid or self._uid)).check_access_rights('read')

        self._cr.execute("""
            SELECT DISTINCT m.id, m.model, m.res_id, m.author_id,
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

            WHERE m.id = ANY (%%(ids)s)""" % self._table, dict(pid=pid, ids=ids))
        for id, rmod, rid, author_id, partner_id, channel_id in self._cr.fetchall():
            if author_id == pid:
                author_ids.add(id)
            elif partner_id == pid:
                partner_ids.add(id)
            elif channel_id:
                channel_ids.add(id)
            elif rmod and rid:
                model_ids.setdefault(rmod, {}).setdefault(rid, set()).add(id)

        allowed_ids = self._find_allowed_doc_ids(model_ids)

        final_ids = author_ids | partner_ids | channel_ids | allowed_ids

        if count:
            return len(final_ids)
        else:
            # re-construct a list based on ids, because set did not keep the original order
            id_list = [id for id in ids if id in final_ids]
            return id_list

    @api.multi
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

        if self._uid == SUPERUSER_ID:
            return
        # Non employees see only messages with a subtype (aka, not internal logs)
        if not self.env['res.users'].has_group('base.group_user'):
            self._cr.execute('''SELECT DISTINCT message.id, message.subtype_id, subtype.internal
                                FROM "%s" AS message
                                LEFT JOIN "mail_message_subtype" as subtype
                                ON message.subtype_id = subtype.id
                                WHERE message.message_type = %%s AND (message.subtype_id IS NULL OR subtype.internal IS TRUE) AND message.id = ANY (%%s)''' % (self._table), ('comment', self.ids,))
            if self._cr.fetchall():
                raise AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
                    (self._description, operation))

        # Read mail_message.ids to have their values
        message_values = dict((res_id, {}) for res_id in self.ids)

        if operation == 'read':
            self._cr.execute("""
                SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id,
                                COALESCE(partner_rel.res_partner_id, needaction_rel.res_partner_id),
                                channel_partner.channel_id as channel_id, m.moderation_status
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
            for mid, rmod, rid, author_id, parent_id, partner_id, channel_id, moderation_status in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False,
                    'notified': any((message_values[mid].get('notified'), partner_id, channel_id))
                }
        elif operation == 'write':
            self._cr.execute("""
                SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id, m.moderation_status,
                                COALESCE(partner_rel.res_partner_id, needaction_rel.res_partner_id),
                                channel_partner.channel_id as channel_id, channel_moderator_rel.res_users_id as moderator_id
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
            for mid, rmod, rid, author_id, parent_id, moderation_status, partner_id, channel_id, moderator_id in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id,
                    'notified': any((message_values[mid].get('notified'), partner_id, channel_id))
                }
        elif operation == 'create':
            self._cr.execute("""SELECT DISTINCT id, model, res_id, author_id, parent_id, moderation_status FROM "%s" WHERE id = ANY (%%s)""" % self._table, (self.ids,))
            for mid, rmod, rid, author_id, parent_id, moderation_status in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': False
                }
        else:  # unlink
            self._cr.execute("""SELECT DISTINCT m.id, m.model, m.res_id, m.author_id, m.parent_id, m.moderation_status, channel_moderator_rel.res_users_id as moderator_id
                FROM "%s" m
                LEFT JOIN "mail_channel" moderated_channel
                ON m.moderation_status = 'pending_moderation' AND m.res_id = moderated_channel.id
                LEFT JOIN "mail_channel_moderator_rel" channel_moderator_rel
                ON channel_moderator_rel.mail_channel_id = moderated_channel.id AND channel_moderator_rel.res_users_id = (%%s)
                WHERE m.id = ANY (%%s)""" % self._table, (self.env.user.id, self.ids,))
            for mid, rmod, rid, author_id, parent_id, moderation_status, moderator_id in self._cr.fetchall():
                message_values[mid] = {
                    'model': rmod,
                    'res_id': rid,
                    'author_id': author_id,
                    'parent_id': parent_id,
                    'moderation_status': moderation_status,
                    'moderator_id': moderator_id
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
                          if not message.get('model') and not message.get('res_id')]

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

        # Moderator condition: allow to WRITE, UNLINK if moderator of a pending message
        moderator_ids = []
        if operation in ['write', 'unlink']:
            moderator_ids = [mid for mid, message in message_values.items() if message.get('moderator_id')]

        # Recipients condition, for read and write (partner_ids) and create (message_follower_ids)
        other_ids = set(self.ids).difference(set(author_ids), set(notified_ids), set(moderator_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        if operation in ['read', 'write']:
            notified_ids = [mid for mid, message in message_values.items() if message.get('notified')]
        elif operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                followers = self.env['mail.followers'].sudo().search([
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ])
                fol_mids = [follower.res_id for follower in followers]
                notified_ids += [mid for mid, message in message_values.items()
                                 if message.get('model') == doc_model and message.get('res_id') in fol_mids]

        # CRUD: Access rights related to the document
        other_ids = other_ids.difference(set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        document_related_ids = []
        for model, doc_ids in model_record_ids.items():
            DocumentModel = self.env[model]
            mids = DocumentModel.browse(doc_ids).exists()
            if hasattr(DocumentModel, 'check_mail_message_access'):
                DocumentModel.check_mail_message_access(mids.ids, operation)  # ?? mids ?
            else:
                self.env['mail.thread'].check_mail_message_access(mids.ids, operation, model_name=model)
            if operation in ['write', 'unlink']:
                document_related_ids += [mid for mid, message in message_values.items()
                                         if message.get('model') == model and message.get('res_id') in mids.ids and
                                         message.get('moderation_status') != 'pending_moderation']
            else:
                document_related_ids += [mid for mid, message in message_values.items()
                                         if message.get('model') == model and message.get('res_id') in mids.ids]

        # Calculate remaining ids: if not void, raise an error
        other_ids = other_ids.difference(set(document_related_ids))
        if not (other_ids and self.browse(other_ids).exists()):
            return
        raise AccessError(
            _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
            (self._description, operation))

    @api.model
    def _get_record_name(self, values):
        """ Return the related document name, using name_get. It is done using
            SUPERUSER_ID, to be sure to have the record name correctly stored. """
        model = values.get('model', self.env.context.get('default_model'))
        res_id = values.get('res_id', self.env.context.get('default_res_id'))
        if not model or not res_id or model not in self.env:
            return False
        return self.env[model].sudo().browse(res_id).name_get()[0][1]

    @api.model
    def _get_reply_to(self, values):
        """ Return a specific reply_to for the document """
        model, res_id, email_from = values.get('model', self._context.get('default_model')), values.get('res_id', self._context.get('default_res_id')), values.get('email_from')  # ctx values / defualt_get res ?
        records = self.env[model].browse([res_id]) if model and res_id else None
        return self.env['mail.thread']._notify_get_reply_to_on_records(default=email_from, records=records)[res_id or False]

    @api.model
    def _get_message_id(self, values):
        if values.get('no_auto_thread', False) is True:
            message_id = tools.generate_tracking_message_id('reply_to')
        elif values.get('res_id') and values.get('model'):
            message_id = tools.generate_tracking_message_id('%(res_id)s-%(model)s' % values)
        else:
            message_id = tools.generate_tracking_message_id('private')
        return message_id

    @api.multi
    def _invalidate_documents(self):
        """ Invalidate the cache of the documents followed by ``self``. """
        for record in self:
            if record.model and record.res_id and 'message_ids' in self.env[record.model]:
                self.env[record.model].invalidate_cache(fnames=[
                    'message_ids',
                    'message_unread',
                    'message_unread_counter',
                    'message_needaction',
                    'message_needaction_counter',
                ], ids=[record.res_id])

    @api.model
    def create(self, values):
        # coming from mail.js that does not have pid in its values
        if self.env.context.get('default_starred'):
            self = self.with_context({'default_starred_partner_ids': [(4, self.env.user.partner_id.id)]})

        if 'email_from' not in values:  # needed to compute reply_to
            values['email_from'] = self._get_default_from()
        if not values.get('message_id'):
            values['message_id'] = self._get_message_id(values)
        if 'reply_to' not in values:
            values['reply_to'] = self._get_reply_to(values)
        if 'record_name' not in values and 'default_record_name' not in self.env.context:
            values['record_name'] = self._get_record_name(values)

        if 'attachment_ids' not in values:
            values.setdefault('attachment_ids', [])

        # extract base64 images
        if 'body' in values:
            Attachments = self.env['ir.attachment']
            data_to_url = {}
            def base64_to_boundary(match):
                key = match.group(2)
                if not data_to_url.get(key):
                    name = match.group(4) if match.group(4) else 'image%s' % len(data_to_url)
                    attachment = Attachments.create({
                        'name': name,
                        'datas': match.group(2),
                        'datas_fname': name,
                        'res_model': values.get('model'),
                        'res_id': values.get('res_id'),
                    })
                    attachment.generate_access_token()
                    values['attachment_ids'].append((4, attachment.id))
                    data_to_url[key] = ['/web/image/%s?access_token=%s' % (attachment.id, attachment.access_token), name]
                return '%s%s alt="%s"' % (data_to_url[key][0], match.group(3), data_to_url[key][1])
            values['body'] = _image_dataurl.sub(base64_to_boundary, tools.ustr(values['body']))

        # delegate creation of tracking after the create as sudo to avoid access rights issues
        tracking_values_cmd = values.pop('tracking_value_ids', False)
        message = super(Message, self).create(values)

        if values.get('attachment_ids'):
            message.attachment_ids.check(mode='read')

        if tracking_values_cmd:
            vals_lst = [dict(cmd[2], mail_message_id=message.id) for cmd in tracking_values_cmd if len(cmd) == 3 and cmd[0] == 0]
            other_cmd = [cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0]
            if vals_lst:
                self.env['mail.tracking.value'].sudo().create(vals_lst)
            if other_cmd:
                message.sudo().write({'tracking_value_ids': tracking_values_cmd})

        if values.get('model') and values.get('res_id'):
            message._invalidate_documents()

        return message

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """ Override to explicitely call check_access_rule, that is not called
            by the ORM. It instead directly fetches ir.rules and apply them. """
        self.check_access_rule('read')
        return super(Message, self).read(fields=fields, load=load)

    @api.multi
    def write(self, vals):
        if 'model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        res = super(Message, self).write(vals)
        if vals.get('attachment_ids'):
            for mail in self:
                mail.attachment_ids.check(mode='read')
        if 'notification_ids' in vals or 'model' in vals or 'res_id' in vals:
            self._invalidate_documents()
        return res

    @api.multi
    def unlink(self):
        # cascade-delete attachments that are directly attached to the message (should only happen
        # for mail.messages that act as parent for a standalone mail.mail record).
        if not self:
            return True
        self.check_access_rule('unlink')
        self.mapped('attachment_ids').filtered(
            lambda attach: attach.res_model == self._name and (attach.res_id in self.ids or attach.res_id == 0)
        ).unlink()
        self._invalidate_documents()
        return super(Message, self).unlink()

    #------------------------------------------------------
    # Messaging API
    #------------------------------------------------------

    @api.multi
    def _notify(self, record, msg_vals, force_send=False, send_after_commit=True, model_description=False, mail_auto_delete=True):
        """ Main notification method. This method basically does two things

         * call ``_notify_compute_recipients`` that computes recipients to
           notify based on message record or message creation values if given
           (to optimize performance if we already have data computed);
         * call ``_notify_recipients`` that performs the notification process;

        :param record: record on which the message is posted, if any;
        :param msg_vals: dictionary of values used to create the message. If given
          it is used instead of accessing ``self`` to lesen query count in some
          simple cases where no notification is actually required;
        :param force_send: tells whether to send notification emails within the
          current transaction or to use the email queue;
        :param send_after_commit: if force_send, tells whether to send emails after
          the transaction has been committed using a post-commit hook;
        :param model_description: optional data used in notification process (see
          notification templates);
        :param mail_auto_delete: delete notification emails once sent;
        """
        msg_vals = msg_vals if msg_vals else {}
        rdata = self._notify_compute_recipients(record, msg_vals)
        return self._notify_recipients(
            rdata, record, msg_vals,
            force_send=force_send, send_after_commit=send_after_commit,
            model_description=model_description, mail_auto_delete=mail_auto_delete)

    @api.multi
    def _notify_compute_recipients(self, record, msg_vals):
        """ Compute recipients to notify based on subtype and followers. This
        method returns data structured as expected for ``_notify_recipients``. """
        msg_sudo = self.sudo()

        pids = [x[1] for x in msg_vals.get('partner_ids')] if 'partner_ids' in msg_vals else msg_sudo.partner_ids.ids
        cids = [x[1] for x in msg_vals.get('channel_ids')] if 'channel_ids' in msg_vals else msg_sudo.channel_ids.ids
        subtype_id = msg_vals.get('subtype_id') if 'subtype_id' in msg_vals else msg_sudo.subtype_id.id

        recipient_data = {
            'partners': [],
            'channels': [],
        }
        res = self.env['mail.followers']._get_recipient_data(record, subtype_id, pids, cids)
        author_id = msg_vals.get('author_id') or self.author_id.id if res else False
        for pid, cid, active, pshare, ctype, notif, groups in res:
            if pid and pid == author_id and not self.env.context.get('mail_notify_author'):  # do not notify the author of its own messages
                continue
            if pid:
                pdata = {'id': pid, 'active': active, 'share': pshare, 'groups': groups}
                if notif == 'inbox':
                    recipient_data['partners'].append(dict(pdata, notif=notif, type='user'))
                else:
                    if not pshare and notif:  # has an user and is not shared, is therefore user
                        recipient_data['partners'].append(dict(pdata, notif='email', type='user'))
                    elif pshare and notif:  # has an user but is shared, is therefore portal
                        recipient_data['partners'].append(dict(pdata, notif='email', type='portal'))
                    else:  # has no user, is therefore customer
                        recipient_data['partners'].append(dict(pdata, notif='email', type='customer'))
            elif cid:
                recipient_data['channels'].append({'id': cid, 'notif': notif, 'type': ctype})
        return recipient_data

    @api.multi
    def _notify_recipients(self, rdata, record, msg_vals,
                           force_send=False, send_after_commit=True,
                           model_description=False, mail_auto_delete=True):
        """ Main method implementing the notification process.

        :param rdata: dict containing recipients data: {
            'partners': list of dict containing partner data: id, share status (boolean),
            notification type ('email' or 'inbox'), type (main classification group used
            in notification process), groups (user groups)
            'channels': list of dict containing channel data: id, notification type
            ('email' for mailing list otherwise 'inbox'), type (channel_type)
        }
        """
        self.ensure_one()

        email_cids = [r['id'] for r in rdata['channels'] if r['notif'] == 'email']
        inbox_pids = [r['id'] for r in rdata['partners'] if r['notif'] == 'inbox']

        message_values = {}
        if rdata['channels']:
            message_values['channel_ids'] = [(6, 0, [r['id'] for r in rdata['channels']])]
        if rdata['partners']:
            message_values['needaction_partner_ids'] = [(6, 0, [r['id'] for r in rdata['partners']])]
        if message_values and record and hasattr(record, '_notify_customize_recipients'):
            message_values.update(record._notify_customize_recipients(self, message_values, rdata))
        if message_values:
            self.write(message_values)

        # notify partners and channels
        if email_cids:
            new_pids = self.env['res.partner'].sudo().search([
                ('id', 'not in', [r['id'] for r in rdata['partners']]),
                ('channel_ids', 'in', email_cids),
                ('email', 'not in', [self.author_id.email, self.email_from]),
            ])
            for partner in new_pids:
                rdata['partners'].append({'id': partner.id, 'share': True, 'notif': 'email', 'type': 'customer', 'groups': []})

        partner_email_rdata = [r for r in rdata['partners'] if r['notif'] == 'email']
        if partner_email_rdata:
            self.env['res.partner']._notify(self, partner_email_rdata, record, force_send=force_send, send_after_commit=send_after_commit, model_description=model_description, mail_auto_delete=mail_auto_delete)

        if inbox_pids:
            self.env['res.partner'].browse(inbox_pids)._notify_by_chat(self)

        if rdata['channels']:
            self.env['mail.channel'].sudo().browse([r['id'] for r in rdata['channels']])._notify(self)

        return True

    # --------------------------------------------------
    # Moderation
    # --------------------------------------------------

    @api.multi
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

    @api.multi
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
            record = self.env[message.model].browse(message.res_id) if message.model and message.res_id else None
            message._notify(record, {})

    @api.multi
    def _moderate_send_reject_email(self, subject, comment):
        for msg in self:
            if not msg.email_from:
                continue
            if self.env.user.partner_id.email:
                email_from = formataddr((self.env.user.partner_id.name, self.env.user.partner_id.email))
            else:
                email_from = self.env.user.company_id.catchall

            body_html = tools.append_content_to_html('<div>%s</div>' % tools.ustr(comment), msg.body)
            vals = {
                'subject': subject,
                'body_html': body_html,
                'email_from': email_from,
                'email_to': msg.email_from,
                'auto_delete': True,
                'state': 'outgoing'
            }
            self.env['mail.mail'].sudo().create(vals)

    @api.multi
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

    @api.multi
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
                {'type': 'deletion', 'message_ids': list(message_ids)}
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
                moderator.partner_id.ids,
                subject=_('Message are pending moderation'),  # tocheck: target language
                body=template.render({'record': moderator.partner_id}, engine='ir.qweb', minimal_qcontext=True),
                email_from=moderator.company_id.catchall or moderator.company_id.email,
            )
