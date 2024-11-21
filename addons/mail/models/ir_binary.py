# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = ["ir.binary"]

    def _find_record_check_access(self, record, access_token, field):
        if record._name in ["res.partner", "mail.guest"] and field == "avatar_128":
            # access to the avatar is allowed if there is access to the messages
            if record._name == "res.partner":
                domain = [("author_id", "=", record.id)]
            else:
                domain = [("author_guest_id", "=", record.id)]
            if self.env["mail.message"].search_count(domain, limit=1):
                return record.sudo()
        return super()._find_record_check_access(record, access_token, field)
