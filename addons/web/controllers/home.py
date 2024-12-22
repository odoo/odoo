# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import psycopg2


import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools import ustr
from odoo.tools.translate import _
from .utils import ensure_db, _get_login_redirect_url, is_user_internal


_logger = logging.getLogger(__name__)


# Shared parameters for all login/signup flows
SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()


class Home(http.Controller):

    @http.route('/', type='http', auth="none")
    def index(self, s_action=None, db=None, **kw):
        if request.db and request.session.uid and not is_user_internal(request.session.uid):
            return request.redirect_query('/web/login_successful', query=request.params)
        return request.redirect_query('/web', query=request.params)

    # ideally, this route should be `auth="user"` but that don't work in non-monodb mode.
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):

        # Ensure we have both a database and a user
        ensure_db()
        if not request.session.uid:
            return request.redirect_query('/web/login', query=request.params, code=303)
        if kw.get('redirect'):
            return request.redirect(kw.get('redirect'), 303)
        if not security.check_session(request.session, request.env):
            raise http.SessionExpiredException("Session expired")
        if not is_user_internal(request.session.uid):
            return request.redirect('/web/login_successful', 303)

        # Side-effect, refresh the session lifetime
        request.session.touch()

        # Restore the user on the environment, it was lost due to auth="none"
        request.update_env(user=request.session.uid)
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return request.redirect('/web/login?error=access')

    @http.route('/web/webclient/load_menus/<string:unique>', type='http', auth='user', methods=['GET'])
    def web_load_menus(self, unique, lang=None):
        """
        Loads the menus for the webclient
        :param unique: this parameters is not used, but mandatory: it is used by the HTTP stack to make a unique request
        :param lang: language in which the menus should be loaded (only works if language is installed)
        :return: the menus (including the images in Base64)
        """
        if lang:
            request.update_context(lang=lang)

        menus = request.env["ir.ui.menu"].load_web_menus(request.session.debug)
        body = json.dumps(menus, default=ustr)
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'public, max-age=' + str(http.STATIC_CACHE_LONG)),
        ])
        return response

    def _login_redirect(self, uid, redirect=None):
        return _get_login_redirect_url(uid, redirect)

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        # simulate hybrid auth=user/auth=public, despite using auth=none to be able
        # to redirect users when no db is selected - cfr ensure_db()
        if request.env.uid is None:
            if request.session.uid is None:
                # no user -> auth=public with specific website public user
                request.env["ir.http"]._auth_method_public()
            else:
                # auth=user
                request.update_env(user=request.session.uid)

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            try:
                uid = request.session.authenticate(request.db, request.params['login'], request.params['password'])
                request.params['login_success'] = True
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/web/login_successful', type='http', auth='user', website=True, sitemap=False)
    def login_successful_external_user(self, **kwargs):
        """Landing page after successful login for external users (unused when portal is installed)."""
        valid_values = {k: v for k, v in kwargs.items() if k in LOGIN_SUCCESSFUL_PARAMS}
        return request.render('web.login_successful', valid_values)

    @http.route('/web/become', type='http', auth='user', sitemap=False)
    def switch_to_admin(self):
        uid = request.env.user.id
        if request.env.user._is_system():
            uid = request.session.uid = odoo.SUPERUSER_ID
            # invalidate session token cache as we've changed the uid
            request.env.registry.clear_cache()
            request.session.session_token = security.compute_session_token(request.session, request.env)

        return request.redirect(self._login_redirect(uid))

    @http.route('/web/health', type='http', auth='none', save_session=False)
    def health(self, db_server_status=False):
        health_info = {'status': 'pass'}
        status = 200
        if db_server_status:
            try:
                odoo.sql_db.db_connect('postgres').cursor().close()
                health_info['db_server_status'] = True
            except psycopg2.Error:
                health_info['db_server_status'] = False
                health_info['status'] = 'fail'
                status = 500
        data = json.dumps(health_info)
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers, status=status)

    @http.route(['/robots.txt'], type='http', auth="none")
    def robots(self, **kwargs):
        return "User-agent: *\nDisallow: /\n"
