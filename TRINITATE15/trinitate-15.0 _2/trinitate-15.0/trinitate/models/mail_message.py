# Copyright 2022 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class Message(models.Model):
    _inherit = "mail.message"

    def _update_content(self, body, attachment_ids):
        res = super()._update_content(body, attachment_ids)
        res_users = self.author_id.id
        res_partner = self.env["res.users"].search([("partner_id", "=", res_users)])
        if not res_partner.editable_messages:
            raise UserError(
                _("It is not possible to update or delete the message.\nPlease contact the administrator.")
            )
        return res
