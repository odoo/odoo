from openerp.osv import osv, fields

class auth_oauth_provider(osv.osv):
    """Class defining the configuration values of an OAuth2 provider"""

    _name = 'auth.oauth.provider'
    _description = 'OAuth2 provider'
    _order = 'name'

    _columns = {
        'name' : fields.char('Provider name', required=True),               # Name of the OAuth2 entity, Google, etc
        'client_id' : fields.char('Client ID'),              # Our identifier
        'auth_endpoint' : fields.char('Authentication URL', required=True), # OAuth provider URL to authenticate users
        'scope' : fields.char('Scope'),                                     # OAUth user data desired to access
        'validation_endpoint' : fields.char('Validation URL', required=True),# OAuth provider URL to validate tokens
        'data_endpoint' : fields.char('Data URL'),
        'enabled' : fields.boolean('Allowed'),
        'css_class' : fields.char('CSS class'),
        'body' : fields.char('Body', required=True),
        'sequence' : fields.integer(),
    }
    _defaults = {
        'enabled' : False,
        'css_class' : "zocial",
    }
