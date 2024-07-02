# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _validate_access_for_current_persona(self, operation):
        if not self:
            return False
        self.ensure_one()
        if self.env.user._is_public():
            guest = self.env["mail.guest"]._get_guest_from_context()
            # sudo: mail.guest - current guest can read channels they are member of
            return guest and self.model == "discuss.channel" and self.res_id in guest.sudo().channel_ids.ids
        return super()._validate_access_for_current_persona(operation)

    def _extras_to_store(self, store: Store, format_reply):
        super()._extras_to_store(store, format_reply=format_reply)
        if format_reply:
            # sudo: mail.message: access to parent is allowed
            for message in self.sudo().filtered(lambda message: message.model == "discuss.channel"):
                if message.parent_id:
                    store.add(message.parent_id, format_reply=False)
                store.add(
                    "Message",
                    {
                        "id": message.id,
                        "parentMessage": (
                            {"id": message.parent_id.id} if message.parent_id else False
                        ),
                    },
                )

    def _bus_notification_target(self):
        self.ensure_one()
        if self.model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_notification_target()
