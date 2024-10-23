# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.addons.portal.utils import get_portal_partner


class MailMessage(models.Model):
    _inherit = ['mail.message']

    def _is_editable_in_portal(self, **kwargs):
        self.ensure_one()
        if self.model and self.res_id and self.env.user._is_public():
            thread = request.env[self.model].browse(self.res_id)
            partner = get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            )
            if partner and self.author_id == partner:
                return True
        return False
