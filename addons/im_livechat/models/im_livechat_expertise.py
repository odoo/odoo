from collections import defaultdict

from odoo import Command, fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class Im_LivechatExpertise(models.Model):
    _name = "im_livechat.expertise"
    _description = "Live Chat Expertise"
    _order = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Operators",
        compute="_compute_user_ids",
        inverse="_inverse_user_ids",
        store=False,
    )

    _name_src_uniq = name_uniq_index(
        message="An expertise with this name already exists.",
    )

    def _compute_user_ids(self):
        users_by_expertise = self._get_users_by_expertise()
        for expertise in self:
            expertise.user_ids = users_by_expertise[expertise]

    def _inverse_user_ids(self):
        users_by_expertise = self._get_users_by_expertise()
        for expertise in self:
            for user in expertise.user_ids - users_by_expertise[expertise]:
                user.sudo().livechat_expertise_ids = [Command.link(expertise.id)]
            for user in users_by_expertise[expertise] - expertise.user_ids:
                user.sudo().livechat_expertise_ids = [Command.unlink(expertise.id)]

    def _get_users_by_expertise(self):
        users_by_expertise = defaultdict(lambda: self.env["res.users"])
        settings_domain = [("livechat_expertise_ids", "in", self.ids)]
        user_settings = self.env["res.users.settings"].sudo().search(settings_domain)
        for user_setting in user_settings:
            for expertise in user_setting.livechat_expertise_ids:
                users_by_expertise[expertise] |= user_setting.user_id
        for expertise, users in users_by_expertise.items():
            users_by_expertise[expertise] = users.with_prefetch(
                user_settings.user_id.ids
            )
        return users_by_expertise
