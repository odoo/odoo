# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    """ Update of res.users class
        - add a preference about username for livechat purpose
    """
    _inherit = 'res.users'

    livechat_username = fields.Char(string='Livechat Username', compute='_compute_livechat_username', inverse='_inverse_livechat_username', store=False)
    livechat_lang_ids = fields.Many2many('res.lang', string='Livechat Languages', compute='_compute_livechat_lang_ids', inverse='_inverse_livechat_lang_ids', store=False)
    livechat_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        string="Live Chat Expertise",
        compute="_compute_livechat_expertise_ids",
        inverse="_inverse_livechat_expertise_ids",
        store=False,
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
    )
    has_access_livechat = fields.Boolean(compute='_compute_has_access_livechat', string='Has access to Livechat', store=False, readonly=True)
    is_in_call = fields.Boolean("Is in call", compute="_compute_is_in_call")

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

    @api.depends('res_users_settings_id.livechat_username')
    def _compute_livechat_username(self):
        for user in self:
            user.livechat_username = user.res_users_settings_id.livechat_username

    def _inverse_livechat_username(self):
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_username = user.livechat_username

    @api.depends('res_users_settings_id.livechat_lang_ids')
    def _compute_livechat_lang_ids(self):
        for user in self:
            user.livechat_lang_ids = user.res_users_settings_id.livechat_lang_ids

    def _inverse_livechat_lang_ids(self):
        for user in self:
            settings = self.env['res.users.settings']._find_or_create_for_user(user)
            settings.livechat_lang_ids = user.livechat_lang_ids

    @api.depends("res_users_settings_id.livechat_expertise_ids")
    def _compute_livechat_expertise_ids(self):
        for user in self:
            user.livechat_expertise_ids = user.res_users_settings_id.livechat_expertise_ids

    def _inverse_livechat_expertise_ids(self):
        for user in self:
            settings = self.env["res.users.settings"]._find_or_create_for_user(user)
            settings.livechat_expertise_ids = user.livechat_expertise_ids

    @api.depends("groups_id")
    def _compute_has_access_livechat(self):
        for user in self.sudo():
            user.has_access_livechat = user.has_group('im_livechat.im_livechat_group_user')

    @api.depends("partner_id.channel_member_ids.rtc_session_ids")
    def _compute_is_in_call(self):
        rtc_sessions = self.env["discuss.channel.rtc.session"].search(
            [("partner_id", "in", self.partner_id.ids)]
        )
        for user in self:
            user.is_in_call = user.partner_id in rtc_sessions.partner_id

    def _init_store_data(self, store: Store):
        super()._init_store_data(store)
        store.add_global_values(has_access_livechat=self.env.user.has_access_livechat)
