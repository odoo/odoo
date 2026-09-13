from odoo import api, fields, models
from odoo.fields import Command

from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    livechat_channel_ids = fields.Many2many(
        comodel_name="im_livechat.channel",
        relation="im_livechat_channel_im_user",
        column1="user_id",
        column2="channel_id",
        copy=False,
    )
    livechat_username = fields.Char(
        compute="_compute_livechat_username",
        inverse="_inverse_livechat_username",
        store=False,
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
    )
    livechat_lang_ids = fields.Many2many(
        comodel_name="res.lang",
        string="Livechat Languages",
        compute="_compute_livechat_lang_ids",
        inverse="_inverse_livechat_lang_ids",
        store=False,
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
    )
    livechat_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        string="Live Chat Expertise",
        compute="_compute_livechat_expertise_ids",
        inverse="_inverse_livechat_expertise_ids",
        store=False,
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
    )
    livechat_ongoing_session_count = fields.Integer(
        string="Number of Ongoing sessions",
        compute="_compute_livechat_ongoing_session_count",
        groups="im_livechat.im_livechat_group_user",
    )
    livechat_is_in_call = fields.Boolean(
        compute="_compute_livechat_is_in_call",
        groups="im_livechat.im_livechat_group_user",
        help="Whether the user is in a call, only available if the user is in a live chat agent",
    )
    has_access_livechat = fields.Boolean(
        string="Has access to Livechat",
        compute="_compute_has_access_livechat",
        store=False,
        readonly=True,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "has_access_livechat",
            "livechat_expertise_ids",
            "livechat_lang_ids",
            "livechat_username",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "livechat_expertise_ids",
            "livechat_lang_ids",
            "livechat_username",
        ]

    @api.depends("livechat_channel_ids", "is_in_call")
    def _compute_livechat_is_in_call(self):
        for user in self:
            user.livechat_is_in_call = (
                user.sudo().is_in_call if user.livechat_channel_ids else None
            )

    @api.depends_context("im_livechat_channel_id")
    @api.depends("livechat_channel_ids.channel_ids.livechat_end_dt", "partner_id")
    def _compute_livechat_ongoing_session_count(self):
        domain = [
            ("channel_id.livechat_end_dt", "=", False),
            ("member_id", "!=", False),
            ("partner_id", "in", self.partner_id.ids),
            ("channel_id.last_interest_dt", ">=", "-15M"),
        ]
        if channel_id := self.env.context.get("im_livechat_channel_id"):
            domain.append(("session_livechat_channel_id", "=", channel_id))
        count_by_partner = dict(
            self.env["im_livechat.channel.member.history"]._read_group(
                domain,
                ["partner_id"],
                ["__count"],
            ),
        )
        for user in self:
            user.livechat_ongoing_session_count = count_by_partner.get(
                user.partner_id, 0
            )

    @api.depends("res_users_settings_id.livechat_username")
    def _compute_livechat_username(self):
        for user in self:
            user.livechat_username = user.sudo().res_users_settings_id.livechat_username

    def _inverse_livechat_username(self):
        for user in self:
            settings = self.env["res.users.settings"]._get_or_create_for_user(user)
            settings.livechat_username = user.livechat_username

    @api.depends("res_users_settings_id.livechat_lang_ids")
    def _compute_livechat_lang_ids(self):
        for user in self:
            user.livechat_lang_ids = user.sudo().res_users_settings_id.livechat_lang_ids

    def _inverse_livechat_lang_ids(self):
        for user in self:
            settings = self.env["res.users.settings"]._get_or_create_for_user(user)
            settings.livechat_lang_ids = user.livechat_lang_ids

    @api.depends("res_users_settings_id.livechat_expertise_ids")
    def _compute_livechat_expertise_ids(self):
        for user in self:
            user.livechat_expertise_ids = (
                user.sudo().res_users_settings_id.livechat_expertise_ids
            )

    def _inverse_livechat_expertise_ids(self):
        for user in self:
            settings = self.env["res.users.settings"]._get_or_create_for_user(user)
            settings.livechat_expertise_ids = user.livechat_expertise_ids

    @api.depends("group_ids")
    def _compute_has_access_livechat(self):
        for user in self.sudo():
            user.has_access_livechat = user.has_group(
                "im_livechat.im_livechat_group_user"
            )

    def write(self, vals):
        if vals.get("group_ids"):
            operator_group = self.env.ref("im_livechat.im_livechat_group_user")
            if operator_group in self.all_group_ids:
                operators = self.filtered(
                    lambda user: operator_group in user.all_group_ids
                )
                result = super().write(vals)
                lost_operators = operators.filtered(
                    lambda user: operator_group not in user.all_group_ids
                )
                self.env["im_livechat.channel"].sudo().search(
                    [("user_ids", "in", lost_operators.ids)]
                ).write(
                    {
                        "user_ids": [
                            Command.unlink(operator.id) for operator in lost_operators
                        ]
                    }
                )
                return result
        return super().write(vals)

    def _init_store_data(self, store: Store):
        super()._init_store_data(store)
        store.add_global_values(has_access_livechat=self.env.user.has_access_livechat)
        if not self.env.user._is_public():
            store.add(
                self.env.user,
                Store.Attr(
                    "is_livechat_manager",
                    lambda u: u.has_group("im_livechat.im_livechat_group_manager"),
                ),
            )
