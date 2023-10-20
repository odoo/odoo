# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ChannelMember(models.Model):
    _inherit = "discuss.channel.member"
    _populate_dependencies = ["res.partner", "res.users", "discuss.channel"]

    def _populate(self, size):
        res = super()._populate(size)
        random = populate.Random("discuss.channel.member")
        channels = self.env["discuss.channel"].browse(self.env.registry.populated_models["discuss.channel"])
        users = self.env["res.users"].browse(self.env.registry.populated_models["res.users"])
        users = users.filtered(lambda user: user.active)
        admin = self.env.ref("base.user_admin")
        members = []
        for channel in channels:
            allowed_users = users
            if channel.channel_type == "channel" and channel.group_public_id:
                if channel.group_public_id in admin.groups_id:
                    members.append({"partner_id": admin.partner_id.id, "channel_id": channel.id})
                allowed_users = users.filtered(lambda user: channel.group_public_id in user.groups_id)
            elif channel.channel_type in ["channel", "group"]:
                members.append({"partner_id": admin.partner_id.id, "channel_id": channel.id})
            if allowed_users:
                # arbitrary limit of 20 for non-channel type to have a functionally significant number
                max_members = len(allowed_users) if channel.channel_type == "channel" else min(20, len(allowed_users))
                for user in random.sample(allowed_users, random.randrange(max_members)):
                    members.append({"partner_id": user.partner_id.id, "channel_id": channel.id})
        return res + self.env["discuss.channel.member"].create(members)
