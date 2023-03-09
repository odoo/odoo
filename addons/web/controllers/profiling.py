# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError
from odoo.http import Controller, request, Response, route
from odoo.tools.json import scriptsafe as json_safe

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

    @route('/web/pev2/<model("ir.profile"):profile>/<float:start>', type="http", sitemap=False, auth='user')
    def pev2(self, profile, start):
        # don't serve PEV2 index if profiling is not enabled
        if not request.env['ir.profile']._enabled_until():
            return request.not_found()
        icp = request.env['ir.config_parameter']
        sql_dump = json.loads(profile.sql)
        query = next(sql for sql in sql_dump if sql['start'] == start)
        context = {
            'query': json_safe.dumps(query),
            'url_root': request.httprequest.url_root,
            'cdn': icp.sudo().get_param('pev2_cdn', "https://unpkg.com")
        }
        return request.render('web.view_pev2_index', context)
