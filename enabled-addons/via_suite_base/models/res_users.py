# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import AccessDenied

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """
        Override signin to link existing users by email if oauth_uid is not set.
        """
        oauth_uid = validation['user_id']
        email = validation.get('email')
        
        # 1. Try to find user by OAuth UID (Standard Odoo behavior)
        user = self.search([
            ("oauth_uid", "=", oauth_uid), 
            ('oauth_provider_id', '=', provider)
        ], limit=1)
        
        if not user and email:
            # 2. Try to find user by login/email if not found by OAuth UID
            user = self.search([
                ("login", "=", email),
                ("oauth_uid", "=", False)
            ], limit=1)
            
            if user:
                # Link existing user to this OAuth account
                user.sudo().write({
                    'oauth_uid': oauth_uid,
                    'oauth_provider_id': provider,
                    'oauth_access_token': params.get('access_token')
                })
        
        return super(ResUsers, self)._auth_oauth_signin(provider, validation, params)
