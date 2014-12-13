import functools
import logging

import simplejson
import urlparse
import werkzeug.utils
from werkzeug.exceptions import BadRequest

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import db_monodb, ensure_db, set_cookie_and_redirect, login_and_redirect
from openerp.addons.auth_signup.controllers.main import AuthSignupHome as Home
from openerp.modules.registry import RegistryManager
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# helpers
#----------------------------------------------------------
def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, *a, **kw):
        kw.pop('debug', False)
        if not kw:
            return """<html><head><script>
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
            </script></head><body></body></html>"""
        return func(self, *a, **kw)
    return wrapper


#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class OAuthLogin(Home):
    def list_providers(self):
        try:
            provider_obj = request.registry.get('auth.oauth.provider')
            providers = provider_obj.search_read(request.cr, SUPERUSER_ID, [('enabled', '=', True), ('auth_endpoint', '!=', False), ('validation_endpoint', '!=', False)])
            # TODO in forwardport: remove conditions on 'auth_endpoint' and 'validation_endpoint' when these fields will be 'required' in model
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                debug=request.debug,
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=simplejson.dumps(state),
            )
            provider['auth_link'] = provider['auth_endpoint'] + '?' + werkzeug.url_encode(params)

        return providers

    def get_state(self, provider):
        redirect = request.params.get('redirect', 'web')
        if not redirect.startswith(('//', 'http://', 'https://')):
            redirect = '%s%s' % (request.httprequest.url_root, redirect)
        state = dict(
            d=request.session.db,
            p=provider['id'],
            r=werkzeug.url_quote_plus(redirect),
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
            return http.redirect_with_hash(request.params.get('redirect'))
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

    @http.route()
    def web_auth_signup(self, *args, **kw):
        providers = self.list_providers()
        if len(providers) == 1:
            werkzeug.exceptions.abort(werkzeug.utils.redirect(providers[0]['auth_link'], 303))
        response = super(OAuthLogin, self).web_auth_signup(*args, **kw)
        response.qcontext.update(providers=providers)
        return response

    @http.route()
    def web_auth_reset_password(self, *args, **kw):
        providers = self.list_providers()
        if len(providers) == 1:
            werkzeug.exceptions.abort(werkzeug.utils.redirect(providers[0]['auth_link'], 303))
        response = super(OAuthLogin, self).web_auth_reset_password(*args, **kw)
        response.qcontext.update(providers=providers)
        return response


class OAuthController(http.Controller):

    @http.route('/auth_oauth/signin', type='http', auth='none')
    @fragment_to_query_string
    def signin(self, **kw):
        state = simplejson.loads(kw['state'])
        dbname = state['d']
        provider = state['p']
        context = state.get('c', {})
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            try:
                u = registry.get('res.users')
                credentials = u.auth_oauth(cr, SUPERUSER_ID, provider, kw, context=context)
                cr.commit()
                action = state.get('a')
                menu = state.get('m')
                redirect = werkzeug.url_unquote_plus(state['r']) if state.get('r') else False
                url = '/web'
                if redirect:
                    url = redirect
                elif action:
                    url = '/web#action=%s' % action
                elif menu:
                    url = '/web#menu_id=%s' % menu
                return login_and_redirect(*credentials, redirect_url=url)
            except AttributeError:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (dbname,))
                url = "/web/login?oauth_error=1"
            except openerp.exceptions.AccessDenied:
                # oauth credentials not valid, user could be on a temporary session
                _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
                url = "/web/login?oauth_error=3"
                redirect = werkzeug.utils.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            except Exception, e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
                url = "/web/login?oauth_error=2"

        return set_cookie_and_redirect(url)

    @http.route('/auth_oauth/oea', type='http', auth='none')
    def oea(self, **kw):
        """login user via Odoo Account provider"""
        dbname = kw.pop('db', None)
        if not dbname:
            dbname = db_monodb()
        if not dbname:
            return BadRequest()

        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            IMD = registry['ir.model.data']
            try:
                model, provider_id = IMD.get_object_reference(cr, SUPERUSER_ID, 'auth_oauth', 'provider_openerp')
            except ValueError:
                return set_cookie_and_redirect('/web?db=%s' % dbname)
            assert model == 'auth.oauth.provider'

        state = {
            'd': dbname,
            'p': provider_id,
            'c': {'no_user_creation': True},
        }

        kw['state'] = simplejson.dumps(state)
        return self.signin(**kw)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
