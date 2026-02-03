# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from contextlib import ExitStack

from werkzeug.urls import url_encode

import odoo
import odoo.modules.registry
from odoo.exceptions import AccessError
from odoo.http import Controller, request, route
from odoo.http.router import db_filter
from odoo.http.session import authenticate, logout, touch

_logger = logging.getLogger(__name__)


class Session(Controller):

    @route('/web/session/get_session_info', type='jsonrpc', auth='user', readonly=True)
    def get_session_info(self):
        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        touch(request.session)
        return request.env['ir.http'].session_info()

    @route('/web/session/authenticate', type='jsonrpc', auth="none", readonly=False)
    def authenticate(self, db, login, password, base_location=None):
        if not db_filter([db]):
            e = "Database not found."
            raise AccessError(e)  # pylint: disable=missing-gettext

        with ExitStack() as stack:
            if not request.db or request.db != db:
                # Use a new env only when no db on the request, which means the env was not set on in through `_serve_db`
                # or the db is different than the request db
                cr = stack.enter_context(odoo.modules.registry.Registry(db).cursor())
                env = odoo.api.Environment(cr, None, {})
            else:
                env = request.env

            credential = {'login': login, 'password': password, 'type': 'password'}
            auth_info = authenticate(request.session, env, credential)
            if auth_info['uid'] != request.session.uid:
                # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
                # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
                return {'uid': None}

            request.session.db = db
            request._save_session(env)

            return env['ir.http'].with_user(request.session.uid).session_info()

    @route('/web/session/modules', type='jsonrpc', auth='user', readonly=True)
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return list(request.env.registry._init_modules)

    @route('/web/session/check', type='jsonrpc', auth='user', readonly=True)
    def check(self):
        return  # ir.http@_authenticate does the job

    @route('/web/session/account', type='jsonrpc', auth='user', readonly=True)
    def account(self):
        ICP = request.env['ir.config_parameter'].sudo()
        params = {
            'response_type': 'token',
            'client_id': ICP.get_str('database.uuid'),
            'state': json.dumps({'d': request.db, 'u': ICP.get_str('web.base.url')}),
            'scope': 'userinfo',
        }
        return 'https://accounts.odoo.com/oauth2/auth?' + url_encode(params)

    @route('/web/session/destroy', type='jsonrpc', auth='user', readonly=True)
    def destroy(self):
        logout(request.session)

    @route('/web/session/logout', type='http', auth='none', methods=['POST'], readonly=True)
    def logout(self, redirect='/odoo'):
        logout(request.session, keep_db=True)
        return request.redirect(redirect, 303)

    @route('/web/session/identity', type='http', auth='user', methods=['GET'], sitemap=False, check_identity=False)
    def session_identity(self, redirect=None):
        """ Display the authentication form in a page. Used when an HTTP call raises a `CheckIdentityException`. """
        return request.render('web.check_identity', {'redirect': redirect})

    # Cannot be readonly because checking the identity can lead to some data being written
    # (e.g. totp rate limit during a totp by mail)
    @route('/web/session/identity/check', type='jsonrpc', auth='user', methods=['POST'], check_identity=False)
    def session_identity_check(self, **kwargs):
        """ JSON route used to receive the authentication form sent by the user. """
        return request.env['ir.http']._check_identity(kwargs)
