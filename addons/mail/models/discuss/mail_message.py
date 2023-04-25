# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _message_format_extras(self, format_reply):
        self.ensure_one()
        vals = super()._message_format_extras(format_reply)
        if format_reply and self.model == "discuss.channel" and self.parent_id:
            vals["parentMessage"] = self.parent_id.message_format(format_reply=False)[0]
        return vals

    def _bus_notification_target(self):
        self.ensure_one()
        if self.model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest
        return super()._bus_notification_target()
