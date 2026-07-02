# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store
from odoo.fields import Command, Domain
from odoo.http import request


class ResUsers(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_channel_ids = fields.Many2many(
        "im_livechat.channel", "im_livechat_channel_im_user", "user_id", "channel_id", copy=False
    )
    livechat_username = fields.Char(
        string="Livechat Username",
        compute="_compute_livechat_username",
        inverse="_inverse_livechat_username",
        store=False,
        user_writeable=True,
    )
    livechat_lang_ids = fields.Many2many(
        "res.lang",
        string="Livechat Languages",
        compute="_compute_livechat_lang_ids",
        inverse="_inverse_livechat_lang_ids",
        store=False,
        user_writeable=True,
    )
    livechat_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        string="Live Chat Expertise",
        compute="_compute_livechat_expertise_ids",
        inverse="_inverse_livechat_expertise_ids",
        store=False,
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
        user_writeable=True,
    )
    livechat_ongoing_session_count = fields.Integer(
        "Number of Ongoing sessions",
        compute="_compute_livechat_ongoing_session_count",
        groups="im_livechat.im_livechat_group_user",
    )
    livechat_is_in_call = fields.Boolean(
        help="Whether the user is in a call, only available if the user is in a live chat agent",
        compute="_compute_livechat_is_in_call",
        groups="im_livechat.im_livechat_group_user",
    )
    has_access_livechat = fields.Boolean(compute='_compute_has_access_livechat', string='Has access to Livechat', store=False, readonly=True)

    def _has_livechat_field_access(self):
        return (
            self.env.user == self
            or self.env.su
            or self.env.user.has_group('base.group_erp_manager')
            or self.env.user.has_group('im_livechat.im_livechat_group_user')
        )

    @api.depends("livechat_channel_ids", "is_in_call")
    def _compute_livechat_is_in_call(self):
        for user in self:
            # sudo - res.users: checking if user is in call is allowed if the user is member of a live chat channel.
            user.livechat_is_in_call = user.sudo().is_in_call if user.livechat_channel_ids else None

    @api.depends_context("im_livechat_channel_id")
    @api.depends("livechat_channel_ids.channel_ids.livechat_end_dt", "partner_id")
    def _compute_livechat_ongoing_session_count(self):
        domain = [
            ("channel_id.livechat_end_dt", "=", False),
            ("member_id", "!=", False),
            ("partner_id", "in", self.partner_id.ids),
            ("channel_id.last_interest_dt", ">=", "-15M"),
        ]
        if channel_id := self.env.context.get('im_livechat_channel_id'):
            domain.append(("session_livechat_channel_id", "=", channel_id))
        count_by_partner = dict(
            self.env["im_livechat.channel.member.history"]._read_group(
                domain, ["partner_id"], ["__count"],
            ),
        )
        for user in self:
            user.livechat_ongoing_session_count = count_by_partner.get(user.partner_id, 0)

    @api.depends('res_users_settings_id.livechat_username')
    @api.depends_context('uid')
    def _compute_livechat_username(self):
        if not self._has_livechat_field_access():
            self.livechat_username = False
            return
        for user in self:
            user.livechat_username = user.sudo().res_users_settings_id.livechat_username

    def _inverse_livechat_username(self):
        if not self._has_livechat_field_access():
            return
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_username = user.livechat_username

    @api.depends('res_users_settings_id.livechat_lang_ids')
    @api.depends_context('uid')
    def _compute_livechat_lang_ids(self):
        if not self._has_livechat_field_access():
            self.livechat_lang_ids = False
            return
        for user in self:
            user.livechat_lang_ids = user.sudo().res_users_settings_id.livechat_lang_ids

    def _inverse_livechat_lang_ids(self):
        if not self._has_livechat_field_access():
            return
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_lang_ids = user.livechat_lang_ids

    @api.depends("res_users_settings_id.livechat_expertise_ids")
    @api.depends_context('uid')
    def _compute_livechat_expertise_ids(self):
        if not self._has_livechat_field_access():
            self.livechat_expertise_ids = False
            return
        for user in self:
            user.livechat_expertise_ids = user.sudo().res_users_settings_id.livechat_expertise_ids

    def _inverse_livechat_expertise_ids(self):
        if not self._has_livechat_field_access():
            return
        for user in self:
            settings = self.env["res.users.settings"]._find_or_create_for_user(user)
            settings.livechat_expertise_ids = user.livechat_expertise_ids

    @api.depends("group_ids")
    def _compute_has_access_livechat(self):
        for user in self.sudo():
            user.has_access_livechat = user.has_group('im_livechat.im_livechat_group_user')

    def write(self, vals):
        if vals.get("group_ids"):
            operator_group = self.env.ref("im_livechat.im_livechat_group_user")
            if operator_group in self.all_group_ids:
                result = super().write(vals)
                lost_operators = self.filtered_domain([("all_group_ids", "not in", operator_group.id)])
                # sudo - im_livechat.channel: user manager can remove user from livechat channels
                self.env["im_livechat.channel"].sudo() \
                    .search([("user_ids", "in", lost_operators.ids)]) \
                    .write({"user_ids": [Command.unlink(operator.id) for operator in lost_operators]})
                return result
        return super().write(vals)

    def authenticate(self, credential, user_agent_env):
        auth_info = super().authenticate(credential, user_agent_env)
        if request and auth_info.get("uid"):
            token = request.cookies.get(self.env["mail.guest"]._cookie_name, "")
            guest = self.env["mail.guest"]._get_guest_from_token(token)
            env = self.env(user=auth_info["uid"], context=dict(guest=guest))
            if guest and not env.user._is_public():
                env.user.with_env(env)._join_livechat_sessions_from_guest(guest)
        return auth_info

    def _join_livechat_sessions_from_guest(self, guest):
        self.ensure_one()
        # using guest env to find livechat channels the guest has access to
        guest_access_env = self.env(user=self.env.ref("base.public_user"))
        channels_to_join = guest_access_env["discuss.channel"].search([
            ("channel_member_ids.guest_id", "=", guest.id),
            ("channel_partner_ids", "!=", self.partner_id.id),
            ("channel_type", "=", "livechat"),
            ("create_date", ">=", "now -1H"),
            ("livechat_end_dt", "=", False),
        ], limit=5, order="id DESC")
        if not channels_to_join:
            return self.env["discuss.channel.member"]
        # sudo: mail.message - reading messages to find guest-authored content and transfer ownership 
        # to the authenticated user is acceptable
        messages = channels_to_join.message_ids.sudo().filtered_domain(
            Domain("author_guest_id", "=", guest.id) | Domain("reaction_ids.guest_id", "=", guest.id)
        )
        guest_messages = messages.filtered_domain(Domain("author_guest_id", "=", guest.id))
        guest_messages.author_guest_id = None
        guest_messages.author_id = self.env.user.partner_id
        guest_reactions = messages.reaction_ids.filtered_domain(Domain("guest_id", "=", guest.id))
        guest_reactions.guest_id = None
        guest_reactions.partner_id = self.env.user.partner_id
        stores = Store.Stores()
        for cid, messages in messages.grouped("res_id").items():
            stores[channels_to_join.browse(cid)].add(
                messages,
                lambda res: (
                    # sudo: mail.message: access to author_guest_id is allowed
                    res.one("author_guest_id", "_store_avatar_fields", sudo=True),
                    # sudo: mail.message: access to author_id is allowed
                    res.one(
                        "author_id",
                        lambda res: (
                            res.attr("is_company"),
                            res.one("main_user_id", ["partner_id", "share"]),
                            res.from_method("_store_avatar_fields"),
                        ),
                        dynamic_fields="_store_author_dynamic_fields",
                        sudo=True,
                    ),
                    res.from_method("_store_reaction_group_fields")
                ),
            )
        channels_to_join.self_member_id.unlink()
        # sudo: discuss.channel - user is not a member yet and cannot add themselves;
        # the user authenticated as the guest who was a member of these channels, so adding them is legitimate
        members = channels_to_join.with_env(self.env).sudo()._add_members(users=self, post_joined_message=False)
        for member in members:
            notif = self.env._(
                "%(visitor)s authenticated as %(user)s.",
                # sudo: mail.guest - reading the name for a notification message is acceptable
                visitor=guest.sudo().name,
                user=self.env.user.partner_id.name,
            )
            member.channel_id.message_post(
                body=Markup('<div class="o_mail_notification" data-oe-type="o_mail_notification">%s</div>') % notif,
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
            )
        return members

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        res.attr("has_access_livechat", self.has_access_livechat)
        if self._is_internal():
            domain = [
                ("channel_id.channel_type", "=", "livechat"),
                ("is_self", "=", True),
                ("is_pinned", "=", True),
            ]
            has_pinned_livechats = self.env["discuss.channel.member"].search_count(domain, limit=1) > 0
            res.attr("show_livechat_category", has_pinned_livechats)

    def _store_init_fields(self, res: Store.FieldList):
        super()._store_init_fields(res)
        if res.is_for_internal_users():
            res.attr(
                "is_livechat_manager",
                lambda u: u.has_group("im_livechat.im_livechat_group_manager"),
            )
