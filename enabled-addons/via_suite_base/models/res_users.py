# -*- coding: utf-8 -*-
"""
User Model Customizations
==========================

Customizes res.users for ViaSuite:
- Extended session timeout (24h for PDV operations)
- Login/logout audit logging
- OAuth user creation
"""

from odoo import models, fields, api
from odoo.http import request
from odoo.addons.via_suite_base.utils.logger import get_logger

logger = get_logger(__name__)


class ResUsers(models.Model):
    """
    Extended User model for ViaSuite.

    Adds:
    - Login audit logging
    - Extended session timeout
    - OAuth user auto-creation
    """

    _inherit = 'res.users'

    # Additional fields for ViaSuite
    via_suite_tenants = fields.Char(
        string='Allowed Tenants',
        help='Comma-separated list of tenant names this user can access. '
             'Use "*" for global access.'
    )

    last_login_audit_id = fields.Many2one(
        'via.suite.login.audit',
        string='Last Login Event',
        help='Reference to the last login audit record'
    )

    @api.model
    def _login(self, db, login, password, user_agent_env=None):
        """
        Override login method to add audit logging.

        Args:
            db (str): Database name
            login (str): User login/email
            password (str): User password
            user_agent_env (dict): User agent environment

        Returns:
            int: User ID if login successful, False otherwise
        """
        try:
            # Call parent login method
            uid = super(ResUsers, self)._login(db, login, password, user_agent_env)

            if uid:
                # Get request information
                ip_address = None
                user_agent = None
                session_id = None

                if request:
                    ip_address = request.httprequest.remote_addr
                    user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')
                    session_id = request.session.sid if hasattr(request, 'session') else None

                # Log successful login
                self.env['via.suite.login.audit'].sudo().log_login_event(
                    user_id=uid,
                    event_type='login',
                    login_method='password',
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )

                logger.info(
                    "user_login_success",
                    user_id=uid,
                    login=login,
                    tenant=db,
                    ip_address=ip_address
                )

            return uid

        except Exception as e:
            # Log failed login attempt
            logger.warning(
                "user_login_failed",
                login=login,
                tenant=db,
                error=str(e)
            )

            # Try to get IP even on failure
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.httprequest.remote_addr
                user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')

            # Don't create audit record with user_id for failed login
            # as we don't have a valid user_id

            raise

    def _logout(self):
        """
        Override logout method to add audit logging.
        """
        try:
            # Get session info before logout
            session_id = None
            ip_address = None
            user_agent = None

            if request:
                ip_address = request.httprequest.remote_addr
                user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '')
                session_id = request.session.sid if hasattr(request, 'session') else None

            # Log logout event
            self.env['via.suite.login.audit'].sudo().log_login_event(
                user_id=self.id,
                event_type='logout',
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )

            logger.info(
                "user_logout",
                user_id=self.id,
                email=self.email,
                tenant=self.env.cr.dbname,
                ip_address=ip_address
            )

        except Exception as e:
            # Don't fail logout if audit fails
            logger.error(
                "logout_audit_error",
                user_id=self.id,
                error=str(e)
            )

        # Call parent logout
        return super(ResUsers, self)._logout()

    @api.model
    def create_oauth_user(self, oauth_user_info, provider_id):
        """
        Create a new user from OAuth information.

        Called when a user logs in via OAuth for the first time.

        Args:
            oauth_user_info (dict): User information from OAuth provider
            provider_id (int): OAuth provider ID

        Returns:
            res.users: Created user record
        """
        try:
            # Extract user information
            email = oauth_user_info.get('email')
            name = oauth_user_info.get('name', email)

            if not email:
                raise ValueError("OAuth user info must contain email")

            # Check if user already exists
            existing_user = self.search([('login', '=', email)], limit=1)
            if existing_user:
                logger.info(
                    "oauth_user_exists",
                    email=email,
                    user_id=existing_user.id
                )
                return existing_user

            # Create new user
            user_values = {
                'name': name,
                'login': email,
                'email': email,
                'active': True,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
                # No password - OAuth only
                'oauth_provider_id': provider_id,
            }

            # Add via_suite_tenants if present in OAuth info
            if 'via_suite_tenants' in oauth_user_info:
                user_values['via_suite_tenants'] = oauth_user_info['via_suite_tenants']

            new_user = self.sudo().create(user_values)

            logger.info(
                "oauth_user_created",
                user_id=new_user.id,
                email=email,
                tenant=self.env.cr.dbname
            )

            return new_user

        except Exception as e:
            logger.error(
                "oauth_user_creation_error",
                email=oauth_user_info.get('email'),
                error=str(e)
            )
            raise

    def check_tenant_access(self, tenant_name):
        """
        Check if user has access to a specific tenant.

        Args:
            tenant_name (str): Name of the tenant/database

        Returns:
            bool: True if user has access, False otherwise
        """
        self.ensure_one()

        if not self.via_suite_tenants:
            # No tenant restrictions - allow access
            return True

        allowed_tenants = [t.strip() for t in self.via_suite_tenants.split(',')]

        # Check for wildcard access
        if '*' in allowed_tenants:
            return True

        # Check if current tenant is in allowed list
        return tenant_name in allowed_tenants