import logging

import werkzeug.urls
import urlparse
import urllib2
import json

import openerp
from openerp.addons.auth_signup.models.res_partner import SignupError
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)


class auth_oauth_account(osv.Model):
    _name = 'auth_oauth.account'

    _columns = {
        'user_id': fields.many2one('res.users', 'User', required=True, readonly=True, ondelete='cascade'),
        'oauth_provider_id': fields.many2one('auth.oauth.provider', 'OAuth Provider', required=True, readonly=True, ondelete='cascade'),
        'oauth_uid': fields.char('OAuth User ID', help="OAuth Provider user_id", required=True),
        'oauth_email': fields.char('OAuth Email', help="OAuth Email", readonly=True),
    }

    _sql_constraints = [
        ('uniq_users_oauth_provider_oauth_uid', 'unique(oauth_provider_id, oauth_uid)', 'OAuth UID must be unique per provider'),
    ]


class res_users_token(osv.Model):
    _inherit = 'res.users.token'

    _columns = {
        'oauth_account_id': fields.many2one('auth_oauth.account', 'OAuth Account', readonly=True, ondelete='cascade'),
        'oauth_provider_id': fields.related('oauth_account_id', 'oauth_provider_id', type='many2one', relation='auth.oauth.provider', string='OAuth Provider', readonly=True),
    }

    def _get_type_selection(self):
        selection = super(res_users_token, self)._get_type_selection()
        selection.append(('oauth', 'OAuth'))
        return selection

    def _auth_oauth_rpc(self, cr, uid, endpoint, access_token, context=None):
        params = werkzeug.url_encode({'access_token': access_token})
        if urlparse.urlparse(endpoint)[4]:
            url = endpoint + '&' + params
        else:
            url = endpoint + '?' + params
        f = urllib2.urlopen(url)
        response = f.read()
        return json.loads(response)

    def _auth_oauth_validate(self, cr, uid, provider, access_token, context=None):
        """ return the validation data corresponding to the access token """
        p = self.pool.get('auth.oauth.provider').browse(cr, uid, provider, context=context)
        validation = self._auth_oauth_rpc(cr, uid, p.validation_endpoint, access_token, context=context)
        if validation.get("error"):
            raise Exception(validation['error'])
        if p.data_endpoint:
            data = self._auth_oauth_rpc(cr, uid, p.data_endpoint, access_token, context=context)
            validation.update(data)
        return validation


class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'oauth_account_ids': fields.one2many('auth_oauth.account', 'user_id', 'OAuth Accounts'),
        'oauth_token_ids': fields.one2many('res.users.token', 'user_id', 'OAuth Access Tokens', domain=[('type', '=', 'oauth')])
    }

    def _generate_signup_values(self, cr, uid, provider, validation, params, context=None):
        oauth_uid = validation['user_id']
        email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        name = validation.get('name', email)
        return {
            'name': name,
            'login': email,
            'email': email,
            'active': True,
        }

    def _auth_oauth_signin(self, cr, uid, provider, validation, params, context=None):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: openerp.exceptions.AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        user_id = None
        login = None
        oauth_account_id = None
        try:
            oauth_uid = validation['user_id']
            oauth_account_ids = self.pool['auth_oauth.account'].search(cr, uid, [("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_account_ids:
                raise openerp.exceptions.AccessDenied()
            oauth_account_id = oauth_account_ids[0]
            user = self.pool['auth_oauth.account'].browse(cr, uid, oauth_account_id, context=context).user_id
            login = user.login
            user_id = user.id
        except openerp.exceptions.AccessDenied, access_denied_exception:
            if context and context.get('no_user_creation'):
                return None
            state = json.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(cr, uid, provider, validation, params, context=context)
            try:
                _, login, _ = self.signup(cr, uid, values, token, context=context)
                user_id = self.search(cr, uid, [('login', '=', login)], context=context)[0]
                oauth_account_id = self.pool['auth_oauth.account'].create(cr, uid, {
                    'user_id': user_id,
                    'oauth_uid': validation['user_id'],
                    'oauth_provider_id': provider,
                    'oauth_email': validation.get('email'),
                }, context=context)
            except SignupError:
                raise access_denied_exception
        if user_id:
            self.pool['res.users.token'].create(cr, uid, {
                'user_id': user_id,
                'token': params['access_token'],
                'type': 'oauth',
                'oauth_account_id': oauth_account_id,
            })
        return login

    def auth_oauth(self, cr, uid, provider, params, context=None):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        access_token = params.get('access_token')
        validation = self.pool['res.users.token']._auth_oauth_validate(cr, uid, provider, access_token, context=context)
        # required check
        if not validation.get('user_id'):
            # Workaround: facebook does not send 'user_id' in Open Graph Api
            if validation.get('id'):
                validation['user_id'] = validation['id']
            else:
                raise openerp.exceptions.AccessDenied()

        # retrieve and sign in user
        login = self._auth_oauth_signin(cr, uid, provider, validation, params, context=context)
        if not login:
            raise openerp.exceptions.AccessDenied()
        # return user credentials
        return (cr.dbname, login, access_token)
