from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _to_store_defaults(self):
        bot_com_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.odoobot_comment")
        return super()._to_store_defaults() + [Store.Attr("isOdoobotDiscussion", lambda m: m.subtype_id.id == bot_com_id),]

    def _to_store(self, store: Store, fields, **kwargs):
        super()._to_store(store, [f for f in fields if f != "subtype_id"], **kwargs)
        if "subtype_id" not in fields:
            return
        if "subtype_id" in fields:
            bot_com_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.odoobot_comment")
            for message in self:
                store.add(message, {"isOdoobotDiscussion": message.sudo().subtype_id.id == bot_com_id})
