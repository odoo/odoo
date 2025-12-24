# -*- coding: utf-8 -*-
import os
import logging

_logger = logging.getLogger(__name__)

def configure_oauth(env):
    """Configuration Keycloak OAuth provider from environment variables."""
    try:
        base_url = os.getenv('VIA_SUITE_KEYCLOAK_BASE_URL', 'https://auth.viafronteira.com')
        realm = os.getenv('VIA_SUITE_KEYCLOAK_REALM', 'via-suite')
        client_id = os.getenv('VIA_SUITE_KEYCLOAK_CLIENT_ID', 'viasuite-odoo')
        
        # Update/Create Provider
        provider = env.ref('via_suite_base.oauth_provider_keycloak_viasuite', raise_if_not_found=False)
        if not provider:
             provider = env['auth.oauth.provider'].search([('name', '=', 'ViaSuite Keycloak')], limit=1)

        vals = {
            'name': 'ViaSuite Keycloak',
            'enabled': True,
            'client_id': client_id,
            'auth_endpoint': f'{base_url}/realms/{realm}/protocol/openid-connect/auth',
            'validation_endpoint': f'{base_url}/realms/{realm}/protocol/openid-connect/userinfo',
            'data_endpoint': f'{base_url}/realms/{realm}/protocol/openid-connect/token',
            'scope': 'openid profile email',
            'css_class': 'btn-primary',
            'sequence': 10,
        }
        
        if provider:
            provider.write(vals)
        else:
            env['auth.oauth.provider'].create(vals)
            
        # Update Config Params
        env['ir.config_parameter'].set_param('via_suite.keycloak.base_url', base_url)
        env['ir.config_parameter'].set_param('via_suite.keycloak.realm', realm)
        env['ir.config_parameter'].set_param('via_suite.keycloak.client_id', client_id)

        return True
    except Exception as e:
        _logger.error(f"Failed to configure OAuth: {str(e)}")
        return False
