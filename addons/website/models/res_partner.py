# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import models, fields

class Partner(models.Model):
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
        return '//maps.googleapis.com/maps/api/staticmap?'+werkzeug.urls.url_encode(params)

    def google_map_link(self, zoom=10):
        params = {
            'q': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.display_name or ''),
            'z': zoom,
        }
        return 'https://maps.google.com/maps?' + werkzeug.urls.url_encode(params)

    def _get_name(self):
        name = super(Partner, self)._get_name()
        if self._context.get('display_website') and self.env.user.has_group('website.group_multi_website'):
            if self.website_id:
                name += ' [%s]' % self.website_id.name
        return name

    def _compute_display_name(self):
        self2 = self.with_context(display_website=False)
        super(Partner, self2)._compute_display_name()
