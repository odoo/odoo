# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import textwrap
from binascii import Error as binascii_error
from collections import defaultdict

from odoo import _, api, Command, fields, models, modules, tools
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.tools import clean_context, groupby as tools_groupby, SQL

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(r'(data:image/[a-z]+?);base64,([a-z0-9+/\n]{3,}=*)\n*([\'"])(?: data-filename="([^"]*)")?', re.I)


class DiscussMessage(models.Model):
    _name = 'discuss.message'
    _description = 'Discuss Message'
    _order = 'id desc'

    # content
    channel_id = fields.Many2one('discuss.channel')
    body = fields.Html('Contents', default='', sanitize_style=True)

    # Ugly hack for compatibility with mail
    message_type = fields.Char(compute="_compute_message_type")
    def _compute_message_type(self):
        for message in self:
            message.message_type = "comment"

    preview = fields.Char(
        'Preview', compute='_compute_preview',
        help='The text-only beginning of the body used as email preview.')
    @api.depends('body')
    def _compute_preview(self):
        for message in self:
            message.preview = message._get_message_preview()

    link_preview_ids = fields.One2many(
        'mail.link.preview', 'message_id', string='Link Previews',
        groups="base.group_erp_manager")
    reaction_ids = fields.One2many(
        'mail.message.reaction', 'discuss_message_id', string="Reactions",
        groups="base.group_system")
    # Attachments are linked to a document through model / res_id and to the message through this field.
    attachment_ids = fields.Many2many(
        'ir.attachment', 'discuss_message_attachment_rel',
        'discuss_message_id', 'attachment_id',
        string='Attachments')
    parent_id = fields.Many2one(
        'discuss.message', 'Parent Message', index='btree_not_null', ondelete='set null')
    child_ids = fields.One2many('discuss.message', 'parent_id', 'Child Messages')
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True, ondelete='set null',
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    author_avatar = fields.Binary("Author's avatar", related='author_id.avatar_128', depends=['author_id'], readonly=False)
    author_guest_id = fields.Many2one(string="Guest", comodel_name='mail.guest')

    is_current_user_or_guest_author = fields.Boolean(compute='_compute_is_current_user_or_guest_author')
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

    # needaction = fields.Boolean(
    #     'Need Action', compute='_compute_needaction', search='_search_needaction')
    # user interface
    starred_partner_ids = fields.Many2many(
        'res.partner', 'discuss_message_res_partner_starred_rel', string='Favorited By')
    pinned_at = fields.Datetime('Pinned', help='Datetime at which the message has been pinned')
    starred = fields.Boolean(
        'Starred', compute='_compute_starred', search='_search_starred', compute_sudo=False,
        help='Current user has a starred notification linked to this message')
    @api.depends('starred_partner_ids')
    @api.depends_context('uid')
    def _compute_starred(self):
        starred = self.sudo().filtered(lambda msg: self.env.user.partner_id in msg.starred_partner_ids)
        for message in self:
            message.starred = message in starred

    notification_ids = fields.One2many(
        'mail.notification', 'discuss_message_id', 'Notifications',
        auto_join=True, copy=False)

    # def _compute_needaction(self):
    #     """ Need action on a mail.message = notified on my channel """
    #     my_messages = self.env['mail.notification'].sudo().search([
    #         ('mail_message_id', 'in', self.ids),
    #         ('res_partner_id', '=', self.env.user.partner_id.id),
    #         ('is_read', '=', False)]).mapped('mail_message_id')
    #     for message in self:
    #         message.needaction = message in my_messages

    def _get_author_guest_formated(self, guest_id):
        author_fields = {"id": True, "name": True}
        return guest_id._guest_format(author_fields).get(guest_id)

    def _get_author_partner_formated(self, author_id):
        author_fields = {
            "id": True,
            "name": True,
            "is_company": True,
            "user": {"id": True},
            "write_date": True,
        }
        return author_id.mail_partner_format(author_fields).get(author_id)

    def _get_author_formated(self, message):
        if message.author_guest_id:
            return self._get_author_guest_formated(message.author_guest_id)
        elif message.author_id:
            return self._get_author_partner_formated(message.author_id)

    def _get_message_reaction_formated(self, message):
        reactions_per_content = defaultdict(self.env['mail.message.reaction'].sudo().browse)
        for reaction in message.reaction_ids:
            reactions_per_content[reaction.content] |= reaction
        return [{
            'content': content,
            'count': len(reactions),
            'personas': [{'id': guest.id, 'name': guest.name, 'type': "guest"} for guest in reactions.guest_id] + [{'id': partner.id, 'name': partner.name, 'type': "partner"} for partner in reactions.partner_id],
            'message': {'id': message.id},
        } for content, reactions in reactions_per_content.items()]

    def _discuss_message_format(self):
        return [{
            "id": message.sudo().id,
            "body": message.sudo().body,
            "author": self._get_author_formated(message.sudo()),
            "thread": {
                "id": message.channel_id.id,
                "model": "discuss.channel",
            },
            "create_date": fields.Datetime.to_string(message.create_date),
            "write_date": fields.Datetime.to_string(message.write_date),
            "parentMessage": message.parent_id._discuss_message_format()[0] if message.parent_id else False,
            "attachments": sorted(message.attachment_ids._attachment_format(), key=lambda a: a["id"]),
            "reactions": self._get_message_reaction_formated(message),
            "linkPreviews": message.link_preview_ids.filtered(lambda preview: not preview.is_hidden)._link_preview_format(),
            "pinned_at": message.pinned_at,
            "starred": message.starred,
        } for message in self]

    @api.model
    def _search_needaction(self, operator, operand):
        is_read = False if operator == '=' and operand else True
        notification_ids = self.env['mail.notification']._search([('res_partner_id', '=', self.env.user.partner_id.id), ('is_read', '=', is_read)])
        return [('notification_ids', 'in', notification_ids)]

    @api.model
    def _search_starred(self, operator, operand):
        if operator == '=' and operand:
            return [('starred_partner_ids', 'in', [self.env.user.partner_id.id])]
        return [('starred_partner_ids', 'not in', [self.env.user.partner_id.id])]

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    # def init(self):
        # self._cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'mail_message_model_res_id_idx'""")
        # if not self._cr.fetchone():
        #     self._cr.execute("""CREATE INDEX mail_message_model_res_id_idx ON mail_message (model, res_id)""")
        # self._cr.execute("""CREATE INDEX IF NOT EXISTS mail_message_model_res_id_id_idx ON mail_message (model, res_id, id)""")

    def _validate_access_for_current_persona(self, operation):
        if not self:
            return False
        self.ensure_one()
        self.sudo(False).check_access_rule(operation)
        self.sudo(False).check_access_rights(operation)
        return True

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

        self.env['bus.bus']._sendone(self.env.user.partner_id, 'mail.message/mark_as_read', {
            'message_ids': notifications.mail_message_id.ids,
            'needaction_inbox_counter': self.env.user.partner_id._get_needaction_count(),
        })

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
        self.env['bus.bus']._sendone(partner_id, 'mail.message/mark_as_read', {
            'message_ids': notifications.mail_message_id.ids,
            'needaction_inbox_counter': self.env.user.partner_id._get_needaction_count(),
        })

    @api.model
    def unstar_all(self):
        """ Unstar messages for the current partner. """
        partner = self.env.user.partner_id

        starred_messages = self.search([('starred_partner_ids', 'in', partner.id)])
        partner.starred_message_ids -= starred_messages
        self.env['bus.bus']._sendone(partner, 'mail.message/toggle_star', {
            'message_ids': starred_messages.ids,
            'starred': False,
        })

    def toggle_message_starred(self):
        """ Toggle messages as (un)starred. Technically, the notifications related
            to uid are set to (un)starred.
        """
        # a user should always be able to star a message they can read
        self.check_access_rule('read')
        starred = not self.starred
        partner = self.env.user.partner_id
        if starred:
            partner.starred_discuss_message_ids |= self
        else:
            partner.starred_discuss_message_ids -= self

        self.env['bus.bus']._sendone(partner, 'mail.message/toggle_star', {
            'message_ids': [self.id],
            'starred': starred,
        })

    def _message_reaction(self, content, action):
        self.ensure_one()
        partner, guest = self.env["res.partner"]._get_current_persona()
        # search for existing reaction
        domain = [
            ("discuss_message_id", "=", self.id),
            ("partner_id", "=", partner.id),
            ("guest_id", "=", guest.id),
            ("content", "=", content),
        ]
        reaction = self.env["mail.message.reaction"].search(domain)
        # create/unlink reaction if necessary
        if action == "add" and not reaction:
            create_values = {
                "discuss_message_id": self.id,
                "content": content,
                "partner_id": partner.id,
                "guest_id": guest.id,
            }
            self.env["mail.message.reaction"].create(create_values)
        if action == "remove" and reaction:
            reaction.unlink()
        # format result
        group_domain = [("discuss_message_id", "=", self.id), ("content", "=", content)]
        count = self.env["mail.message.reaction"].search_count(group_domain)
        group_command = "ADD" if count > 0 else "DELETE"
        personas = [("ADD" if action == "add" else "DELETE", {"id": guest.id if guest else partner.id, "type": "guest" if guest else "partner"})] if guest or partner else []
        group_values = {
            "content": content,
            "count": count,
            "personas": personas,
            "message": {"id": self.id},
        }
        payload = {"Message": {"id": self.id, "reactions": [(group_command, group_values)]}}
        self.env["bus.bus"]._sendone(self._bus_notification_target(), "mail.record/insert", payload)

    # ------------------------------------------------------
    # MESSAGE READ / FETCH / FAILURE API
    # ------------------------------------------------------

    @api.model
    def _message_fetch(self, domain, search_term=None, before=None, after=None, around=None, limit=30):
        res = {}
        if search_term:
            # we replace every space by a % to avoid hard spacing matching
            search_term = search_term.replace(" ", "%")
            domain = expression.AND([domain, expression.OR([
                # sudo: access to attachment is allowed if you have access to the parent model
                [("attachment_ids", "in", self.env["ir.attachment"].sudo()._search([("name", "ilike", search_term)]))],
                [("body", "ilike", search_term)],
            ])])
            domain = expression.AND([domain, [("message_type", "not in", ["user_notification", "notification"])]])
            res["count"] = self.search_count(domain)
        if around:
            messages_before = self.search(domain=[*domain, ('id', '<=', around)], limit=limit // 2, order="id DESC")
            messages_after = self.search(domain=[*domain, ('id', '>', around)], limit=limit // 2, order='id ASC')
            return {**res, "messages": (messages_after + messages_before).sorted('id', reverse=True)}
        if before:
            domain = expression.AND([domain, [('id', '<', before)]])
        if after:
            domain = expression.AND([domain, [('id', '>', after)]])
        res["messages"] = self.search(domain, limit=limit, order='id ASC' if after else 'id DESC')
        if after:
            res["messages"] = res["messages"].sorted('id', reverse=True)
        return res

    def _bus_notification_target(self):
        self.ensure_one()
        return self.env.user.partner_id

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _cleanup_side_records(self):
        """ Clean related data: notifications, stars, ... to avoid lingering
        notifications / unreachable counters with void messages notably. """
        self.write({
            'starred_partner_ids': [(5, 0, 0)],
        })

    def _filter_empty(self):
        """ Return subset of "void" messages """
        return self.filtered(
            lambda msg:
                (not msg.body or tools.is_html_empty(msg.body)) and
                (not msg.subtype_id or not msg.subtype_id.description) and
                not msg.attachment_ids and
                not msg.tracking_value_ids
        )

    def _get_message_preview(self, max_char=190):
        self.ensure_one()
        plaintext_ct = tools.html_to_inner_content(self.body)
        return textwrap.shorten(plaintext_ct, max_char) if max_char else plaintext_ct
