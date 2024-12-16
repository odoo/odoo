# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, fields, models


class Im_LivechatExpertise(models.Model):
    """Expertise of Live Chat users."""

    _name = "im_livechat.expertise"
    _description = "Live Chat Expertise"
    _order = "name"

    name = fields.Char("Name", required=True, translate=True)
    user_ids = fields.Many2many(
        "res.users",
        string="Operators",
        compute="_compute_user_ids",
        inverse="_inverse_user_ids",
        store=False,
    )

    _name_unique = models.UniqueIndex("(name)")

    def _compute_user_ids(self):
        users_by_expertise = self._get_users_by_expertise()
        for expertise in self:
            expertise.user_ids = users_by_expertise[expertise]

    def _inverse_user_ids(self):
        users_by_expertise = self._get_users_by_expertise()
        for expertise in self:
            for user in expertise.user_ids - users_by_expertise[expertise]:
                # sudo: res.users: livechat manager can add expertise on users
                user.sudo().livechat_expertise_ids = [Command.link(expertise.id)]
            for user in users_by_expertise[expertise] - expertise.user_ids:
                # sudo: res.users: livechat manager can remove expertise on users
                user.sudo().livechat_expertise_ids = [Command.unlink(expertise.id)]

    def _get_users_by_expertise(self):
        users_by_expertise = defaultdict(lambda: self.env["res.users"])
        settings_domain = [("livechat_expertise_ids", "in", self.ids)]
        # sudo: res.users.settings: livechat manager can read expertise on users
        user_settings = self.env["res.users.settings"].sudo().search(settings_domain)
        for user_setting in user_settings:
            for expertise in user_setting.livechat_expertise_ids:
                users_by_expertise[expertise] |= user_setting.user_id
        for expertise, users in users_by_expertise.items():
            users_by_expertise[expertise] = users.with_prefetch(user_settings.user_id.ids)
        return users_by_expertise
