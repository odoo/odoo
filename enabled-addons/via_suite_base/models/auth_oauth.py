# -*- coding: utf-8 -*-
"""
OAuth Authentication Customizations
====================================

Customizes OAuth authentication for ViaSuite:
- Keycloak integration
- Tenant validation
- Auto-user creation
"""

import requests
from odoo import models, api
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.via_suite_base.utils.logger import get_logger

logger = get_logger(__name__)


class AuthOAuthProvider(models.Model):
    """
    Extended OAuth Provider for ViaSuite Keycloak integration.
    """

    _inherit = 'auth.oauth.provider'

    @api.model
    def _get_keycloak_user_info(self, access_token, provider):
        """
        Get user information from Keycloak.

        Args:
            access_token (str): OAuth access token
            provider (auth.oauth.provider): OAuth provider record

        Returns:
            dict: User information from Keycloak including custom attributes
        """
        try:
            # Build userinfo endpoint URL
            userinfo_url = provider.validation_endpoint

            # Request user information
            response = requests.get(
                userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )

            response.raise_for_status()
            user_info = response.json()

            logger.info(
                "keycloak_userinfo_retrieved",
                email=user_info.get('email'),
                tenant=self.env.cr.dbname
            )

            return user_info

        except Exception as e:
            logger.error(
                "keycloak_userinfo_error",
                error=str(e),
                provider_id=provider.id
            )
            raise AccessDenied("Failed to retrieve user information from Keycloak")


class ResUsers(models.Model):
    """
    Extended res.users for OAuth tenant validation.
    """

    _inherit = 'res.users'

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """
        Override OAuth signin to add tenant validation.

        Validates that the user has access to the current tenant before
        allowing login.

        Args:
            provider (int): OAuth provider ID
            validation (dict): Validation response from OAuth provider
            params (dict): OAuth parameters

        Returns:
            tuple: (db, login, oauth_user_key)
        """
        try:
            # Get current database/tenant name
            current_tenant = self.env.cr.dbname

            # Get provider record
            oauth_provider = self.env['auth.oauth.provider'].browse(provider)

            # Get user info from Keycloak (includes custom attributes)
            access_token = params.get('access_token')
            if not access_token:
                raise AccessDenied("No access token provided")

            user_info = self.env['auth.oauth.provider']._get_keycloak_user_info(
                access_token,
                oauth_provider
            )

            # Extract email and tenant information
            email = user_info.get('email')
            if not email:
                raise AccessDenied("Email not provided by OAuth provider")

            # Get allowed tenants from Keycloak custom attributes
            # Keycloak sends custom attributes in the userinfo response
            allowed_tenants = user_info.get('via_suite_tenants', [])

            # Handle different formats (string or list)
            if isinstance(allowed_tenants, str):
                allowed_tenants = [t.strip() for t in allowed_tenants.split(',')]

            # Validate tenant access
            has_access = self._validate_tenant_access(
                current_tenant,
                allowed_tenants
            )

            if not has_access:
                logger.warning(
                    "oauth_tenant_access_denied",
                    email=email,
                    tenant=current_tenant,
                    allowed_tenants=allowed_tenants
                )
                raise AccessDenied(
                    f"User {email} does not have access to tenant: {current_tenant}"
                )

            # Find or create user
            user = self._find_or_create_oauth_user(email, user_info, provider)

            # Update via_suite_tenants field
            if allowed_tenants:
                tenant_str = ','.join(allowed_tenants) if isinstance(allowed_tenants, list) else allowed_tenants
                user.sudo().write({'via_suite_tenants': tenant_str})

            # Log successful OAuth login
            ip_address = None
            user_agent = None
            session_id = None

            if request:
                ip_address = request.httprequest.remote_addr
                user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')
                session_id = request.session.sid if hasattr(request, 'session') else None

            self.env['via.suite.login.audit'].sudo().log_login_event(
                user_id=user.id,
                event_type='login',
                login_method='oauth',
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )

            logger.info(
                "oauth_login_success",
                user_id=user.id,
                email=email,
                tenant=current_tenant,
                ip_address=ip_address
            )

            # Return login credentials
            return (self.env.cr.dbname, user.login, validation.get('user_id'))

        except AccessDenied:
            raise
        except Exception as e:
            logger.error(
                "oauth_signin_error",
                error=str(e),
                tenant=self.env.cr.dbname
            )
            raise AccessDenied(f"OAuth signin failed: {str(e)}")

    @api.model
    def _validate_tenant_access(self, tenant_name, allowed_tenants):
        """
        Validate if user has access to the current tenant.

        Args:
            tenant_name (str): Current tenant/database name
            allowed_tenants (list): List of allowed tenant names

        Returns:
            bool: True if access granted, False otherwise
        """
        # If no restrictions, allow access
        if not allowed_tenants:
            return True

        # Check for wildcard access
        if '*' in allowed_tenants:
            logger.info(
                "tenant_access_wildcard",
                tenant=tenant_name
            )
            return True

        # Check if tenant is in allowed list
        has_access = tenant_name in allowed_tenants

        logger.info(
            "tenant_access_check",
            tenant=tenant_name,
            allowed_tenants=allowed_tenants,
            has_access=has_access
        )

        return has_access

    @api.model
    def _find_or_create_oauth_user(self, email, user_info, provider_id):
        """
        Find existing user or create new user from OAuth information.

        Args:
            email (str): User email
            user_info (dict): User information from OAuth provider
            provider_id (int): OAuth provider ID

        Returns:
            res.users: User record
        """
        # Search for existing user
        user = self.search([('login', '=', email)], limit=1)

        if user:
            logger.info(
                "oauth_user_found",
                user_id=user.id,
                email=email
            )
            return user

        # Create new user
        user = self.create_oauth_user(user_info, provider_id)

        return user