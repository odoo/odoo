# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _compute_is_current_user_or_guest_author(self):
        super()._compute_is_current_user_or_guest_author()
        portal_data = self.env.context.get("portal_data", {})
        portal_partner = portal_data.get("portal_partner")
        portal_thread = portal_data.get("portal_thread")
        if (
            not portal_partner
            or not portal_thread
            or not isinstance(portal_partner, self.pool["res.partner"])
            or not isinstance(portal_thread, self.pool["mail.thread"])
        ):
            return
        for message in self:
            if (
                message.author_id == portal_partner
                and message.model == portal_thread._name
                and message.res_id == portal_thread.id
            ):
                message.is_current_user_or_guest_author = True
