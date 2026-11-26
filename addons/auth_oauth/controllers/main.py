# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import json
import logging
import secrets
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

import werkzeug.urls
from werkzeug.exceptions import BadRequest

from odoo import SUPERUSER_ID, _, api
from odoo.exceptions import AccessDenied
from odoo.http import Controller, request, route
from odoo.http.requestlib import fragment_to_query_string
from odoo.http.router import db_filter
from odoo.http.session import authenticate
from odoo.modules.registry import Registry
from odoo.tools import hash_sign, verify_hash_signed
from odoo.tools.date_utils import all_timezones
from odoo.tools.misc import clean_context

from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.utils import _get_login_redirect_url, ensure_db

_logger = logging.getLogger(__name__)

# How long an authorization request stays valid. Covers the time the user
# spends on the pages of the provider (consent, mfa, account recovery)
# NOTE: replays will be accepted in Odoo in that window, but should be
# rejected by the IDP server since a code verifier can only be used once
STATE_VALIDITY_HOURS = 1


def oauth_redirect_uri():
    """The redirect uri must be the very same on the authorization request and
    on the token request (RFC 6749 §4.1.3).
    """
    return request.httprequest.url_root + 'auth_oauth/signin'


# ----------------------------------------------------------
# Controller
# ----------------------------------------------------------
class OAuthLogin(Home):
    def list_providers(self):
        """List the enabled providers, as the buttons of the login page.

        The buttons only point to ``/web/login-with/<id>``: the authorization
        request itself (signed state, code challenge) is only issued when the
        user actually picks a provider, not on every rendering of the page.
        """
        try:
            # sudo: the login page is rendered for a visitor with no user yet
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        # carried over to /web/login-with, where get_state() reads them
        query = {
            key: request.params[key]
            for key in ('redirect', 'token')
            if request.params.get(key)
        }
        query_string = '?%s' % urlencode(query) if query else ''
        for provider in providers:
            provider['auth_link'] = '/web/login-with/%s%s' % (provider['id'], query_string)
            # these values end up in the qcontext of the login page
            provider.pop('client_secret', None)
        return providers

    @route('/web/login-with/<string:provider_ref>', type='http', auth='none', methods=['GET'], replica=False)  # nosemgrep: http-auth-none
    def web_login_with(self, provider_ref, **kw):
        """Send the user to the authorization endpoint of a provider.

        :param str provider_ref: the id of the provider, or its xmlid
        """
        ensure_db()
        # sudo: providers are reached before anyone is signed in
        Provider = request.env['auth.oauth.provider'].sudo()
        if provider_ref.isdigit():
            provider = Provider.browse(int(provider_ref))
        else:
            provider = request.env(su=True).ref(provider_ref, raise_if_not_found=False)
            if provider is None or provider._name != Provider._name:
                provider = Provider
        if not provider.exists().enabled:
            redirect = request.redirect('/web/login?oauth_error=provider_unavailable', 303)
            redirect.autocorrect_location_header = False
            return redirect
        if provider.flow == 'pkce':
            auth_link = self._get_pkce_auth_link(provider)
        else:
            auth_link = self._get_implicit_auth_link(provider)
        return request.redirect(auth_link, 303, local=False)

    def _get_implicit_auth_link(self, provider):
        """Build the authorization link of an implicit flow provider: the
        provider hands the access token over on the callback.

        :param provider: the ``auth.oauth.provider`` record
        :return: the authorization link
        :rtype: str
        """
        params = dict(
            response_type='token',
            client_id=provider['client_id'],
            redirect_uri=oauth_redirect_uri(),
            scope=provider['scope'],
            state=json.dumps(self.get_state(provider)),
        )
        return "%s?%s" % (provider['auth_endpoint'], urlencode(params))

    def _get_pkce_auth_link(self, provider):
        """Build the authorization link of a PKCE provider.

        Nothing is remembered server side: the state carries a signed nonce,
        and the code verifier is derived from it again on the way back.

        :param provider: the ``auth.oauth.provider`` record
        :return: the authorization link
        :rtype: str
        """
        state = self.get_state(provider)
        nonce = secrets.token_urlsafe(16)
        # just to avoid collision for the same session id, so 128 bits/16 bytes is plenty enough
        state['n'] = self._sign_pkce_state(state, nonce)
        # The session id is what binds the authorization request to this browser.
        code_verifier = provider._get_code_verifier(request.session.sid, nonce)
        params = dict(
            response_type='code',
            client_id=provider['client_id'],
            redirect_uri=oauth_redirect_uri(),
            scope=provider['scope'],
            state=json.dumps(state),
            code_challenge=provider._get_code_challenge(code_verifier),
            # the only method Odoo issues: "plain" would send the verifier itself
            code_challenge_method='S256',
        )
        return "%s?%s" % (provider['auth_endpoint'], urlencode(params))

    def _sign_pkce_state(self, state, nonce):
        """Sign the nonce of an authorization request along with the state it
        travels in, and return the signature to carry as ``state['n']``.
        """
        return hash_sign(
            request.env(su=True), "auth_oauth_pkce_state", [nonce, state],
            expiration_hours=STATE_VALIDITY_HOURS,
        )

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

    @route()
    def web_login(self, *args, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return request.redirect(request.params.get('redirect'))
        providers = self.list_providers()

        response = super().web_login(*args, **kw)
        if response.is_qweb:
            response.qcontext['providers'] = providers
            error = request.params.get('oauth_error')
            if error == 'signup_disabled':
                response.qcontext['error'] = _("Sign up is not allowed on this database.")
            elif error == 'access_denied':
                response.qcontext['error'] = _("Access Denied")
            elif error == 'provider_unavailable':
                response.qcontext['error'] = _("This login method is not available.")
            elif error == 'unauthorized':
                response.qcontext['error'] = _("You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")

        return response

    def get_auth_signup_qcontext(self):
        result = super().get_auth_signup_qcontext()
        result["providers"] = self.list_providers()
        return result


class OAuthController(Controller):

    @route('/auth_oauth/signin', type='http', auth='none', replica=False)
    @fragment_to_query_string
    def signin(self, **kw):
        return self._signin(kw)

    def _signin(self, kw, allow_disabled_provider=False):
        """Sign the user in from the callback of a provider.

        :param dict kw: the parameters of the callback
        :param bool allow_disabled_provider: let the sign in go through a
            provider that is not enabled. Never set from a request parameter,
            see ``oea``.
        """
        # the state is attacker controlled, nothing of it may be taken at face value
        try:
            state = json.loads(kw['state'])
        except (KeyError, ValueError):
            raise BadRequest()
        if not isinstance(state, dict):
            raise BadRequest()

        # make sure request.session.db and state['d'] are the same,
        # update the session and retry the request otherwise
        dbname = state.get('d')
        if not dbname or not db_filter([dbname]):
            raise BadRequest()
        ensure_db(db=dbname)

        provider_id = state.get('p')
        # sudo: the login page is reached without a user; the id is checked below
        provider = request.env['auth.oauth.provider'].with_user(SUPERUSER_ID).browse(provider_id).exists()
        if not provider or not (provider.enabled or allow_disabled_provider):
            # a provider that is not allowed any more must not sign anyone in,
            # whichever flow the callback claims to come back from
            raise BadRequest()

        # before anything of the callback is acted upon, whichever the flow:
        # the access token (implicit) or the code and its verifier (pkce) must
        # not reach a provider other than the one that issued the response
        try:
            self._validate_issuer(provider, kw)
        except AccessDenied:
            return self._oauth_error_redirect('access_denied')

        if provider.flow == 'pkce':
            # the provider hands over a single use authorization code, traded
            # here for the access token the rest of the sign in is the same
            # with as in the implicit flow; it hands over an error instead when
            # the user turned the authorization request down
            if error := kw.get('error'):
                _logger.info(
                    "OAuth2 PKCE: provider %r turned the authorization request down: %s",
                    provider.name, error,
                )
                return self._oauth_error_redirect('access_denied')
            try:
                kw['access_token'] = self._auth_oauth_pkce_token(provider, state, kw)
            except AccessDenied:
                return self._oauth_error_redirect('access_denied')

        request.update_context(**clean_context(state.get('c', {})))
        if browser_tz := request.cookies.get('tz'):
            tz = None
            with contextlib.suppress(KeyError, ValueError):
                tz = ZoneInfo(browser_tz).key
            if tz in all_timezones:
                request.update_context(signup_tz=tz)
        try:
            # auth_oauth may create a new user, the commit makes it
            # visible to authenticate()'s own transaction below
            _, login, key = request.env['res.users'].with_user(SUPERUSER_ID).auth_oauth(provider.id, kw)
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

            credential = {'login': login, 'token': key, 'type': 'oauth_token'}
            auth_info = authenticate(request.session, request.env, credential)
            resp = request.redirect(_get_login_redirect_url(auth_info['uid'], url), 303)
            resp.autocorrect_location_header = False

            # Since /web is hardcoded, verify user has right to land on it
            if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user._is_internal():
                resp.location = '/'
            return resp
        except AttributeError:  # TODO juc master: useless since ensure_db()
            # auth_signup is not installed
            _logger.error("auth_signup not installed on database %s: oauth sign up cancelled.", dbname)
            error = 'signup_disabled'
        except AccessDenied:
            # oauth credentials not valid, user could be on a temporary session
            _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
            error = 'unauthorized'
        except Exception:
            # signup error
            _logger.exception("Exception during request handling")
            error = 'access_denied'

        return self._oauth_error_redirect(error)

    def _validate_issuer(self, provider, params):
        """Make sure the authorization response comes from the provider the
        state names, countering the mix-up attack (RFC 9700 §4.4): a hostile
        provider A forwards the authorization request of the user to an honest
        provider B, whose response then comes back with the state of A. Acted
        upon as a response of A, it would hand B's access token (implicit) or
        B's code along with its verifier (pkce) over to A.

        Providers supporting RFC 9207 identify themselves with an ``iss``
        parameter on every authorization response, compared here (§2.4, plain
        string comparison) with the issuer configured on the provider. When
        the issuer is not configured, an ``iss`` is still checked against the
        origin of the authorization endpoint, which a response of another
        provider never comes from.

        :param provider: the ``auth.oauth.provider`` named by the state
        :param dict params: the parameters of the callback
        :raise AccessDenied: if the response does not come from ``provider``
        """
        iss = params.get('iss')
        if provider.issuer:
            if iss != provider.issuer:
                _logger.info(
                    "OAuth2: the callback of provider %r does not come from its "
                    "issuer %r but from %r",
                    provider.name, provider.issuer, iss,
                )
                raise AccessDenied()
        elif iss is not None:
            try:
                same_origin = urlsplit(iss)[:2] == urlsplit(provider.auth_endpoint)[:2]
            except (ValueError, AttributeError):  # not a url at all
                same_origin = False
            if not same_origin:
                _logger.info(
                    "OAuth2: the callback of provider %r comes from issuer %r, which "
                    "is not the origin of its authorization endpoint",
                    provider.name, iss,
                )
                raise AccessDenied()

    def _auth_oauth_pkce_token(self, provider, state, params):
        """Turn the authorization code of the callback into an access token, so
        that the rest of the sign in is the same as with the implicit flow.

        :raise AccessDenied: if the state does not check out or if the
            provider turns the exchange down
        """
        code = params.get('code')
        if not code:
            _logger.info(
                "OAuth2 PKCE: the callback of provider %r carries no authorization code",
                provider.name,
            )
            raise AccessDenied()
        nonce = self._verify_pkce_state(state)
        if not nonce:
            _logger.info(
                "OAuth2 PKCE: the state of this callback does not check out, the "
                "authorization request expired, was tampered with, or was not "
                "issued by this server"
            )
            raise AccessDenied()
        code_verifier = provider._get_code_verifier(request.session.sid, nonce)
        token = provider._exchange_code_for_token(code, code_verifier, oauth_redirect_uri())
        return token['access_token']

    def _verify_pkce_state(self, state):
        """Check the signature carried by the state and return the nonce it
        authenticates, or ``None`` when the state may not be trusted.
        """
        signature = state.pop("n", None)
        if not isinstance(signature, str):
            return None
        try:
            payload = verify_hash_signed(request.env(su=True), "auth_oauth_pkce_state", signature)
        except (ValueError, IndexError, UnicodeDecodeError):
            return None
        if not payload:  # tampered with, or past its expiration
            return None
        nonce, signed_state = payload
        if signed_state != {key: value for key, value in state.items() if key != "n"}:
            # the signature is genuine, the state it travels in is not the one
            # it was issued for
            return None
        return nonce

    def _oauth_error_redirect(self, error):
        """Send the user back to the login page, which displays the message of
        ``error``.

        :param str error: ``signup_disabled``, ``access_denied`` or
            ``unauthorized``, see ``OAuthLogin.web_login``
        """
        redirect = request.redirect("/web/login?oauth_error=%s" % error, 303)
        redirect.autocorrect_location_header = False
        return redirect

    @route('/auth_oauth/oea', type='http', auth='none', replica=False)
    def oea(self, **kw):
        """login user via Odoo Account provider"""
        dbname = kw.pop('db', None)
        if not dbname:
            dbname = request.db
        if not dbname:
            raise BadRequest()
        if not db_filter([dbname]):
            raise BadRequest()

        registry = Registry(dbname)
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
        # the Odoo.com provider backs the support login of the hosting platform:
        # it has to keep working on a database where it was disabled, which a
        # neutralized copy does to every provider
        return self._signin(kw, allow_disabled_provider=True)
