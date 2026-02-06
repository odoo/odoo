from odoo import models, fields, api


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
        default='eats.store eats.order eats.store.orders.read eats.store.orders.write',
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
                record.webhook_url = f"{base_url}/api/delivery/{record.provider}"
            else:
                record.webhook_url = False
    
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
        Get OAuth access token using client_id and client_secret
        This is used for making API calls TO Uber
        """
        self.ensure_one()
        import requests
        
        response = requests.post(
            self.auth_url,
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials',
                'scope': self.api_scopes
            }
        )
        
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            raise Exception(f"Failed to get access token: {response.text}")
    
    def verify_webhook_signature(self, payload_bytes, signature):
        """
        Verify HMAC signature of incoming webhook
        This uses webhook_signing_key (NOT client_secret!)
        """
        self.ensure_one()
        import hmac
        import hashlib
        
        if not self.webhook_signing_key:
            return False
        
        try:
            expected = hmac.new(
                self.webhook_signing_key.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception:
            return False
