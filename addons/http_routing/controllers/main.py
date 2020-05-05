# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http
from odoo.http import request, STATIC_CACHE_LONG
from odoo.addons.web.controllers.main import Home

class Routing(Home):

    @http.route('/website/translations/<string:unique>', type='http', auth="public", website=True)
    def get_website_translations(self, unique, lang, mods=None):
        if mods:
            mods = mods.split(',')
        translations_per_module, lang_params = request.env["ir.translation"]\
            .get_translations_for_webclient(mods, lang, frontend=True)

        body = json.dumps({
            'lang': lang,
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(request.env['res.lang'].sudo().get_installed()) > 1,
        })
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'public, max-age=' + str(STATIC_CACHE_LONG)),
        ])
        return response
