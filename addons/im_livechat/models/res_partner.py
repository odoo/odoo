# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.addons.mail.tools.discuss import Store


class Partners(models.Model):
    """Update of res.partner class to take into account the livechat username."""
    _inherit = 'res.partner'

    user_livechat_username = fields.Char(compute='_compute_user_livechat_username')

    def _search_for_channel_invite_to_store(self, store: Store, channel):
        super()._search_for_channel_invite_to_store(store, channel)
        if channel.channel_type != "livechat" or not self:
            return
        lang_name_by_code = dict(self.env["res.lang"].get_installed())
        invite_by_self_count_by_partner_id = dict(
            self.env["discuss.channel.member"]._read_group(
                [["create_uid", "=", self.env.user.id], ["partner_id", "in", self.ids]],
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )
        active_livechat_partners = (
            self.env["im_livechat.channel"].search([]).available_operator_ids.partner_id
        )
        for partner in self:
            store.add(
                "Persona",
                {
                    "invite_by_self_count": invite_by_self_count_by_partner_id.get(partner, 0),
                    "is_available": partner in active_livechat_partners,
                    "lang_name": lang_name_by_code[partner.lang],
                    "id": partner.id,
                    "type": "partner",
                },
            )

    @api.depends('user_ids.livechat_username')
    def _compute_user_livechat_username(self):
        for partner in self:
            partner.user_livechat_username = next(iter(partner.user_ids.mapped('livechat_username')), False)

    def _to_store(self, store: Store, fields=None):
        super()._to_store(store, fields=fields)
        if fields and fields.get("user_livechat_username"):
            for partner in self:
                data = {"id": partner.id, "type": "partner"}
                if partner.user_livechat_username:
                    data["user_livechat_username"] = partner.user_livechat_username
                else:
                    data["name"] = partner.name
                store.add("Persona", data)
