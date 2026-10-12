# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError

from odoo.addons.website.models.mixins import WebsitePublishedMixin


class WebsitePublishedMultiMixin(WebsitePublishedMixin):
    _inherit = 'website.published.multi.mixin'

    def open_website_url(self):
        if self._name == 'hr.job' and not self.website_id:
            website_id = self.env['website'].search([
                ('company_id', '=', self.company_id.id),
            ], limit=1).id
            if not website_id:
                raise UserError(self.env._("No website found for the company. Please create a website for this company to be able to open the job offer on the website."))
            return self.env['website'].get_client_action(self.website_url, False, website_id)

        return super().open_website_url()
