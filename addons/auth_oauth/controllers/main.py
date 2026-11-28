# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import functools
import hashlib
import json
import logging
import os
import re
from datetime import timedelta

import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import BadRequest

from odoo import api, http, SUPERUSER_ID, _
from odoo.exceptions import AccessDenied
from odoo.http import request, Response
from odoo import registry as registry_get
from odoo.tools.misc import clean_context, consteq, hash_sign, verify_hash_signed

from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url


_logger = logging.getLogger(__name__)

NATIVE_REDIRECT_URL = 'com.odoo.mobile:/oauth'
NATIVE_FLOW_ID = re.compile(r'[0-9a-f]{32}')
NATIVE_CHALLENGE = re.compile(r'[A-Za-z0-9_-]{43}')
NATIVE_CODE_SCOPE = 'auth_oauth.native'
NATIVE_CODE_LIFETIME = timedelta(minutes=5)


#----------------------------------------------------------
# helpers
#----------------------------------------------------------
def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, *a, **kw):
        kw.pop('debug', False)
        if not kw:
            return Response("""<html><head><script>
                var l = window.location;
                var q = l.hash.substring(1);
                var r = l.pathname + l.search;
                if(q.length !== 0) {
                    var s = l.search ? (l.search === '?' ? '' : '&') : '?';
                    r = l.pathname + l.search + s + q;
                }
                if (r == l.pathname) {
                    r = '/';
                }
                window.location = r;
            </script></head><body></body></html>""")
        return func(self, *a, **kw)
    return wrapper


