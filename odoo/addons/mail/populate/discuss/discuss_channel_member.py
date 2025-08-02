# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


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
        # group batches by channel because chat members must be created in the same batch to satisfy contraints
        users_by_channel = defaultdict(list)
        big_done = 0
        big = min(300, len(users))
        chat_with_admin = 0
        admin_dm_size = {"small": 25, "medium": 100, "large": 500}[size]
        for channel in channels:
            allowed_users = users
            if channel.channel_type == "channel" and channel.group_public_id:
                if random.randint(1, 2) == 1 and channel.group_public_id in admin.groups_id:
                    users_by_channel[channel].append(admin)
                allowed_users = users.filtered(lambda user: channel.group_public_id in user.groups_id)
            elif random.randint(1, 2) == 1 and channel.channel_type in ["channel", "group"]:
                users_by_channel[channel].append(admin)
            if allowed_users:
                # arbitrary limit of 20 for non-channel type to have a functionally significant number
                max_users = len(allowed_users) if channel.channel_type == "channel" else min(20, len(allowed_users))
                number_users = (
                    random.choices([1, 2], weights=[1, 100], k=1)[0]
                    if channel.channel_type == "chat"
                    else big
                    if big_done < 2 and channel.channel_type == "channel"
                    else random.randrange(max_users)
                )
                if number_users >= big and admin in users_by_channel[channel]:
                    big_done += 1
                if chat_with_admin < admin_dm_size and channel.channel_type == "chat" and random.randint(1, 2) == 1:
                    users_by_channel[channel].extend([admin, random.choice(allowed_users)])
                    chat_with_admin += 1
                else:
                    users_by_channel[channel].extend(random.sample(allowed_users, number_users))
        batches = [[]]
        i = 0
        total = 0
        for channel, users in users_by_channel.items():
            if len(batches[i]) > 1000:
                i += 1
                batches.append([])
            batches[i].extend({"channel_id": channel.id, "partner_id": user.partner_id.id} for user in users)
            total += len(users)
        count = 0
        for batch in batches:
            count += len(batch)
            _logger.info("Batch of discuss.channel.member: %s/%s", count, total)
            res += self.env["discuss.channel.member"].create(batch)
        return res
