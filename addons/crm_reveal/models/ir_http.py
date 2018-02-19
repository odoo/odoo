# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from threading import Thread

from odoo import models, api
from odoo.http import request
from odoo.modules.registry import Registry


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls):
        response = super(IrHttp, cls)._dispatch()
        if response and getattr(response, 'status_code', 0) == 200 and hasattr(response, 'qcontext'):
            template = response.qcontext.get('response_template')
            if template:
                view = request.env['website'].get_template(template)
                if view:
                    url = request.httprequest.url
                    if request.env['http.url.track'].sudo().match_url(url):
                        if not request.session.get('s_db_id'):
                            session_vals = {'user_id': request.session.get('uid'), 'ip_address': request.httprequest.remote_addr}
                            s_db_id = request.env['http.session'].sudo().create_session(session_vals)
                            request.session['s_db_id'] = s_db_id

                        vals = {'user_id': request.session.get('uid'), 'session_id': request.session['s_db_id'], 'url': url}
                        request.env['http.pageview'].sudo().create_pageview(vals)

        return response
