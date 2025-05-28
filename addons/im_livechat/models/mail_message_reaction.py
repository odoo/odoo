from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessageReaction(models.Model):
    _name = "mail.message.reaction"
    _inherit = ["mail.message.reaction"]

    def _persona_to_store(self, store: Store):
        channel_reactions_with_partner = self.filtered(
            lambda r: r.partner_id and r.message_id.model == "discuss.channel"
        )
        channel_by_message = channel_reactions_with_partner.message_id._record_by_message()
        livechat_partner_reactions = channel_reactions_with_partner.filtered(
            lambda r: channel_by_message.get(r.message_id, self.env["discuss.channel"]).channel_type
            == "livechat"
        )
        super(MailMessageReaction, self - livechat_partner_reactions)._persona_to_store(store)
        store.add(
            livechat_partner_reactions.partner_id,
            fields=["avatar_128", *self.env["res.partner"]._get_store_livechat_username_fields()],
        )
