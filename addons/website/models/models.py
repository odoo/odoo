# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def _can_return_content(self, field_name=None, access_token=None):
        if (
            "website_published" in self._fields
            and field_name in self._fields
            and not self._fields[field_name].groups
            and self.sudo().website_published
        ):
            return True
        return super()._can_return_content(field_name, access_token)
