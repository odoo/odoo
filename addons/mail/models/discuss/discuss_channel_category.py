# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class ChannelCategory(models.Model):
    _name = "discuss.channel.category"
    _description = "Channel Category"

    name = fields.Char("Channel category name", required=True)
    channel_ids = fields.One2many("discuss.channel", "channel_category_id", string="Channels")
    sequence = fields.Integer(string='Sequence', default=5)

    def get_channels(self):
        self.ensure_one()
        return Store(self.channel_ids).get_result()

    def _to_store(self, store: Store):
        """Adds channel categories data to the given store."""
        fields = {"name": True, "sequence": True}
        for category in self:
            data = category._read_format(list(fields), load=False)[0]
            store.add(category, data)
