# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import models, fields, api
from odoo.addons.website.tools.jsonld_builder import JsonLd


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.published.multi.mixin']

    visitor_ids = fields.One2many('website.visitor', 'partner_id', string='Visitors')

    def google_map_img(self, zoom=8, width=298, height=298):
        google_maps_api_key = self.env['website'].get_current_website().google_maps_api_key
        if not google_maps_api_key:
            return False
        params = {
            'center': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.display_name or ''),
            'size': "%sx%s" % (width, height),
            'zoom': zoom,
            'sensor': 'false',
            'key': google_maps_api_key,
        }
        return '//maps.googleapis.com/maps/api/staticmap?' + werkzeug.urls.url_encode(params)

    def google_map_link(self, zoom=10):
        params = {
            'q': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.display_name or ''),
            'z': zoom,
        }
        return 'https://maps.google.com/maps?' + werkzeug.urls.url_encode(params)

    @api.depends('website_id')
    @api.depends_context('display_website')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get('display_website') or not self.env.user.has_group('website.group_multi_website'):
            return
        for partner in self:
            if partner.website_id:
                partner.display_name += f' [{partner.website_id.name}]'

    def _to_organization_structured_data(self, website, image_url=None, use_logo=False):
        """Build partner-based Organization JSON-LD."""
        self.ensure_one()
        base_url = website.get_base_url()

        org_schema = JsonLd(
            "Organization",
            name=self.display_name,
            url=(self.website and self.website.strip()) or f"{base_url}{self.website_url}",
            telephone=self.phone,
            email=self.email,
        )
        if image_url is None and self.image_1920:
            image_url = f"{base_url}{website.image_url(self, 'image_1920')}"
        if image_url:
            org_schema.add_nested(**{('logo' if use_logo else 'image'): JsonLd("ImageObject", url=image_url)})

        org_schema.add_nested(
            address=website.postal_address_structured_data(
                street=self.street,
                street2=self.street2,
                city=self.city,
                zip=self.zip,
                state_code=self.state_id.code,
                country_code=self.country_id.code,
            ),
        )
        return org_schema
