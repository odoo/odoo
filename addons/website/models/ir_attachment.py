# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models, api
_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # Technical field used to resolve multiple attachments in a multi-website environment.
    key = fields.Char()
    website_id = fields.Many2one('website')

    @api.model_create_multi
    def create(self, vals_list):
        website = self.env['website'].get_current_website(fallback=False)
        for vals in vals_list:
            if website and 'website_id' not in vals and 'not_force_website_id' not in self.env.context:
                vals['website_id'] = website.id
        return super().create(vals_list)

    @api.model
    def get_serving_groups(self):
        return super().get_serving_groups() + ['website.group_website_designer']

    def _get_serve_attachment(self, url, extra_domain=None, order=None):
        website = self.env['website'].get_current_website()
        extra_domain = (extra_domain or []) + website.website_domain()
        order = ('website_id, %s' % order) if order else 'website_id'
        return super()._get_serve_attachment(url, extra_domain, order)
