# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalMixin(models.AbstractModel):
    _inherit = 'portal.mixin'

    def _get_portal_website(self):
        self.ensure_one()
        return self.company_id.website_id if 'company_id' in self else self.env['website']
