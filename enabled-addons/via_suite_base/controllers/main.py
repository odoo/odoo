# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin
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
        if kw.get('oauth_error'):
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






