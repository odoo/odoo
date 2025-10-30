# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import models, fields, api
from odoo.addons.website.structured_data import StructuredData


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

    def _to_structured_data(self, website):
        self.ensure_one()
        name = self.display_name or self.name
        if not name:
            return False

        base_url = website.get_base_url()
        website_url = self.website or ''
        if website_url and not website_url.startswith(("http://", "https://")):
            website_url = werkzeug.urls.join(base_url, website_url)

        image_path = website.image_url(self, 'image_512')
        image_url = f'{base_url}{image_path}' if image_path else None

        structured_data = StructuredData(
            "Organization",
            name=name,
            url=website_url or base_url,
            logo=image_url,
        )

        street = self.street.strip() if self.street else None
        postal_code = self.zip.strip() if self.zip else None
        city = self.city.strip() if self.city else None
        region = self.state_id.name if self.state_id else None
        country = self.country_id.name if self.country_id else None
        if any((street, postal_code, city, region, country)):
            structured_data.add(
                "address",
                StructuredData(
                    "PostalAddress",
                    street_address=street,
                    postal_code=postal_code,
                    locality=city,
                    region=region,
                    country=country,
                )
            )

        return structured_data

    @api.depends('website_id')
    @api.depends_context('display_website')
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get('display_website') or not self.env.user.has_group('website.group_multi_website'):
            return
        for partner in self:
            if partner.website_id:
                partner.display_name += f' [{partner.website_id.name}]'
