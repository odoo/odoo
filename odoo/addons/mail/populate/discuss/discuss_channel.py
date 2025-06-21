# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Channel(models.Model):
    _inherit = "discuss.channel"
    _populate_sizes = {"small": 150, "medium": 1000, "large": 10000}

    def _populate_factories(self):
        groups = self.env.ref("base.group_portal") + self.env.ref("base.group_user") + self.env.ref("base.group_system")

        def compute_group(values, counter, random):
            if values["channel_type"] == "channel" and random.randrange(2):
                return random.choice(groups.ids)
            return False

        return [
            ("name", populate.constant("channel_{counter}")),
            ("channel_type", populate.randomize(["channel", "group", "chat"], weights=[1, 2, 10])),
            ("description", populate.constant("channel_{counter}_description")),
            ("group_public_id", populate.compute(compute_group)),
        ]

    def _populate(self, size):
        # install_mode to prevent from automatically adding system as member
        return super(Channel, self.with_context(install_mode=True))._populate(size)
