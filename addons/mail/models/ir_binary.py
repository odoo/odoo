# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import AccessError


class IrBinary(models.AbstractModel):
    _inherit = "ir.binary"

    def _find_record_check_access(self, record, access_token, field, **kwargs):
        try:
            return super()._find_record_check_access(record, access_token, field, **kwargs)
        except AccessError:
            if (
                record._name in ["res.partner", "mail.guest"]
                and field == "avatar_128"
                and kwargs.get("thread_model")
                and kwargs.get("thread_id")
            ):
                thread = self.env[kwargs.pop("thread_model")]._get_thread_with_access(
                    int(kwargs.pop("thread_id")), **kwargs
                )
                if thread:
                    is_participant = (
                        record._name == "res.partner" and record in thread.message_ids.author_id
                    ) or (
                        record._name == "mail.guest"
                        and record in thread.message_ids.author_guest_id
                    )
                    if is_participant:
                        return record.sudo()
            raise
