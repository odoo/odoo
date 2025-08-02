# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.mail.tools.discuss import Store
from odoo.fields import Command


class ResUsers(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_channel_ids = fields.Many2many(
        "im_livechat.channel", "im_livechat_channel_im_user", "user_id", "channel_id"
    )
    livechat_username = fields.Char(
        string="Livechat Username",
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
        compute="_compute_livechat_username",
        inverse="_inverse_livechat_username",
        store=False,
    )
    livechat_lang_ids = fields.Many2many(
        "res.lang",
        string="Livechat Languages",
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
        compute="_compute_livechat_lang_ids",
        inverse="_inverse_livechat_lang_ids",
        store=False,
    )
    livechat_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        "im_livechat_expertise_res_users_rel",
        "user_id",
        "expertise_id",
        string="Live Chat Expertise",
        groups="im_livechat.im_livechat_group_user,base.group_erp_manager",
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
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
            # sudo - res.users: checking if user is in call is allowed if the user is member of a live chat channel.
            user.livechat_is_in_call = user.sudo().is_in_call if user.livechat_channel_ids else None

    @api.depends("livechat_channel_ids.channel_ids.livechat_end_dt", "partner_id")
    def _compute_livechat_ongoing_session_count(self):
        count_by_partner = dict(
            self.env["im_livechat.channel.member.history"]._read_group(
                [
                    ("channel_id.livechat_end_dt", "=", False),
                    ("partner_id", "in", self.partner_id.ids),
                ],
                ["partner_id"],
                ["__count"],
            )
        )
        for user in self:
            user.livechat_ongoing_session_count = count_by_partner.get(user.partner_id, 0)

    @api.depends('res_users_settings_id.livechat_username')
    def _compute_livechat_username(self):
        for user in self:
            # sudo: livechat user can see the livechat username of any other user
            user.livechat_username = user.sudo().res_users_settings_id.livechat_username

    def _inverse_livechat_username(self):
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_username = user.livechat_username

    @api.depends('res_users_settings_id.livechat_lang_ids')
    def _compute_livechat_lang_ids(self):
        for user in self:
            # sudo: livechat user can see the livechat languages of any other user
            user.livechat_lang_ids = user.sudo().res_users_settings_id.livechat_lang_ids

    def _inverse_livechat_lang_ids(self):
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_lang_ids = user.livechat_lang_ids

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

    def _init_store_data(self, store: Store):
        super()._init_store_data(store)
        store.add_global_values(has_access_livechat=self.env.user.has_access_livechat)
