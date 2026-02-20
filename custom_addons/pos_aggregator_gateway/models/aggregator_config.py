# from odoo import models, fields, api


# class AggregatorConfig(models.Model):
#     _name = 'pos.aggregator.config'
#     _description = 'Delivery Aggregator Configuration'
    
#     name = fields.Char(string='Name', required=True, default='Uber Eats')
#     provider = fields.Selection([
#         ('ubereats', 'Uber Eats'),
#         ('doordash', 'DoorDash'),
#     ], string='Provider', required=True, default='ubereats')
    
#     # ========================================
#     # OAuth Credentials (for API calls TO Uber)
#     # ========================================
#     client_id = fields.Char(
#         string='Client ID',
#         required=True,
#         help="OAuth Client ID from Uber Developer Dashboard. Used to authenticate API calls."
#     )
#     client_secret = fields.Char(
#         string='Client Secret',
#         required=True,
#         help="OAuth Client Secret from Uber Developer Dashboard. Used with Client ID to obtain access tokens for making API calls (Accept Order, Deny Order, etc.)"
#     )
    
#     # ========================================
#     # Webhook Security (for webhooks FROM Uber)
#     # ========================================
#     webhook_signing_key = fields.Char(
#         string='Webhook Signing Key',
#         required=True,
#         help="HMAC signing key for webhook signature verification. Set this in Uber Developer Dashboard → Webhooks section. Used to verify that incoming webhooks are actually from Uber."
#     )
    
#     # ========================================
#     # Store Configuration
#     # ========================================
#     store_id = fields.Char(
#         string='Store UUID',
#         help="Uber Store UUID (e.g., 9523e60b-c7d1-49c1-8733-6ba52c00bc5a)"
#     )
    
#     # ========================================
#     # Environment & API Settings
#     # ========================================
#     environment = fields.Selection([
#         ('sandbox', 'Sandbox/Test'),
#         ('production', 'Production')
#     ], string='Environment', default='sandbox', required=True)
    
#     api_base_url = fields.Char(
#         string='API Base URL',
#         compute='_compute_api_urls',
#         store=True,
#         help="Automatically set based on environment"
#     )
    
#     auth_url = fields.Char(
#         string='Auth URL',
#         compute='_compute_api_urls',
#         store=True,
#         help="OAuth token endpoint"
#     )
    
#     # ========================================
#     # Webhook Settings
#     # ========================================
#     active = fields.Boolean(
#         string='Active',
#         default=True,
#         help="Enable/disable this aggregator configuration"
#     )
    
#     webhook_url = fields.Char(
#         compute='_compute_webhook_url',
#         string="Webhook URL",
#         help="Auto-generated webhook URL. Copy this to Uber Developer Dashboard."
#     )
    
#     # ========================================
#     # Additional Settings
#     # ========================================
#     api_scopes = fields.Char(
#         string='API Scopes',
#         default='eats.store eats.order eats.store.orders.read eats.store.orders.write',
#         help="Space-separated OAuth scopes"
#     )
    
#     # ========================================
#     # Computed Fields
#     # ========================================
#     @api.depends('provider', 'environment')
#     def _compute_api_urls(self):
#         """Set API URLs based on environment"""
#         for record in self:
#             if record.provider == 'ubereats':
#                 if record.environment == 'production':
#                     record.api_base_url = 'https://api.uber.com'
#                     record.auth_url = 'https://login.uber.com/oauth/v2/token'
#                 else:  # sandbox
#                     record.api_base_url = 'https://test-api.uber.com'
#                     record.auth_url = 'https://login.uber.com/oauth/v2/token'
#             elif record.provider == 'doordash':
#                 # DoorDash URLs when implemented
#                 record.api_base_url = False
#                 record.auth_url = False
#             else:
#                 record.api_base_url = False
#                 record.auth_url = False
    
#     @api.depends('provider')
#     def _compute_webhook_url(self):
#         """Generate webhook URL based on provider"""
#         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
#         for record in self:
#             if record.provider:
#                 record.webhook_url = f"{base_url}/api/delivery/{record.provider}"
#             else:
#                 record.webhook_url = False
    
#     # ========================================
#     # Validation
#     # ========================================
#     @api.constrains('client_id', 'client_secret', 'webhook_signing_key')
#     def _check_credentials(self):
#         """Ensure all required credentials are set when active"""
#         for record in self:
#             if record.active:
#                 if not record.client_id:
#                     raise models.ValidationError("Client ID is required for active configuration")
#                 if not record.client_secret:
#                     raise models.ValidationError("Client Secret is required for active configuration")
#                 if not record.webhook_signing_key:
#                     raise models.ValidationError("Webhook Signing Key is required for active configuration")
    
#     # ========================================
#     # Helper Methods
#     # ========================================
#     def get_access_token(self):
#         """
#         Get OAuth access token using client_id and client_secret
#         This is used for making API calls TO Uber
#         """
#         self.ensure_one()
#         import requests
        
#         response = requests.post(
#             self.auth_url,
#             data={
#                 'client_id': self.client_id,
#                 'client_secret': self.client_secret,
#                 'grant_type': 'client_credentials',
#                 'scope': self.api_scopes
#             }
#         )
        
