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
        1. Validate tenant claim
        2. Disable JIT Provisioning (only allow existing Odoo users)
        """
        # 1. Tenant Validation
        _logger.debug("OAuth Validation Data: %s", validation)
        token_tenant = validation.get('tenant')
        current_db = self.env.cr.dbname
        expected_db = f"via-suite-{token_tenant}" if token_tenant else False
        
        if not token_tenant or current_db != expected_db:
            _logger.error("Tenant mismatch: expected %s, got %s (token tenant: %s)", 
                          current_db, expected_db, token_tenant)
            raise AccessDenied("Invalid tenant or permission denied for this database.")

        oauth_uid = validation['user_id']
        email = validation.get('email')
        
        # 2. Find user (don't create if missing)
        user = self.search([
            ("oauth_uid", "=", oauth_uid), 
            ('oauth_provider_id', '=', provider)
        ], limit=1)
        
        if not user and email:
            user = self.search([
                ("login", "=", email),
                ("oauth_uid", "=", False)
            ], limit=1)
            
            if user:
                # Link existing user
                user.sudo().write({
                    'oauth_uid': oauth_uid,
                    'oauth_provider_id': provider,
                    'oauth_access_token': params.get('access_token')
                })
        
        if not user:
            _logger.warning("OAuth login failed: User %s not found in Odoo and JIT is disabled.", email)
            raise AccessDenied("User not found. Please contact your administrator.")
            
        return user.id

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            if not self._context.get('skip_keycloak_sync') and self.env.context.get('install_mode') is not True:
                try:
                    self.env['via_suite.keycloak.service'].upsert_user(user)
                except Exception as e:
                    _logger.error("Failed to sync new user to Keycloak: %s", str(e))
        return users

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        if not self._context.get('skip_keycloak_sync'):
            for user in self:
                if any(k in vals for k in ['login', 'name', 'active']):
                    try:
                        self.env['via_suite.keycloak.service'].upsert_user(user)
                    except Exception as e:
                        _logger.error("Failed to sync user update to Keycloak: %s", str(e))
        return res

    def unlink(self):
        for user in self:
            if not self._context.get('skip_keycloak_sync'):
                try:
                    self.env['via_suite.keycloak.service'].delete_user(user)
                except Exception as e:
                    _logger.error("Failed to delete user from Keycloak: %s", str(e))
        return super(ResUsers, self).unlink()
