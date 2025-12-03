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

    def _store_message_fields(self, res: Store.FieldList, **kwargs):
        super()._store_message_fields(res, **kwargs)
        res.many(
            "call_history_ids",
            ["duration_hour", "end_dt"],
            predicate=lambda m: m.body and 'data-oe-type="call"' in m.body,
        )

    def _store_extra_fields(self, res: Store.FieldList, *, format_reply):
        super()._store_extra_fields(res, format_reply=format_reply)
        if format_reply:
            # sudo: mail.message: access to parent is allowed
            res.one(
                "parent_id",
                "_store_message_fields",
                fields_params={"format_reply": False},
                predicate=lambda m: m.channel_id,
                sudo=True,
            )

    def _bus_channel(self):
        self.ensure_one()
        if self.channel_id:
            return self.channel_id
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_channel()