#         if response.status_code == 200:
#             return response.json().get('access_token')
#         else:
#             raise Exception(f"Failed to get access token: {response.text}")
    
#     def verify_webhook_signature(self, payload_bytes, signature):
#         """
#         Verify HMAC signature of incoming webhook
#         This uses webhook_signing_key (NOT client_secret!)
#         """
#         self.ensure_one()
#         import hmac
#         import hashlib
        
#         if not self.webhook_signing_key:
#             return False
        
#         try:
#             expected = hmac.new(
#                 self.webhook_signing_key.encode('utf-8'),
#                 payload_bytes,
#                 hashlib.sha256
#             ).hexdigest()
#             return hmac.compare_digest(signature, expected)
#         except Exception:
#             return False

from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AggregatorConfig(models.Model):
    _name = 'pos.aggregator.config'
    _description = 'Delivery Aggregator Configuration'
    
    name = fields.Char(string='Name', required=True, default='Uber Eats')
    provider = fields.Selection([
        ('ubereats', 'Uber Eats'),
        ('doordash', 'DoorDash'),
    ], string='Provider', required=True, default='ubereats')
    
    # ========================================
    # OAuth Credentials (for API calls TO Uber)
    # ========================================
    client_id = fields.Char(
        string='Client ID',
        required=True,
        help="OAuth Client ID from Uber Developer Dashboard. Used to authenticate API calls."
    )
    client_secret = fields.Char(
        string='Client Secret',
        required=True,
        help="OAuth Client Secret from Uber Developer Dashboard. Used with Client ID to obtain access tokens for making API calls (Accept Order, Deny Order, etc.)"
    )
    
    # ========================================
    # OAuth Token Storage (AUTO-FILLED by OAuth callback)
    # ========================================
    access_token = fields.Char(
        string='Access Token',
        readonly=True,
        help="OAuth access token obtained after authorization. Auto-filled by OAuth callback. Used for making authenticated API calls to Uber."
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        readonly=True,
        help="OAuth refresh token for renewing access token. Auto-filled by OAuth callback."
    )
    token_expires_at = fields.Datetime(
        string='Token Expires At',
        readonly=True,
        help="When the current access token expires. Auto-calculated when token is obtained."
    )
    token_status = fields.Selection([
        ('not_authorized', 'Not Authorized'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon')
    ], string='Token Status', compute='_compute_token_status', store=False)
    
    # ========================================
    # Webhook Security (for webhooks FROM Uber)
    # ========================================
    webhook_signing_key = fields.Char(
        string='Webhook Signing Key',
        required=True,
        help="HMAC signing key for webhook signature verification. Set this in Uber Developer Dashboard → Webhooks section. Used to verify that incoming webhooks are actually from Uber."
    )
    
    # ========================================
    # Store Configuration
    # ========================================
    store_id = fields.Char(
        string='Store UUID',
        help="Uber Store UUID (e.g., 9523e60b-c7d1-49c1-8733-6ba52c00bc5a)"
    )
    
    # ========================================
    # Environment & API Settings
    # ========================================
    environment = fields.Selection([
        ('sandbox', 'Sandbox/Test'),
        ('production', 'Production')
    ], string='Environment', default='sandbox', required=True)
    
    api_base_url = fields.Char(
        string='API Base URL',
        compute='_compute_api_urls',
        store=True,
        help="Automatically set based on environment"
    )
    
    auth_url = fields.Char(
        string='Auth URL',
        compute='_compute_api_urls',
        store=True,
        help="OAuth token endpoint"
    )
    
    # ========================================
    # Webhook Settings
    # ========================================
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Enable/disable this aggregator configuration"
    )
    
    webhook_url = fields.Char(
        compute='_compute_webhook_url',
        string="Webhook URL",
        help="Auto-generated webhook URL. Copy this to Uber Developer Dashboard."
    )
    
    # ========================================
    # Additional Settings
    # ========================================
    api_scopes = fields.Char(
        string='API Scopes',
        default='eats.pos_provisioning',
        help="Space-separated OAuth scopes"
    )
    
    # ========================================
    # Computed Fields
    # ========================================
    @api.depends('provider', 'environment')
    def _compute_api_urls(self):
        """Set API URLs based on environment"""
        for record in self:
            if record.provider == 'ubereats':
                if record.environment == 'production':
                    record.api_base_url = 'https://api.uber.com'
                    record.auth_url = 'https://login.uber.com/oauth/v2/token'
                else:  # sandbox
                    record.api_base_url = 'https://test-api.uber.com'
                    record.auth_url = 'https://login.uber.com/oauth/v2/token'
            elif record.provider == 'doordash':
                # DoorDash URLs when implemented
                record.api_base_url = False
                record.auth_url = False
            else:
                record.api_base_url = False
                record.auth_url = False
    
    @api.depends('provider')
    def _compute_webhook_url(self):
        """Generate webhook URL based on provider"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.provider:
                # Changed from 'ubereats' to 'uber' to match Uber dashboard
                provider_path = 'uber' if record.provider == 'ubereats' else record.provider
                record.webhook_url = f"{base_url}/api/delivery/{provider_path}"
            else:
                record.webhook_url = False
    
    @api.depends('access_token', 'token_expires_at')
    def _compute_token_status(self):
        """Compute current token status"""
        for record in self:
            if not record.access_token:
                record.token_status = 'not_authorized'
            elif not record.token_expires_at:
                record.token_status = 'active'
            else:
                now = fields.Datetime.now()
                expires_at = record.token_expires_at
                
                if now >= expires_at:
                    record.token_status = 'expired'
                elif (expires_at - now).days <= 7:
                    record.token_status = 'expiring_soon'
                else:
                    record.token_status = 'active'
    
    # ========================================
    # Validation
    # ========================================
    @api.constrains('client_id', 'client_secret', 'webhook_signing_key')
    def _check_credentials(self):
        """Ensure all required credentials are set when active"""
        for record in self:
            if record.active:
                if not record.client_id:
                    raise models.ValidationError("Client ID is required for active configuration")
                if not record.client_secret:
                    raise models.ValidationError("Client Secret is required for active configuration")
                if not record.webhook_signing_key:
                    raise models.ValidationError("Webhook Signing Key is required for active configuration")
    
    # ========================================
    # Helper Methods
    # ========================================
    def get_access_token(self):
        """
        Get valid OAuth access token (refresh if needed)
        This is used for making API calls TO Uber
        """
        self.ensure_one()
        
        # Check if token exists and is still valid
        if self.access_token and self.token_expires_at:
            now = fields.Datetime.now()
            # Refresh if expired or expiring within 1 hour
            if self.token_expires_at > now + timedelta(hours=1):
                return self.access_token
        
        # Need to refresh or get new token
        if self.refresh_token:
            return self._refresh_access_token()
        else:
            # No refresh token, need client credentials flow
            return self._get_client_credentials_token()
    
    def _get_client_credentials_token(self):
        """
        Get access token using client_credentials grant
        Used for server-to-server API calls
        """
        self.ensure_one()
        import requests
        
        try:
            response = requests.post(
                self.auth_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'client_credentials',
                    'scope': self.api_scopes
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 2592000)  # Default 30 days
                
                # Calculate expiry
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Store token
                self.sudo().write({
                    'access_token': access_token,
                    'token_expires_at': expires_at
                })
                
                _logger.info(f"Client credentials token obtained, expires at {expires_at}")
                return access_token
            else:
                _logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get access token: {response.text}")
        except Exception as e:
            _logger.exception("Error getting client credentials token")
            raise
    
    def _refresh_access_token(self):
        """
        Refresh access token using refresh_token
        """
        self.ensure_one()
        import requests
        
        try:
            response = requests.post(
                self.auth_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token', self.refresh_token)  # May return new refresh token
                expires_in = token_data.get('expires_in', 2592000)
                
                # Calculate expiry
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Store tokens
                self.sudo().write({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': expires_at
                })
                
                _logger.info(f"Access token refreshed, expires at {expires_at}")
                return access_token
            else:
                _logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                # Clear tokens and try client credentials
                self.sudo().write({
                    'access_token': False,
                    'refresh_token': False,
                    'token_expires_at': False
                })
                return self._get_client_credentials_token()
        except Exception as e:
            _logger.exception("Error refreshing access token")
            raise
    
    def verify_webhook_signature(self, payload_bytes, signature):
        """
        Verify HMAC signature of incoming webhook
        This uses webhook_signing_key (NOT client_secret!)
        """
        self.ensure_one()
        import hmac
        import hashlib
        
        if not self.webhook_signing_key:
            _logger.error("Webhook signing key not configured")
            return False
        
        try:
            expected = hmac.new(
                self.webhook_signing_key.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Case-insensitive comparison
            return hmac.compare_digest(signature.lower(), expected.lower())
        except Exception as e:
            _logger.exception("Error verifying webhook signature")
            return False
    
    def action_authorize_oauth(self):
        """
        Button action to initiate OAuth authorization flow
        Opens Uber's authorization page
        """
        self.ensure_one()
        
        if self.provider != 'ubereats':
            raise models.UserError("OAuth authorization is only available for Uber Eats")
        
        # Build authorization URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/uber/oauth/callback"
        
        auth_url = (
            f"https://login.uber.com/oauth/v2/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope={self.api_scopes}"
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }
    
    def action_test_connection(self):
        """
        Test API connection and token validity
        """
        self.ensure_one()
        
        try:
            token = self.get_access_token()
            
            if token:
                self.env.user.notify_success(
                    message='Connection successful! Access token is valid.',
                    title='Connection Test'
                )
            else:
                raise Exception("Failed to obtain access token")
                
        except Exception as e:
            raise models.UserError(f"Connection test failed: {str(e)}")
    
    def action_revoke_tokens(self):
        """
        Clear stored OAuth tokens
        """
        self.ensure_one()
        
        self.sudo().write({
            'access_token': False,
            'refresh_token': False,
            'token_expires_at': False
        })
        
        self.env.user.notify_success(
            message='OAuth tokens have been cleared.',
            title='Tokens Revoked'
        )
