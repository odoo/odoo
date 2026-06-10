# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalMixin(models.AbstractModel):
    _inherit = 'portal.mixin'

    def _get_portal_website(self):
        self.ensure_one()
        # A record's own website takes precedence over its company's website
        if 'website_id' in self and self.website_id:
            return self.website_id
        if 'company_id' in self and self.company_id:
            website = self.env.website
            if website and website.company_id == self.company_id:
                return website
            return self.company_id.website_id
        return self.env.website
