# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _prepare_channel_lead_create_vals(self, partner, key):
        vals = super()._prepare_channel_lead_create_vals(partner, key)
        if self.channel_type != "livechat":
            return vals
        vals["partner_id"] = self.livechat_customer_partner_ids[0].id if self.livechat_customer_partner_ids else False
        vals["source_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_source_livechat").id
        vals["medium_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_medium_website").id
        return vals

    def _store_livechat_extra_fields(self, res: Store.FieldList):
        super()._store_livechat_extra_fields(res)
        if not self.env["crm.lead"].has_access("read"):
            return
        res.many(
            "livechat_customer_partner_ids",
            lambda res: res.many("opportunity_ids", ["name"]),
            only_data=True,
        )

    def _types_allowing_create_lead(self):
        return super()._types_allowing_create_lead() + ["livechat"]
