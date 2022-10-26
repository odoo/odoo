# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request
from odoo.tools.json import scriptsafe


class GoogleMap(http.Controller):
    '''
    This class generates on-the-fly partner maps that can be reused in every
    website page. To do so, just use an ``<iframe ...>`` whose ``src``
    attribute points to ``/google_map`` (this controller generates a complete
    HTML5 page).

    URL query parameters:
    - ``partner_ids``: a comma-separated list of ids (partners to be shown)
    - ``partner_url``: the base-url to display the partner
        (eg: if ``partner_url`` is ``/partners/``, when the user will click on
        a partner on the map, it will be redirected to <myodoo>.com/partners/<id>)

    In order to resize the map, simply resize the ``iframe`` with CSS
    directives ``width`` and ``height``.
    '''

    @http.route(['/google_map'], type='http', auth="public", website=True, sitemap=False)
    def google_map(self, *arg, **post):
        clean_ids = []
        for partner_id in post.get('partner_ids', "").split(","):
            try:
                clean_ids.append(int(partner_id))
            except ValueError:
                pass
        partners = request.env['res.partner'].sudo().search([("id", "in", clean_ids),
                                                             ('website_published', '=', True), ('is_company', '=', True)])
        partner_data = {
            "counter": len(partners),
            "partners": []
        }
        for partner in partners.with_context(show_address=True):
            partner_data["partners"].append({
                'id': partner.id,
                'name': partner.name,
                'address': '\n'.join(partner.name_get()[0][1].split('\n')[1:]),
                'latitude': str(partner.partner_latitude) if partner.partner_latitude else False,
                'longitude': str(partner.partner_longitude) if partner.partner_longitude else False,
            })
        if 'customers' in post.get('partner_url', ''):
            partner_url = '/customers/'
        else:
            partner_url = '/partners/'

        google_maps_api_key = request.website.google_maps_api_key
        values = {
            'partner_url': partner_url,
            'partner_data': scriptsafe.dumps(partner_data),
            'google_maps_api_key': google_maps_api_key,
        }
        return request.render("website_google_map.google_map", values)
