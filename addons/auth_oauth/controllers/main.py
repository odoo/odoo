import functools
import logging

import simplejson
import werkzeug.utils
from werkzeug.exceptions import BadRequest

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request, LazyResponse
from openerp.addons.web.controllers.main import db_monodb, set_cookie_and_redirect, login_and_redirect
from openerp.modules.registry import RegistryManager
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# helpers
#----------------------------------------------------------
def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, *a, **kw):
        if not kw:
            return """<html><head><script>
                var l = window.location;
                var q = l.hash.substring(1);
                var r = '/' + l.search;
                if(q.length !== 0) {
                    var s = l.search ? (l.search === '?' ? '' : '&') : '?';
                    r = l.pathname + l.search + s + q;
                }
                window.location = r;
            </script></head><body></body></html>"""
        return func(self, *a, **kw)
    return wrapper

#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class OAuthLogin(openerp.addons.web.controllers.main.Home):
    def list_providers(self):
        try:
            provider_obj = request.registry.get('auth.oauth.provider')
            providers = provider_obj.search_read(request.cr, SUPERUSER_ID, [('enabled', '=', True)])
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
        return dict(
            d=request.session.db,
            p=provider['id']
        )

    @http.route()
    def web_login(self, *args, **kw):
        providers = self.list_providers()

        response = super(OAuthLogin, self).web_login(*args, **kw)
        if isinstance(response, LazyResponse):
            error = request.params.get('oauth_error')
            if error == '1':
                error = _("Sign up is not allowed on this database.")
            elif error == '2':
                error = _("Access Denied")
            elif error == '3':
                error = _("You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")
            else:
                error = None

            response.params['values']['providers'] = providers
            if error:
                response.params['values']['error'] = error

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
                url = '/web'
                if action:
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
        """login user via OpenERP Account provider"""
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
