# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError
from odoo.http import Controller, request, Response, route
import urllib.parse

class Profiling(Controller):

    @route('/web/set_profiling', type='http', auth='public', sitemap=False)
    def profile(self, profile=None, collectors=None, **params):
        if collectors is not None:
            collectors = collectors.split(',')
        else:
            collectors = ['sql', 'traces_async']
        profile = profile and profile != '0'
        try:
            state = request.env['ir.profile'].set_profiling(profile, collectors=collectors, params=params)
            return Response(json.dumps(state), mimetype='application/json')
        except UserError as e:
            return Response(response='error: %s' % e, status=500, mimetype='text/plain')

    @route([
        '/web/speedscope',
        '/web/speedscope/<model("ir.profile"):profile>',
    ], type='http', sitemap=False, auth='user', readonly=True)
    def speedscope(self, profile=None, action=False, **kwargs):
        if profile and isinstance(profile, str):
            profile = request.env['ir.profile'].browse(int(profile))
        if not kwargs and not action:
            context = {
                'profile': profile,
            }
            return request.render('web.config_speedscope_index', context)
        icp = request.env['ir.config_parameter']
        context = {
            'profile': profile,
            'url_root': request.httprequest.url_root,
            'cdn': icp.sudo().get_param('speedscope_cdn', "https://cdn.jsdelivr.net/npm/speedscope@1.13.0/dist/release/")
        }
        if profile and action == 'download_json':
            url_params = urllib.parse.urlencode(kwargs)
            return request.redirect(f'/web/content/ir.profile/{profile.id}/speedscope?download=true&filename=profile_{profile.id}.json{"&" + url_params if url_params else ""}')
        response = request.render('web.view_speedscope_index', context)
        return response
