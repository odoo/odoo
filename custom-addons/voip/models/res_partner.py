# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class Contact(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "voip.queue.mixin"]

    @api.model
    def get_contacts(self, offset, limit, search_terms):
        domain = ["|", ("phone", "!=", False), ("mobile", "!=", False)]
        if search_terms:
            search_fields = ["complete_name", "phone", "mobile", "email"]
            search_domain = expression.OR([[(field, "ilike", search_terms)] for field in search_fields])
            domain = expression.AND([domain, search_domain])
        return self.search(domain, offset=offset, limit=limit)._format_contacts()

    def _format_contacts(self):
        return [
            {
                "id": contact.id,
                "displayName": contact.display_name,
                "email": contact.email,
                "landlineNumber": contact.phone,
                "mobileNumber": contact.mobile,
                "name": contact.name,
            }
            for contact in self
        ]
