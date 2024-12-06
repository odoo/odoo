# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, models, fields, _
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """Update of res.partner class to take into account the livechat username."""
    _inherit = 'res.partner'

    user_livechat_username = fields.Char(compute='_compute_user_livechat_username')

    def _search_for_channel_invite_to_store(self, store: Store, channel):
        super()._search_for_channel_invite_to_store(store, channel)
        if channel.channel_type != "livechat" or not self:
            return
        lang_name_by_code = dict(self.env["res.lang"].get_installed())
        invite_by_self_count_by_partner = dict(
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
                partner,
                {
                    "invite_by_self_count": invite_by_self_count_by_partner.get(partner, 0),
                    "is_available": partner in active_livechat_partners,
                    "lang_name": lang_name_by_code[partner.lang],
                },
            )

    @api.depends('user_ids.livechat_username')
    def _compute_user_livechat_username(self):
        for partner in self:
            partner.user_livechat_username = next(iter(partner.user_ids.mapped('livechat_username')), False)

    def _to_store(self, store: Store, fields, **kwargs):
        """Override to add name when user_livechat_username is not set."""
        super()._to_store(store, fields, **kwargs)
        if "user_livechat_username" in fields:
            store.add(self.filtered(lambda p: not p.user_livechat_username), "name")

    def _bus_send_history_message(self, channel, page_history):
        message_body = _("No history found")
        if page_history:
            message_body = Markup("<ul>%s</ul>") % (
                Markup("").join(
                    Markup('<li><a href="%(page)s" target="_blank">%(page)s</a></li>')
                    % {"page": page}
                    for page in page_history
                )
            )
        self._bus_send_transient_message(channel, message_body)

    def _can_return_content(self, field_name=None, access_token=None):
        """Custom access check allowing to retrieve an operator's avatar.

        Here, we assume that if you are a member of at least one
        im_livechat.channel, then it's ok to make your avatar publicly
        available.

        We also make the chatbot operator avatars publicly available."""
        if field_name == "avatar_128":
            domain = [("user_ids.partner_id", "=", self.id)]
            if self.env["im_livechat.channel"].sudo().search_count(domain, limit=1):
                return True
            domain = [("operator_partner_id", "=", self.id)]
            if self.env["chatbot.script"].sudo().search_count(domain, limit=1):
                return True
        return super()._can_return_content(field_name, access_token)
