# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.addons.mail.tools.discuss import Store


class CrmLead(models.Model):
    _inherit = "crm.lead"

    origin_channel_id = fields.Many2one(
        "discuss.channel",
        "Live chat from which the lead was created",
        readonly=True,
        index="btree_not_null",
    )

    @api.model_create_multi
    def create(self, vals_list):
        origin_channel_ids = [
            vals["origin_channel_id"] for vals in vals_list if vals.get("origin_channel_id")
        ]
        if not self.env["discuss.channel"].browse(origin_channel_ids).has_access("read"):
            raise AccessError(
                self.env._("You cannot create leads linked to channels you don't have access to.")
            )
        return super().create(vals_list)

    def write(self, vals):
        if origin_channel_id := vals.get("origin_channel_id"):
            if not self.env["discuss.channel"].browse(origin_channel_id).has_access("read"):
                raise AccessError(
                    self.env._(
                        "You cannot update a lead and link it to a channel you don't have access to."
                    )
                )
        return super().write(vals)

    def action_open_livechat(self):
        Store(bus_channel=self.env.user).add(
            self.origin_channel_id,
            extra_fields={"open_chat_window": True},
        ).bus_send()
