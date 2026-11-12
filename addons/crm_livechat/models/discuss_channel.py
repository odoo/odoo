# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _prepare_lead_create_values(self, partner, key):
        values = super()._prepare_lead_create_values(partner, key)
        if self.channel_type == "livechat":
            values["partner_id"] = self.livechat_customer_partner_ids[:1].id
            values["source_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_source_livechat").id
            values["medium_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_medium_website").id
        return values

    def _types_allowing_lead_command(self):
        return super()._types_allowing_lead_command() + ["livechat"]

    def _store_livechat_extra_fields(self, res: Store.FieldList):
        super()._store_livechat_extra_fields(res)
        if not self.env["crm.lead"].has_access("read"):
            return
        res.many(
            "livechat_customer_partner_ids",
            lambda res: res.many("opportunity_ids", ["name"]),
            only_data=True,
        )
