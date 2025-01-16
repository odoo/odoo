# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json

from odoo.exceptions import UserError
from odoo.http import Controller, request, Response, route, content_disposition


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
        '/web/speedscope/<profile>',
    ], type='http', sitemap=False, auth='user', readonly=True)
    def speedscope(self, profile=None, action=False, **kwargs):
        profiles = request.env['ir.profile'].browse(int(p) for p in profile.split(',')).exists()
        profile_str = profile
        if not profiles:
            raise request.not_found()
        params = kwargs or profiles._default_profile_params()
        speedscope_result = profiles._generate_speedscope(profiles._parse_params(params))
        if action == 'speedscope_download_json':
            headers = [
                ('Content-Type', 'application/json'),
                ('X-Content-Type-Options', 'nosniff'),
                ('Content-Disposition', content_disposition(f'profile_{profile_str}.json')),
            ]
            return request.make_response(speedscope_result, headers)
        icp = request.env['ir.config_parameter']
        context = {
            'profiles': profiles,
            'speedscope_base64': base64.b64encode(speedscope_result).decode('utf-8'),
            'url_root': request.httprequest.url_root,
            'cdn': icp.sudo().get_param('speedscope_cdn', "https://cdn.jsdelivr.net/npm/speedscope@1.13.0/dist/release/")
        }
        response = request.render('web.view_speedscope_index', context)
        if action == 'speedscope_download_html':
            response.headers['Content-Disposition'] = content_disposition(f'profile_{profile_str}.html')
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Content-Type'] = 'text/html'
        return response

    @route([
      '/web/profile_config/<profile>',
    ], type='http', sitemap=False, auth='user', readonly=True)
    def profile_config(self, profile=None, action=False, **kwargs):
        profile_str = profile
        profiles = request.env['ir.profile'].browse(int(p) for p in profile_str.split(',')).exists()
        if not profiles:
            raise request.not_found()

        if action == 'memory_open':
            memory_profile = profiles._generate_memory_profile(profiles._parse_params(kwargs))
            encoded_memory_profile = json.dumps(memory_profile).encode('utf_8')
            context = {
                'profile': profiles,
                'memory_graph': base64.b64encode(encoded_memory_profile).decode('utf-8'),
                }
            return request.render('web.view_memory', context)

        context = {
            'default_params': profiles._default_profile_params(),
            'profile_str': profile_str,
            'profiles': profiles,
        }
        return request.render('web.config_speedscope_index', context)
