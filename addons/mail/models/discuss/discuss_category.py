# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.web.models.models import lazymapping
from odoo.addons.mail.tools.discuss import Store


class DiscussCategory(models.Model):
    _name = "discuss.category"
    _description = "Discussion Category"
    _inherit = ["bus.sync.mixin"]

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    # description
    name = fields.Char("Name", required=True)
    channel_ids = fields.One2many("discuss.channel", "discuss_category_id", string="Channels")
    sequence = fields.Integer("Sequence", default=_default_sequence)

    # constraints
    _name_unique = models.Constraint("UNIQUE(name)", "The category name must be unique")

    def _sync_field_names(self, res):
        super()._sync_field_names(res)
        res[None].extend(["name", "sequence"])

    def _bus_channel(self):
        return self.channel_ids

    @api.ondelete(at_uninstall=False)
    def _unlink_sync_to_channel(self):
        stores = lazymapping(lambda channel: Store(bus_channel=channel))
        for category in self:
            for channel in category.channel_ids:
                stores[channel].delete(category)
        for store in stores.values():
            store.bus_send()
