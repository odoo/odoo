# -*- coding: utf-8 -*-
import json
import logging
import werkzeug.utils

from odoo import http
from odoo.http import request
from odoo.osv.expression import AND
from odoo.tools import convert, ustr
from odoo.modules.module import get_module_resource
from odoo.addons.http_routing.models.ir_http import url_for

_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route(['/pos/web', '/pos/ui'], type='http', auth='user')
    def pos_web(self, config_id=False, **k):
        """Open a pos session for the given config.

        The right pos session will be selected to open, if non is open yet a new session will be created.

        /pos/ui and /pos/web both can be used to acces the POS. On the SaaS,
        /pos/ui uses HTTPS while /pos/web uses HTTP.

        :param debug: The debug mode to load the session in.
        :type debug: str.
        :param config_id: id of the config that has to be loaded.
        :type config_id: str.
        :returns: object -- The rendered pos session.
        """
        domain = [
                ('state', 'in', ['opening_control', 'opened']),
                ('user_id', '=', request.session.uid),
                ('rescue', '=', False)
                ]
        if config_id:
            domain = AND([domain,[('config_id', '=', int(config_id))]])
        pos_session = request.env['pos.session'].sudo().search(domain, limit=1)

        # The same POS session can be opened by a different user => search without restricting to
        # current user. Note: the config must be explicitly given to avoid fallbacking on a random
        # session.
        if not pos_session and config_id:
            domain = [
                ('state', 'in', ['opening_control', 'opened']),
                ('rescue', '=', False),
                ('config_id', '=', int(config_id)),
            ]
            pos_session = request.env['pos.session'].sudo().search(domain, limit=1)

        if not pos_session:
            return werkzeug.utils.redirect('/web#action=point_of_sale.action_client_pos_menu')
        # The POS only work in one company, so we enforce the one of the session in the context
        session_info = request.env['ir.http'].session_info()
        session_info['user_context']['allowed_company_ids'] = pos_session.company_id.ids
        context = {
            'session_info': session_info,
            'login_number': pos_session.login(),
            'pos_session_id': pos_session.id,
        }
        return request.render('point_of_sale.index', qcontext=context)

    @http.route('/pos/ui/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        domain = [
            ('state', '=', 'opened'),
            ('user_id', '=', request.session.uid),
            ('rescue', '=', False)
        ]
        pos_session = request.env['pos.session'].sudo().search(domain, limit=1)
        session_info = request.env['ir.http'].session_info()
        session_info['user_context']['allowed_company_ids'] = pos_session.company_id.ids
        context = {
            'session_info': session_info,
        }
        return request.render('point_of_sale.qunit_suite', qcontext=context)

    @http.route('/pos/sale_details_report', type='http', auth='user')
    def print_sale_details(self, date_start=False, date_stop=False, **kw):
        r = request.env['report.point_of_sale.report_saledetails']
        pdf, _ = request.env.ref('point_of_sale.sale_details_report').with_context(date_start=date_start, date_stop=date_stop)._render_qweb_pdf(r)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route('/pos/load_onboarding_data', type='json', auth='user')
    def load_onboarding_data(self):
        convert.convert_file(request.env.cr, 'point_of_sale', 'data/point_of_sale_onboarding.xml', None, mode='init', kind='data')

    @http.route('/pos-service-worker', type='http', auth='user', methods=['GET'], sitemap=False)
    def service_worker(self):
        sw_file = get_module_resource('point_of_sale', 'static/src/js/pos-service-worker.js')
        with open(sw_file, 'rb') as fp:
            body = fp.read()
        response = request.make_response(body, [
            ('Content-Type', 'text/javascript'),
            ('Service-Worker-Allowed', url_for('/pos/')),
        ])
        return response

    @http.route('/pos/manifest.webmanifest', type='http', auth='user', methods=['GET'], sitemap=False)
    def webmanifest(self):
        manifest = {
            'name': 'Point of Sale',
            'short_name': 'POS',
            'description': 'User-friendly PoS interface for shops and restaurants',
            'scope': url_for('/pos/'),
            'display': 'standalone',
            'background_color': '#ffffff',
            'theme_color': '#875A7B',
        }
        icon_sizes = ['48', '72', '96', '144', '512']
        manifest['icons'] = [{
            'src': f'/point_of_sale/static/description/icon-{size}.png',
            'sizes': f'{size}x{size}',
            'type': 'image/png',
        } for size in icon_sizes]
        body = json.dumps(manifest, default=ustr)
        response = request.make_response(body, [
            ('Content-Type', 'application/manifest+json'),
        ])
        return response
