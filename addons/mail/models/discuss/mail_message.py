# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _gather_notification_dependencies(self):
        deps = super()._gather_notification_dependencies()
        for message in self:
            if not message.notification_data:
                continue
            match message.notification_data["type"]:
                case "channel-joined":
                    deps["res.partner"]["fields"].update(message._get_notification_partner_fields())
                    deps["mail.guest"]["fields"].add("name")
                    inviter = message.notification_data["payload"]["inviter_persona"]
                    inviter_model = "res.partner" if inviter["type"] == "partner" else "mail.guest"
                    deps[inviter_model]["ids"].add(inviter["id"])
                    invitee = message.notification_data["payload"]["invitee_persona"]
                    invitee_model = "res.partner" if invitee["type"] == "partner" else "mail.guest"
                    deps[invitee_model]["ids"].add(invitee["id"])
        return deps

    def _get_notification_partner_fields(self):
        return ["name"]

    def _extras_to_store(self, store: Store, format_reply):
        super()._extras_to_store(store, format_reply=format_reply)
        if format_reply:
            # sudo: mail.message: access to parent is allowed
            store.add(
                self.sudo().filtered(lambda message: message.model == "discuss.channel"),
                Store.One("parent_id", format_reply=False, rename="parentMessage"),
            )

    def _bus_channel(self):
        self.ensure_one()
        if self.model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)._bus_channel()
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest._bus_channel()
        return super()._bus_channel()
