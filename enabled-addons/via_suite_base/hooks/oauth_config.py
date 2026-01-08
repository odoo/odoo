# -*- coding: utf-8 -*-
import os
import logging

_logger = logging.getLogger(__name__)

def configure_oauth(env):
    """
    Configure Keycloak OAuth provider from environment variables.
    
    Sets up:
    1. OAuth Provider (auth.oauth.provider)
    2. System Parameters for Keycloak configuration
    """
    try:
        # Get env vars with defaults, handling empty strings
        base_url = os.getenv('VIA_SUITE_KEYCLOAK_BASE_URL') or 'https://auth.viafronteira.com'
        realm = os.getenv('VIA_SUITE_KEYCLOAK_REALM') or 'master'
        client_id = os.getenv('VIA_SUITE_KEYCLOAK_CLIENT_ID') or 'via-suite'
        client_secret = os.getenv('VIA_SUITE_KEYCLOAK_CLIENT_SECRET') or 'TOfcFxlhdu4pVBhiT9xS47aqtfX39AAf'
        
        _logger.info("Configuring Keycloak with base_url: %s, realm: %s", base_url, realm)

        # Build Keycloak endpoints
        auth_endpoint = f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/auth"
        token_endpoint = f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        userinfo_endpoint = f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/userinfo"
        
        # Update OAuth Provider
        oauth_provider = env.ref('via_suite_base.oauth_provider_keycloak_viasuite', raise_if_not_found=False)
        
        if not oauth_provider:
            oauth_provider = env['auth.oauth.provider'].search([
                ('name', '=', 'ViaSuite Keycloak')
            ], limit=1)
        
        vals = {
            'name': 'ViaSuite Keycloak',
            'client_id': client_id,
            'body': 'Sign in with ViaSuite',
            'auth_endpoint': auth_endpoint,
            'scope': 'openid profile email',
            'validation_endpoint': userinfo_endpoint,
            'data_endpoint': False,  # Must be False for Implicit Flow
            'enabled': bool(client_secret),
            'css_class': 'btn-primary',
            'sequence': 10,
        }
        
        if oauth_provider:
            oauth_provider.write(vals)
        else:
            env['auth.oauth.provider'].create(vals)
        
        # Update System Parameters
        params = {
            'via_suite.keycloak.base_url': base_url,
            'via_suite.keycloak.realm': realm,
            'via_suite.keycloak.client_id': client_id,
            'via_suite.keycloak.client_secret': client_secret,
        }
        
        for key, value in params.items():
            env['ir.config_parameter'].sudo().set_param(key, value)
        
        return True
        
    except Exception as e:
        _logger.error(f"Failed to configure OAuth provider: {str(e)}")
        return False
