from odoo import models, fields, api

class AggregatorConfig(models.Model):
    _name = 'pos.aggregator.config'
    _description = 'Delivery Aggregator Configuration'
    
    name = fields.Char(string='Name', required=True, default='Uber Eats')
    provider = fields.Selection([
        ('ubereats', 'Uber Eats'),
        ('doordash', 'DoorDash'),
    ], string='Provider', required=True, default='ubereats')
    
    # Credentials
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret', help="Used for Webhook Signature Verification")
    store_id = fields.Char(string='Store ID')
    
    # Webhook Settings
    active = fields.Boolean(default=True)
    webhook_url = fields.Char(compute='_compute_webhook_url', string="Webhook URL")

    @api.depends('provider')
    def _compute_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.provider:
                record.webhook_url = f"{base_url}/api/delivery/{record.provider}"
            else:
                record.webhook_url = False
