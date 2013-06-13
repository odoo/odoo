import functools
import logging

import simplejson
import werkzeug.utils
from werkzeug.exceptions import BadRequest

import openerp
from openerp import SUPERUSER_ID
import openerp.addons.web.http as oeweb
from openerp.addons.web.controllers.main import db_monodb, set_cookie_and_redirect, login_and_redirect
from openerp.modules.registry import RegistryManager

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# helpers
#----------------------------------------------------------
def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, req, **kw):
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
        return func(self, req, **kw)
    return wrapper


#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class OAuthController(oeweb.Controller):
    _cp_path = '/auth_oauth'

    @oeweb.jsonrequest
    def list_providers(self, req, dbname):
        try:
            registry = RegistryManager.get(dbname)
            with registry.cursor() as cr:
                providers = registry.get('auth.oauth.provider')
                l = providers.read(cr, SUPERUSER_ID, providers.search(cr, SUPERUSER_ID, [('enabled', '=', True)]))
        except Exception:
            l = []
        return l

    @oeweb.httprequest
    @fragment_to_query_string
    def signin(self, req, **kw):
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
                url = '/'
                if action:
                    url = '/#action=%s' % action
                elif menu:
                    url = '/#menu_id=%s' % menu
                return login_and_redirect(req, *credentials, redirect_url=url)
            except AttributeError:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (dbname,))
                url = "/#action=login&oauth_error=1"
            except openerp.exceptions.AccessDenied:
                # oauth credentials not valid, user could be on a temporary session
                _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
                url = "/#action=login&oauth_error=3"
                redirect = werkzeug.utils.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            except Exception, e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
                url = "/#action=login&oauth_error=2"

        return set_cookie_and_redirect(req, url)

    @oeweb.httprequest
    def oea(self, req, **kw):
        """login user via OpenERP Account provider"""
        dbname = kw.pop('db', None)
        if not dbname:
            dbname = db_monodb(req)
        if not dbname:
            return BadRequest()

        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            IMD = registry['ir.model.data']
            model, provider_id = IMD.get_object_reference(cr, SUPERUSER_ID, 'auth_oauth', 'provider_openerp')
            assert model == 'auth.oauth.provider'

        state = {
            'd': dbname,
            'p': provider_id,
            'c': {'no_user_creation': True},
        }

        kw['state'] = simplejson.dumps(state)
        return self.signin(req, **kw)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
