# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.web.models.models import lazymapping
from odoo.addons.mail.tools.discuss import Store


class DiscussCategory(models.Model):
    _name = "discuss.category"
    _description = "Discussion Category"

    # description
    name = fields.Char("Name", required=True)
    channel_ids = fields.One2many("discuss.channel", "discuss_category_id", string="Channels")

    # constraints
    _name_unique = models.Constraint("UNIQUE(name)", "The category name must be unique")

    def write(self, vals):
        if "name" in vals:
            old_name_by_category = {category: category.name for category in self}
            result = super().write(vals)
            stores = lazymapping(lambda channel: Store(bus_channel=channel))
            for category in self:
                if old_name_by_category[category] == vals["name"]:
                    continue
                for channel in category.channel_ids:
                    stores[channel].add(category, ["name"])
            for store in stores.values():
                store.bus_send()
            return result
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_sync_to_channel(self):
        stores = lazymapping(lambda channel: Store(bus_channel=channel))
        for category in self:
            for channel in category.channel_ids:
                stores[channel].delete(category)
        for store in stores.values():
            store.bus_send()
