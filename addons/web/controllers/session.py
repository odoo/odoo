# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import operator

from werkzeug.urls import url_encode

import odoo
import odoo.modules.registry
from odoo import http
from odoo.modules import module
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.http import request
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


class Session(http.Controller):

    @http.route('/web/session/get_session_info', type='json', auth="user")
    def get_session_info(self):
        # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@)
        request.session.touch()
        return request.env['ir.http'].session_info()

    @http.route('/web/session/authenticate', type='json', auth="none")
    def authenticate(self, db, login, password, base_location=None):
        if not http.db_filter([db]):
            raise AccessError("Database not found.")
        pre_uid = request.session.authenticate(db, login, password)
        if pre_uid != request.session.uid:
            # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
            # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
            return {'uid': None}

        request.session.db = db
        registry = odoo.modules.registry.Registry(db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, request.session.uid, request.session.context)
            if not request.db:
                # request._save_session would not update the session_token
                # as it lacks an environment, rotating the session myself
                http.root.session_store.rotate(request.session, env)
                request.future_response.set_cookie(
                    'session_id', request.session.sid,
                    max_age=http.SESSION_LIFETIME, httponly=True
                )
            return env['ir.http'].session_info()

    @http.route('/web/session/get_lang_list', type='json', auth="none")
    def get_lang_list(self):
        try:
            return http.dispatch_rpc('db', 'list_lang', []) or []
        except Exception as e:
            return {"error": e, "title": _("Languages")}

    @http.route('/web/session/modules', type='json', auth="user")
    def modules(self):
        # return all installed modules. Web client is smart enough to not load a module twice
        return list(request.env.registry._init_modules.union([module.current_test] if module.current_test else []))

    @http.route('/web/session/check', type='json', auth="user")
    def check(self):
        return  # ir.http@_authenticate does the job

    @http.route('/web/session/account', type='json', auth="user")
    def account(self):
        ICP = request.env['ir.config_parameter'].sudo()
        params = {
            'response_type': 'token',
            'client_id': ICP.get_param('database.uuid') or '',
            'state': json.dumps({'d': request.db, 'u': ICP.get_param('web.base.url')}),
            'scope': 'userinfo',
        }
        return 'https://accounts.odoo.com/oauth2/auth?' + url_encode(params)

    @http.route('/web/session/destroy', type='json', auth="user")
    def destroy(self):
        request.session.logout()

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        request.session.logout(keep_db=True)
        return request.redirect(redirect, 303)
