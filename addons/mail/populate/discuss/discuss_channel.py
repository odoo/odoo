# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Channel(models.Model):
    _inherit = "discuss.channel"
    _populate_dependencies = ["res.partner"]
    _populate_sizes = {"small": 10, "medium": 100, "large": 500}

    def _populate_factories(self):
        return [
            ("name", populate.constant("channel_{counter}")),
            ("channel_type", populate.randomize(["channel", "group"])),
            ("description", populate.constant("channel_{counter}_description")),
        ]
