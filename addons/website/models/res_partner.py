# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import api, models


def urlplus(url, params):
    return werkzeug.Href(url)(params or None)


class Partner(models.Model):

    _inherit = "res.partner"

    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        google_maps_api_key = self.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')
        if not google_maps_api_key:
            return False
        params = {
            'center': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.name_get()[0][1] or ''),
            'size': "%sx%s" % (width, height),
            'zoom': zoom,
            'sensor': 'false',
            'key': google_maps_api_key,
        }
        return urlplus('//maps.googleapis.com/maps/api/staticmap', params)

    @api.multi
    def google_map_link(self, zoom=10):
        params = {
            'q': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.name_get()[0][1] or ''),
            'z': zoom,
        }
        return urlplus('https://maps.google.com/maps', params)
