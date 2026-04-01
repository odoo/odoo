# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    call_history_ids = fields.One2many("discuss.call.history", "start_call_message_id")
    channel_id = fields.Many2one("discuss.channel", compute="_compute_channel_id")

    @api.depends("model", "res_id")
    def _compute_channel_id(self):
        for message in self:
            if message.model == "discuss.channel" and message.res_id:
                message.channel_id = self.env["discuss.channel"].browse(message.res_id)
            else:
                message.channel_id = False

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
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
                self.sudo().filtered(lambda message: message.channel_id),
                Store.One("parent_id", format_reply=False),
            )

    def _bus_channel(self):
        self.ensure_one()
        if self.channel_id:
            return self.channel_id
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_channel()
