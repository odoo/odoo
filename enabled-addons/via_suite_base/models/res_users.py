# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """
        Override signin to:
        1. Validate tenant claim (if present)
        2. Disable JIT Provisioning (only allow existing Odoo users)
        3. Raise custom exceptions for better error handling
        """
        from odoo.addons.via_suite_base.exceptions import TenantMismatchError, UserNotFoundError
        
        # 1. Tenant Validation
        _logger.info("OAuth Validation Data: %s", validation)
        token_tenant = validation.get('tenant')
        current_db = self.env.cr.dbname
        
        # Check for Super-Admin / Support bypass roles
        user_roles = validation.get('roles', [])
        if not isinstance(user_roles, list):
            user_roles = [user_roles] if user_roles else []
            
        # Also check standard Keycloak location if not found in top-level 'roles'
        if not any(role in ['via-suite-administrator', 'via-support'] for role in user_roles):
            realm_access = validation.get('realm_access', {})
            if isinstance(realm_access, dict):
                user_roles.extend(realm_access.get('roles', []))
        
        is_bypass = any(role in ['via-suite-administrator', 'via-support'] for role in user_roles)
        
        if is_bypass:
            _logger.info("Super-admin/Support bypass active for login. Skipping tenant validation.")
        elif token_tenant:
            # If tenant claim exists and not a super-admin, validate it
            # Support both "via-suite-{tenant}" and plain tenant name formats
            expected_db = f"via-suite-{token_tenant}"
            
            if current_db != expected_db and current_db != token_tenant:
                _logger.error("Tenant mismatch: current_db=%s, token_tenant=%s, expected_db=%s", 
                              current_db, token_tenant, expected_db)
                raise TenantMismatchError(token_tenant, current_db)
            _logger.info("Tenant validation passed: %s", token_tenant)
        else:
            _logger.warning("No tenant claim in token for database %s and no bypass role detected.", current_db)

        oauth_uid = validation['user_id']
        email = validation.get('email')
        
        _logger.info("Looking for user with oauth_uid=%s, email=%s", oauth_uid, email)
        
        # 2. Find user (don't create if missing)
        user = self.search([
            ("oauth_uid", "=", oauth_uid), 
            ('oauth_provider_id', '=', provider)
        ], limit=1)
        
        if not user and email:
            # Try to find by email and link the account
            user = self.search([
                ("login", "=", email),
                ("oauth_uid", "=", False)
            ], limit=1)
            
            if user:
                _logger.info("Linking existing user %s (id=%s) to OAuth", email, user.id)
        
        if user:
            # Check if user is active
            if not user.active:
                _logger.warning("User %s exists but is inactive", email)
                from odoo.addons.via_suite_base.exceptions import AccountDisabledError
                raise AccountDisabledError(email)
            
            # ALWAYS update the token to allow authentication via _check_credentials
            user.sudo().write({
                'oauth_uid': oauth_uid,
                'oauth_provider_id': provider,
                'oauth_access_token': params.get('access_token')
            })
        
        if not user:
            _logger.warning("OAuth login failed: User %s not found in system (JIT disabled)", email)
            raise UserNotFoundError(email)
        
        if not user:
            _logger.warning("OAuth login failed: User %s not found in system (JIT disabled)", email)
            raise UserNotFoundError(email)
        
        _logger.info("OAuth signin successful for user %s (id=%s)", user.login, user.id)
        return user.login  # Must return login, not user.id

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            if not self.env.context.get('skip_keycloak_sync') and self.env.context.get('install_mode') is not True:
                try:
                    self.env['via_suite.keycloak.service'].upsert_user(user)
                except Exception as e:
                    _logger.error("Failed to sync new user to Keycloak: %s", str(e))
        return users

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        if not self.env.context.get('skip_keycloak_sync'):
            for user in self:
                if any(k in vals for k in ['login', 'name', 'active']):
                    try:
                        self.env['via_suite.keycloak.service'].upsert_user(user)
                    except Exception as e:
                        _logger.error("Failed to sync user update to Keycloak: %s", str(e))
        return res

    def unlink(self):
        for user in self:
            if not self.env.context.get('skip_keycloak_sync'):
                try:
                    self.env['via_suite.keycloak.service'].delete_user(user)
                except Exception as e:
                    _logger.error("Failed to delete user from Keycloak: %s", str(e))
        return super(ResUsers, self).unlink()
