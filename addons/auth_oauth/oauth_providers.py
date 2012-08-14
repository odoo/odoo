from openerp.osv import osv, fields

class oauth_providers(osv.osv):

    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'oauth.providers'
    _description = 'OAuth2 provider'
    _order = 'name'

    _columns = {
        'name' : fields.char('Provider name', required=True),               # Name of the OAuth2 entity, Google, LinkedIn, etc
        'client_id' : fields.char('Client ID', required=True),              # Our identifier
        'auth_endpoint' : fields.char('Authentication URL', required=True), # OAuth provider URL to authenticate users
        'scope' : fields.char('Scope'),                                     # OAUth user data desired to access
        'validation_endpoint' : fields.char('Validation URL'),              # OAuth provider URL to validate tokens
        'data_endpoint' : fields.char('Data URL'),
        'redirect_uris' : fields.char('Redirect URIs'),
        'icon_url' : fields.char('Icon'),                                   # URL of the icon's provider
        'active' : fields.boolean('Active'),
        'sequence' : fields.integer(),
    }

    _sql_constraints = [
        ('name', 'unique(name)', 'The name of the OAuth provider must be unique')
    ]

oauth_providers()