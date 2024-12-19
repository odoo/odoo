# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError
from odoo.http import Controller, request, Response, route, content_disposition
import base64
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
        '/web/speedscope/config',
        '/web/speedscope/config/<model("ir.profile"):profile>',
    ], type='http', sitemap=False, auth='user', readonly=True)
    def speedscope_config(self, profile=None):
        context = {
            'profile': profile,
        }
        return request.render('web.config_speedscope_index', context)

    @route([
        '/web/speedscope',
        '/web/speedscope/<model("ir.profile"):profile>',
    ], type='http', sitemap=False, auth='user', readonly=True)
    def speedscope(self, profile=None):
        icp = request.env['ir.config_parameter']
        context = {
            'profile': profile,
            'url_root': request.httprequest.url_root,
            'cdn': icp.sudo().get_param('speedscope_cdn', "https://cdn.jsdelivr.net/npm/speedscope@1.13.0/dist/release/")
        }
        context['search_params'] = urllib.parse.quote(urllib.parse.urlencode(request.httprequest.args))
        return request.render('web.view_speedscope_index', context)
