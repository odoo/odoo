# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib

from odoo import SUPERUSER_ID, api, models


class Publisher_WarrantyContract(models.AbstractModel):
    _inherit = "publisher_warranty.contract"

    @api.model
    def _post_publisher_messages(self, messages):
        super()._post_publisher_messages(messages)
        user = self.env["res.users"].sudo().browse(SUPERUSER_ID)
        if poster := self.sudo().env.ref(
            "mail.channel_all_employees",
            raise_if_not_found=False,
        ):
            for message in messages:
                with contextlib.suppress(Exception):
                    poster.message_post(
                        body=message,
                        subtype_xmlid="mail.mt_comment",
                        partner_ids=[user.partner_id.id],
                    )