#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class OAuthLogin(Home):
    def list_providers(self):
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state),
                # nonce=base64.urlsafe_b64encode(os.urandom(16)),
            )
            provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return providers

    def get_state(self, provider):
        redirect = request.params.get('redirect') or 'web'
        if not redirect.startswith(('//', 'http://', 'https://')):
            redirect = '%s%s' % (request.httprequest.url_root, redirect[1:] if redirect[0] == '/' else redirect)
        state = dict(
            d=request.session.db,
            p=provider['id'],
            r=werkzeug.urls.url_quote_plus(redirect),
        )
        token = request.params.get('token')
        if token:
            state['t'] = token
        return state

    @http.route()
    def web_login(self, *args, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return request.redirect(request.params.get('redirect'))
        providers = self.list_providers()

        response = super(OAuthLogin, self).web_login(*args, **kw)
        if response.is_qweb:
            error = request.params.get('oauth_error')
            if error == '1':
                error = _("Sign up is not allowed on this database.")
            elif error == '2':
                error = _("Access Denied")
            elif error == '3':
                error = _("You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")
            else:
                error = None

            response.qcontext['providers'] = providers
            if error:
                response.qcontext['error'] = error

        return response

    def get_auth_signup_qcontext(self):
        result = super(OAuthLogin, self).get_auth_signup_qcontext()
        result["providers"] = self.list_providers()
        return result


class OAuthController(http.Controller):

    @http.route('/auth_oauth/signin', type='http', auth='none', readonly=False)
    @fragment_to_query_string
    def signin(self, **kw):
        state = json.loads(kw['state'])

        # make sure request.session.db and state['d'] are the same,
        # update the session and retry the request otherwise
        dbname = state['d']
        if not http.db_filter([dbname]):
            return BadRequest()
        ensure_db(db=dbname)

        provider = state['p']
        native_challenge = state.get('nc')
        native_flow = state.get('nf')
        if not (
            isinstance(native_challenge, str) and NATIVE_CHALLENGE.fullmatch(native_challenge)
            and isinstance(native_flow, str) and NATIVE_FLOW_ID.fullmatch(native_flow)
        ):
            native_challenge = native_flow = None
        request.update_context(**clean_context(state.get('c', {})))
        try:
            # auth_oauth may create a new user, the commit makes it
            # visible to authenticate()'s own transaction below
            _, login, key = request.env['res.users'].with_user(SUPERUSER_ID).auth_oauth(provider, kw)
            request.env.cr.commit()

            action = state.get('a')
            menu = state.get('m')
            redirect = werkzeug.urls.url_unquote_plus(state['r']) if state.get('r') else False
            url = '/odoo'
            if redirect:
                url = redirect
            elif action:
                url = '/odoo/action-%s' % action
            elif menu:
                url = '/odoo?menu_id=%s' % menu

            if native_challenge:
                # the mobile app opened this flow in a system browser tab: hand the
                # login over to the app instead of creating a session in that browser.
                # The code lives as long as the user may take to confirm.
                code = hash_sign(
                    request.env(su=True), NATIVE_CODE_SCOPE,
                    {'login': login, 'challenge': native_challenge, 'redirect': url},
                    expiration=NATIVE_CODE_LIFETIME,
                )
                return self._native_confirm(login, self._native_url(native_flow, db=dbname, code=code))

            return self._login_and_redirect(dbname, login, key, url)
        except AttributeError:  # TODO juc master: useless since ensure_db()
            # auth_signup is not installed
            _logger.error("auth_signup not installed on database %s: oauth sign up cancelled.", dbname)
            error = '1'
        except AccessDenied:
            # oauth credentials not valid, user could be on a temporary session
            _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
            error = '3'
        except Exception:
            # signup error
            _logger.exception("Exception during request handling")
            error = '2'

        if native_challenge:
            return self._native_redirect(native_flow, error=error)

        redirect = request.redirect(f"/web/login?oauth_error={error}", 303)
        redirect.autocorrect_location_header = False
        return redirect

    @http.route('/auth_oauth/native/exchange', type='http', auth='none', methods=['POST'], csrf=False, readonly=False)
    def native_exchange(self, db=None, code=None, verifier=None, **kw):
        """Exchange a code issued by signin() for a session, from the mobile
        app's own web view. The verifier proves that the caller is the app that
        started the flow, as the code itself went through a custom URL scheme.

        The app posts without a page to take a CSRF token from, so cross-site
        posts are rejected from the Sec-Fetch-Site and Origin headers instead."""
        headers = request.httprequest.headers
        origin = headers.get('Origin')
        if headers.get('Sec-Fetch-Site') not in (None, 'none', 'same-origin') or (
            origin not in (None, 'null') and origin != request.httprequest.host_url.rstrip('/')
        ):
            return BadRequest()
        if not (db and code and verifier) or not http.db_filter([db]):
            return BadRequest()
        ensure_db(db=db)

        try:
            payload = verify_hash_signed(request.env(su=True), NATIVE_CODE_SCOPE, code)
        except ValueError:
            payload = None
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        if not payload or not consteq(payload['challenge'], challenge):
            return request.redirect("/web/login?oauth_error=3", 303)

        user = request.env['res.users'].sudo().search([('login', '=', payload['login'])], limit=1)
        try:
            return self._login_and_redirect(db, user.login, user.oauth_access_token, payload['redirect'])
        except AccessDenied:
            return request.redirect("/web/login?oauth_error=3", 303)

    def _login_and_redirect(self, dbname, login, key, url):
        credential = {'login': login, 'token': key, 'type': 'oauth_token'}
        auth_info = request.session.authenticate(dbname, credential)
        resp = request.redirect(_get_login_redirect_url(auth_info['uid'], url), 303)
        resp.autocorrect_location_header = False

        # Since /web is hardcoded, verify user has right to land on it
        if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user._is_internal():
            resp.location = '/'
        return resp

    def _native_url(self, flow, **params):
        # one redirect URI per flow (RFC 8252 8.9/8.10): the app only accepts the one it started
        return f"{NATIVE_REDIRECT_URL}/{flow}?{werkzeug.urls.url_encode(params)}"

    def _native_redirect(self, flow, **params):
        resp = request.redirect(self._native_url(flow, **params), 303, local=False)
        resp.autocorrect_location_header = False
        return resp

    def _native_confirm(self, login, native_url):
        """Any app can claim the com.odoo.mobile scheme and start a flow with its
        own challenge, and a provider session completes the login without any
        interaction. The code is therefore only handed over once the user follows
        the link of this page (RFC 8252 8.6)."""
        request.env['ir.http']._auth_method_public()
        response = request.render('auth_oauth.native_confirm', {'login': login, 'native_url': native_url})
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        response.headers['Cache-Control'] = 'no-store'
        return response

    @http.route('/auth_oauth/oea', type='http', auth='none', readonly=False)
    def oea(self, **kw):
        """login user via Odoo Account provider"""
        dbname = kw.pop('db', None)
        if not dbname:
            dbname = request.db
        if not dbname:
            raise BadRequest()
        if not http.db_filter([dbname]):
            raise BadRequest()

        registry = registry_get(dbname)
        with registry.cursor() as cr:
            try:
                env = api.Environment(cr, SUPERUSER_ID, {})
                provider = env.ref('auth_oauth.provider_openerp')
            except ValueError:
                redirect = request.redirect(f'/web?db={dbname}', 303)
                redirect.autocorrect_location_header = False
                return redirect
            assert provider._name == 'auth.oauth.provider'

        state = {
            'd': dbname,
            'p': provider.id,
            'c': {'no_user_creation': True},
        }

        kw['state'] = json.dumps(state)
        return self.signin(**kw)
