# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    call_history_ids = fields.One2many("discuss.call.history", "start_call_message_id")

    def _to_store_defaults(self):
        return super()._to_store_defaults() + [
            Store.Many(
                "call_history_ids",
                ["duration_hour", "end_dt"],
                predicate=lambda m: m.body and 'data-oe-type="call"' in m.body,
            ),
        ]

    def _extras_to_store(self, store: Store, format_reply):
        super()._extras_to_store(store, format_reply=format_reply)
        if format_reply:
            # sudo: mail.message: access to parent is allowed
            store.add(
                self.sudo().filtered(lambda message: message.model == "discuss.channel"),
                Store.One("parent_id", format_reply=False),
            )

    def _bus_channel(self):
        self.ensure_one()
        if self.model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)._bus_channel()
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest._bus_channel()
        return super()._bus_channel()
