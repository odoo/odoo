# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from contextlib import ExitStack

from werkzeug.urls import url_encode

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class Session(http.Controller):

    @http.route('/web/session/get_session_info', type='jsonrpc', auth='user', readonly=True)
    def get_session_info(self):
        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        request.session.touch()
        return request.env['ir.http'].session_info()

    @http.route('/web/session/authenticate', type='jsonrpc', auth="none", readonly=False)
    def authenticate(self, db, login, password, base_location=None):
        if not http.db_filter([db]):
            raise AccessError("Database not found.")  # pylint: disable=missing-gettext

        with ExitStack() as stack:
            if not request.db or request.db != db:
                # Use a new env only when no db on the request, which means the env was not set on in through `_serve_db`
                # or the db is different than the request db
                cr = stack.enter_context(odoo.modules.registry.Registry(db).cursor())
                env = odoo.api.Environment(cr, None, {})
            else:
                env = request.env

            credential = {'login': login, 'password': password, 'type': 'password'}
            auth_info = request.session.authenticate(env, credential)
            if auth_info['uid'] != request.session.uid:
                # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
                # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
                return {'uid': None}

            request.session.db = db
            request._save_session(env)

            return env['ir.http'].with_user(request.session.uid).session_info()

    @http.route('/web/session/modules', type='jsonrpc', auth='user', readonly=True)
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return list(request.env.registry._init_modules)

    @http.route('/web/session/check', type='jsonrpc', auth='user', readonly=True)
    def check(self):
        return  # ir.http@_authenticate does the job

    @http.route('/web/session/account', type='jsonrpc', auth='user', readonly=True)
    def account(self):
        ICP = request.env['ir.config_parameter'].sudo()
        params = {
            'response_type': 'token',
            'client_id': ICP.get_str('database.uuid'),
            'state': json.dumps({'d': request.db, 'u': ICP.get_str('web.base.url')}),
            'scope': 'userinfo',
        }
        return 'https://accounts.odoo.com/oauth2/auth?' + url_encode(params)

    @http.route('/web/session/destroy', type='jsonrpc', auth='user', readonly=True)
    def destroy(self):
        request.session.logout()

    @http.route('/web/session/logout', type='http', auth='none', methods=['POST'], readonly=True)
    def logout(self, redirect='/odoo'):
        request.session.logout(keep_db=True)
        return request.redirect(redirect, 303)
