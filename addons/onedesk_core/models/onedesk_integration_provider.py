from odoo import models, fields, api


class OnedeskIntegrationProvider(models.Model):
    _name = 'onedesk.integration.provider'
    _description = 'Plateforme de réservation'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    logo = fields.Binary(string='Logo')
    
    # Support
    supports_oauth = fields.Boolean(string='OAuth', default=False)
    supports_ical = fields.Boolean(string='iCal', default=True)
    
    # OAuth config
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    oauth_authorize_url = fields.Char(string='URL Autorisation')
    oauth_token_url = fields.Char(string='URL Token')
    oauth_scope = fields.Char(string='Scopes')
    
    # API config
    api_base_url = fields.Char(string='URL API')
    api_version = fields.Char(string='Version API')
    
    # Aide
    setup_instructions = fields.Html(string='Instructions')
    ical_help_url = fields.Char(string='Aide iCal')
    
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Le code doit être unique!')
    ]
