# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin, OAuthController
from odoo.addons.via_suite_base.exceptions import ViaSuiteAuthError
import logging

_logger = logging.getLogger(__name__)


class ViaSuiteLogin(OAuthLogin):
    """
    Override login to auto-redirect to Keycloak OAuth.
    
    Inherits from OAuthLogin to leverage native OAuth flow with
    fragment_to_query_string decorator for Implicit Flow support.
    """
    
    @http.route('/web/login', type='http', auth="none", website=True)
    def web_login(self, redirect=None, **kw):
        """
        Auto-redirect to Keycloak OAuth provider if not already authenticated.
        """
        # If user is already logged in, redirect to the app
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))
        
        # If there's an OAuth error, let super handle it
        if kw.get('oauth_error') or kw.get('via_error'):
            return super(ViaSuiteLogin, self).web_login(redirect=redirect, **kw)
        
        # Get the OAuth provider (use sudo since auth="none")
        try:
            provider = request.env.ref('via_suite_base.oauth_provider_keycloak_viasuite').sudo()
        except ValueError:
            provider = None
        
        if not provider or not provider.enabled:
            # Fallback to default login if OAuth is not configured
            _logger.warning("Keycloak OAuth provider not found or disabled, showing standard login")
            return super(ViaSuiteLogin, self).web_login(redirect=redirect, **kw)
        
        # Auto-redirect to Keycloak by using the auth_link from list_providers
        providers = self.list_providers()
        if providers:
            keycloak_provider = next((p for p in providers if p['id'] == provider.id), None)
            if keycloak_provider and keycloak_provider.get('auth_link'):
                _logger.info("Auto-redirecting to Keycloak SSO: %s", keycloak_provider['auth_link'])
                return request.redirect(keycloak_provider['auth_link'], local=False)
        
        # Fallback to standard login if something went wrong
        _logger.warning("Could not build Keycloak auth link, falling back to standard login")
        return super(ViaSuiteLogin, self).web_login(redirect=redirect, **kw)


class ViaSuiteOAuthController(OAuthController):
    """
    Override OAuth controller to catch custom exceptions and show branded error pages.
    """
    
    @http.route('/auth_oauth/signin', type='http', auth='none', readonly=False)
    def signin(self, **kw):
        """
        Override to catch ViaSuite custom exceptions and redirect with proper error codes.
        We must verify the logic manually because super().signin catches AccessDenied
        and swallows our custom error codes.
        """
        from odoo.addons.auth_oauth.controllers.main import fragment_to_query_string
        from odoo.modules.registry import Registry
        from odoo import api, http
        import json
        import werkzeug.urls
        
        # Apply the fragment_to_query_string decorator manually logic
        if not kw:
            from odoo.http import Response
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
        
        # Core logic copied from auth_oauth to allow custom exception handling
        from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url
        from odoo.tools.misc import clean_context
        
        state = json.loads(kw['state'])
        dbname = state['d']
        if not http.db_filter([dbname]):
            return http.request.not_found()
        
        ensure_db(db=dbname)
        request.update_context(**clean_context(state.get('c', {})))
        
        provider = state['p']
        
        try:
            # Check directly using current implementation
            _, login, key = request.env['res.users'].with_user(api.SUPERUSER_ID).auth_oauth(provider, kw)
            
            # Commit not typically needed with request.env as it auto-commits on success, 
            # but auth_oauth does it to make user visible to authenticate's transaction if created.
            request.env.cr.commit()
            
            action = state.get('a')
            menu = state.get('m')
            redirect = werkzeug.urls.url_unquote_plus(state['r']) if state.get('r') else False
            url = '/web'
            if redirect:
                url = redirect
            elif action:
                url = '/web#action=%s' % action
            elif menu:
                url = '/web#menu_id=%s' % menu
            
            # Correct authentication flow
            credential = {'login': login, 'token': key, 'type': 'oauth_token'}
            auth_info = request.session.authenticate(request.env, credential)
            resp = request.redirect(_get_login_redirect_url(auth_info['uid'], url), 303)
            resp.autocorrect_location_header = False
            return resp
            
        except ViaSuiteAuthError as e:
            # CATCH CUSTOM ERRORS HERE
            _logger.warning("ViaSuite Auth Error: %s - %s", e.error_code, str(e))
            return request.redirect(f"/web/login?via_error={e.error_code}")
                
        except AttributeError as e:
            # auth_signup not installed
            _logger.exception("AttributeError during OAuth signin (check if auth_signup is installed or other attribute error): %s", e)
            _logger.error("auth_signup not installed on database %s: oauth signin cancelled." % (dbname,))
            return request.redirect("/web/login?oauth_error=1")
            
        except http.AccessDenied:
            # oauth credentials not valid, user not on a specific authorize list
            _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
            return request.redirect("/web/login?oauth_error=3")
            
        except Exception as e:
            # oauth providers not correctly configured, etc
            _logger.exception("OAuth2: %s" % str(e))
            return request.redirect("/web/login?oauth_error=2")






