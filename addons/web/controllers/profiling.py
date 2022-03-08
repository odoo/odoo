# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError
from odoo.http import Controller, request, Response, route

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
            return json.dumps(state)
        except UserError as e:
            return Response(response='error: %s' % e, status=500)

    @route(['/web/speedscope', '/web/speedscope/<model("ir.profile"):profile>'], type='http', sitemap=False, auth='user')
    def speedscope(self, profile=None):
        # don't server speedscope index if profiling is not enabled
        if not request.env['ir.profile']._enabled_until():
            return request.not_found()
        icp = request.env['ir.config_parameter']
        context = {
            'profile': profile,
            'url_root': request.httprequest.url_root,
            'cdn': icp.sudo().get_param('speedscope_cdn', "https://cdn.jsdelivr.net/npm/speedscope@1.13.0/dist/release/")
        }
        return request.render('web.view_speedscope_index', context)
