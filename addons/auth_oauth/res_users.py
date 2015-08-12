import logging

import werkzeug.urls
import urlparse
import urllib
import urllib2
import simplejson

import openerp
from openerp.addons.auth_signup.res_users import SignupError
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'oauth_provider_id': fields.many2one('auth.oauth.provider', 'OAuth Provider'),
        'oauth_uid': fields.char('OAuth User ID', help="Oauth Provider user_id", copy=False),
        'oauth_access_token': fields.char('OAuth Access Token', readonly=True, copy=False),
    }

    _sql_constraints = [
        ('uniq_users_oauth_provider_oauth_uid', 'unique(oauth_provider_id, oauth_uid)', 'OAuth UID must be unique per provider'),
    ]

    def _auth_oauth_rpc(self, cr, uid, endpoint, params, method='get', context=None):
        # params = werkzeug.url_encode({'access_token': access_token})
        if method == 'get':
            if urlparse.urlparse(endpoint)[4]:
                url = endpoint + '&' + werkzeug.url_encode(params)
            else:
                url = endpoint + '?' + werkzeug.url_encode(params)
            _logger.info("url: %s" % (url,))
            req = urllib2.Request(url, headers={'Content-Type': 'application/json'})
        else:
            ''' default: post method '''
            url = endpoint
            _logger.info("url: %s" % (url,))
            req = urllib2.Request(url, data=urllib.urlencode(params), headers={'Content-Type': 'application/x-www-form-urlencoded'})

        '''
        special process for Douban
        '''
        if endpoint == 'https://api.douban.com/v2/user/~me':
            url = endpoint
            _logger.info("url: %s" % (url,))
            req = urllib2.Request(url, headers={'Authorization': 'Bearer ' + params['access_token']})

        f = urllib2.urlopen(req)
        response = f.read()
        _logger.info("response: %s" % (response,))
        if not isinstance(response, str):
            _logger.info("response is not str")
            response = str(response)
        # strip space
        response = response.strip()
        if response.startswith('callback(') and response.endswith(');'):
            '''
            QQ strip prefix and suffix when fetch openid
            '''
            response = response[9:-2].strip()

        try:
            res = simplejson.loads(response)
        except simplejson.scanner.JSONDecodeError:
            res = werkzeug.url_decode(response)

        return res

    def _auth_oauth_validate(self, cr, uid, provider, params, context=None):
        """ return the validation data corresponding to the access token """
        p = self.pool.get('auth.oauth.provider').browse(cr, uid, provider, context=context)

        state = simplejson.loads(params['state'])
        vparams = dict(
            grant_type=p['grant_type'],
            client_id=p['client_id'],
            client_secret=p['client_secret'],
            redirect_uri=state['rr'],
            code=params['code'],
        )
        validation = self._auth_oauth_rpc(cr, uid, p.validation_endpoint, vparams, 'post', context)
        if validation.get("msg") or validation.get("error"):
            if validation.get("error"):
                raise Exception(validation['error'])
            raise Exception(validation['msg'])
        if p.data_endpoint:
            data = self._auth_oauth_rpc(cr, uid, p.data_endpoint, dict(access_token=validation['access_token']), context)
            _logger.info("data_endpoint: %s" % (data,))
            if not data.get('openid'):
                if data.get('uid'):
                    data['openid'] = data.get('uid')
                elif data.get('taobao_user_id'):
                    data['openid'] = data.get('taobao_user_id')
                elif data.get('douban_user_id'):
                    data['openid'] = data.get('douban_user_id')
            validation.update(data)
        return validation

    def _generate_signup_values(self, cr, uid, provider, validation, params, context=None):
        oauth_uid = validation['openid']
        email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        name = validation.get('name', email)
        return {
            'name': name,
            'login': email,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': validation['access_token'],
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
        try:
            oauth_uid = validation['openid']
            user_ids = self.search(cr, uid, [("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not user_ids:
                raise openerp.exceptions.AccessDenied()
            assert len(user_ids) == 1
            user = self.browse(cr, uid, user_ids[0], context=context)
            user.write({'oauth_access_token': validation['access_token']})
            return user.login
        except openerp.exceptions.AccessDenied, access_denied_exception:
            _logger.error("AccessDenied")
            if context and context.get('no_user_creation'):
                return None
            state = simplejson.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(cr, uid, provider, validation, params, context=context)
            try:
                _, login, _ = self.signup(cr, uid, values, token, context=context)
                return login
            except SignupError:
                _logger.error("SignupError")
                raise access_denied_exception

    def auth_oauth(self, cr, uid, provider, params, context=None):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        # access_token = params.get('access_token')
        validation = self._auth_oauth_validate(cr, uid, provider, params)
        _logger.error("validation %s" % (validation,))
        # required check
        if not validation.get('openid'):
            _logger.error("No openid")
            raise openerp.exceptions.AccessDenied()
        # retrieve and sign in user
        login = self._auth_oauth_signin(cr, uid, provider, validation, params, context=context)
        if not login:
            _logger.error("Not login")
            raise openerp.exceptions.AccessDenied()
        # return user credentials
        return (cr.dbname, login, validation['access_token'])

    def check_credentials(self, cr, uid, password):
        try:
            return super(res_users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:
            res = self.search(cr, SUPERUSER_ID, [('id', '=', uid), ('oauth_access_token', '=', password)])
            if not res:
                raise

#
