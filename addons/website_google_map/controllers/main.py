# -*- coding: utf-8 -*-

import json
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request


class google_map(http.Controller):
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

    @http.route(['/google_map'], type='http', auth="public", website=True)
    def google_map(self, *arg, **post):
        cr, uid, context = request.cr, request.uid, request.context
        partner_obj = request.registry['res.partner']

        # filter real ints from query parameters and build a domain
        clean_ids = []
        for s in post.get('partner_ids', "").split(","):
            try:
                i = int(s)
                clean_ids.append(i)
            except ValueError:
                pass

        # search for partners that can be displayed on a map
        domain = [("id", "in", clean_ids), ('website_published', '=', True), ('is_company', '=', True)]
        partners_ids = partner_obj.search(cr, SUPERUSER_ID, domain, context=context)

        # browse and format data
        partner_data = {
        "counter": len(partners_ids),
        "partners": []
        }
        request.context.update({'show_address': True})
        for partner in partner_obj.browse(cr, SUPERUSER_ID, partners_ids, context=context):
            partner_data["partners"].append({
                'id': partner.id,
                'name': partner.name,
                'address': '\n'.join(partner.name_get()[0][1].split('\n')[1:]),
                'latitude': partner.partner_latitude,
                'longitude': partner.partner_longitude,
                })

        # generate the map
        values = {
            'partner_url': post.get('partner_url'),
            'partner_data': json.dumps(partner_data)
        }
        return request.website.render("website_google_map.google_map", values)
