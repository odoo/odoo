# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
import json
import werkzeug
import logging

_logger = logging.getLogger(__name__)


class ViaSuiteLogin(Home):
    """
    Override login to auto-redirect to Keycloak OAuth.
    """
    
    @http.route('/web/login', type='http', auth="none", website=True)
    def web_login(self, redirect=None, **kw):
        """
        Auto-redirect to Keycloak OAuth provider if not already authenticated.
        """
        # If user is already logged in, redirect to the app
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))
        
        # If there's an OAuth error return, let super handle it (it translates error codes into messages)
        if kw.get('oauth_error'):
            return super(ViaSuiteLogin, self).web_login(redirect=redirect, **kw)
        
        # Get the OAuth provider (use sudo since auth="none")
        try:
            provider = request.env.ref('via_suite_base.oauth_provider_keycloak_viasuite').sudo()
        except ValueError:
            provider = None
        
        if not provider or not provider.enabled:
            # Fallback to default login if OAuth is not configured
            return super(ViaSuiteLogin, self).web_login(redirect=redirect, **kw)
        
        # Ensure auth_endpoint is absolute
        # Prefer system parameter for base_url if auth_endpoint is relative
        auth_endpoint = provider.auth_endpoint
        if auth_endpoint and not auth_endpoint.startswith(('http://', 'https://')):
            base_url = request.env['ir.config_parameter'].sudo().get_param('via_suite.keycloak.base_url')
            if not base_url:
                # Fallback to hardcoded default if parameter is missing
                base_url = 'https://auth.viafronteira.com'
            auth_endpoint = f"{base_url.rstrip('/')}/{auth_endpoint.lstrip('/')}"
        
        # Build OAuth URL exactly like the button does
        # Make redirect_uri dynamic based on the current host
        base_url_request = request.httprequest.host_url.rstrip('/')
        redirect_uri = f"{base_url_request}/auth_oauth/signin"
        
        _logger.info("Redirecting to Keycloak: %s (redirect_uri: %s)", auth_endpoint, redirect_uri)
        
        params = {
            'response_type': 'token',
            'client_id': provider.client_id,
            'redirect_uri': redirect_uri,
            'scope': provider.scope or 'openid profile email',
            'state': json.dumps({'d': request.env.cr.dbname, 'p': provider.id, 'r': redirect or '/web'}),
        }
        
        # Build the URL and ensure it's absolute for the redirect
        oauth_url = f"{auth_endpoint}?{werkzeug.urls.url_encode(params)}"
        
        # local=False is CRITICAL for Odoo not to strip the domain
        return request.redirect(oauth_url, local=False)






