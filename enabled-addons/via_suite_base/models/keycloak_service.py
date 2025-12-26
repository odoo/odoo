# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class KeycloakService(models.AbstractModel):
    _name = 'via_suite.keycloak.service'
    _description = 'Keycloak Admin API Service'

    def _get_config(self):
        """Get Keycloak configuration from system parameters."""
        params = self.env['ir.config_parameter'].sudo()
        return {
            'base_url': params.get_param('via_suite.keycloak.base_url'),
            'realm': params.get_param('via_suite.keycloak.realm'),
            'client_id': params.get_param('via_suite.keycloak.client_id'),
            'client_secret': params.get_param('via_suite.keycloak.client_secret'),
        }

    def _get_admin_token(self):
        """Authenticate with Keycloak using Client Credentials."""
        config = self._get_config()
        if not all([config['base_url'], config['realm'], config['client_id'], config['client_secret']]):
            _logger.error("Keycloak configuration is incomplete.")
            return False

        url = f"{config['base_url'].rstrip('/')}/realms/{config['realm']}/protocol/openid-connect/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': config['client_id'],
            'client_secret': config['client_secret']
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            _logger.error("Failed to get Keycloak admin token: %s", str(e))
            return False

    def _api_call(self, method, endpoint, data=None, params=None):
        """Execute a call to the Keycloak Admin API."""
        config = self._get_config()
        token = self._get_admin_token()
        if not token:
            return False

        url = f"{config['base_url'].rstrip('/')}/admin/realms/{config['realm']}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request(method, url, json=data, params=params, headers=headers, timeout=10)
            if response.status_code == 409:
                _logger.warning("Keycloak API Conflict (409): %s", response.text)
                return 'CONFLICT'
            response.raise_for_status()
            if response.status_code == 201: # Created
                # Keycloak returns the location of the new resource in headers
                return response.headers.get('Location', True)
            if response.status_code == 204: # No Content
                return True
            return response.json()
        except Exception as e:
            _logger.error("Keycloak API Call Failed [%s %s]: %s", method, endpoint, str(e))
            return False

    def upsert_user(self, user):
        """
        Create or update user in Keycloak.
        :param user: res.users record
        """
        # First, check if user exists in Keycloak by email
        email = user.login
        existing_users = self._api_call('GET', 'users', params={'email': email, 'exact': True})
        
        user_data = {
            'username': email,
            'email': email,
            'firstName': user.name.split(' ')[0] if user.name else '',
            'lastName': ' '.join(user.name.split(' ')[1:]) if user.name and len(user.name.split(' ')) > 1 else '',
            'enabled': user.active,
            'attributes': {
                'tenant': [self.env.cr.dbname.replace('via-suite-', '')]
            }
        }

        if existing_users and isinstance(existing_users, list):
            # Update
            kc_user_id = existing_users[0]['id']
            _logger.info("Updating existing user %s in Keycloak (ID: %s)", email, kc_user_id)
            return self._api_call('PUT', f'users/{kc_user_id}', data=user_data)
        else:
            # Create
            _logger.info("Creating new user %s in Keycloak", email)
            user_data['emailVerified'] = True # Assume verified since Odoo admin created it
            result = self._api_call('POST', 'users', data=user_data)
            
            # If conflict (email already exists in another tenant or mapped differently)
            if result == 'CONFLICT':
                 _logger.warning("User %s already exists in Keycloak (Conflict).", email)
                 return False
            return result

    def delete_user(self, user):
        """Delete user from Keycloak."""
        email = user.login
        existing_users = self._api_call('GET', 'users', params={'email': email, 'exact': True})
        if existing_users and isinstance(existing_users, list):
            kc_user_id = existing_users[0]['id']
            _logger.info("Deleting user %s from Keycloak (ID: %s)", email, kc_user_id)
            return self._api_call('DELETE', f'users/{kc_user_id}')
        return True
