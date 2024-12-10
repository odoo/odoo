from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _to_store(self, store: Store, /, *, fields=None, **kwargs):
        super()._to_store(store, fields=fields, **kwargs)
        bot_com_id = self.env["ir.model.data"]._xmlid_to_res_id("mail.odoobot_comment")
        if fields is None:
            fields = ["subtype_id"]
        if "subtype_id" in fields:
            for message in self:
                store.add(message, {"isOdoobotDiscussion": message.sudo().subtype_id.id == bot_com_id})
