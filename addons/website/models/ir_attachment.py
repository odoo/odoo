# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.fields import Domain


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # Technical field used to resolve multiple attachments in a multi-website environment.
    key = fields.Char()
    website_id = fields.Many2one('website')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.website and 'website_id' not in vals:
                vals['website_id'] = self.env.website.id
        return super().create(vals_list)

    @api.model
    def get_serving_groups(self):
        return super().get_serving_groups() + ['website.group_website_designer']

    def _get_serve_attachment(self, url, extra_domain=None, order=None):
        extra_domain = Domain(extra_domain or Domain.TRUE) & self.env.website.website_domain()
        order = ('website_id, %s' % order) if order else 'website_id'
        return super()._get_serve_attachment(url, extra_domain, order)
