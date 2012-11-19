import logging

import urllib
import urlparse
import urllib2
import simplejson

import openerp
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'oauth_provider_id': fields.many2one('auth.oauth.provider', 'OAuth Provider'),
        'oauth_uid': fields.char('OAuth User ID', help="Oauth Provider user_id"),
        'oauth_access_token': fields.char('OAuth Access Token', readonly=True),
    }

    _sql_constraints = [
        ('uniq_users_oauth_provider_oauth_uid', 'unique(oauth_provider_id, oauth_uid)', 'OAuth UID must be unique per provider'),
    ]

    def _auth_oauth_rpc(self, cr, uid, endpoint, access_token, context=None):
        params = urllib.urlencode({'access_token': access_token})
        if urlparse.urlparse(endpoint)[4]:
            url = endpoint + '&' + params
        else:
            url = endpoint + '?' + params
        f = urllib2.urlopen(url)
        response = f.read()
        return simplejson.loads(response)

    def _auth_oauth_validate(self, cr, uid, provider, access_token, context=None):
        """ return the validation data corresponding to the access token """
        p = self.pool.get('auth.oauth.provider').browse(cr, uid, provider, context=context)
        validation = self._auth_oauth_rpc(cr, uid, p.validation_endpoint, access_token)
        if validation.get("error"):
            raise Exception(validation['error'])
        if p.data_endpoint:
            data = self._auth_oauth_rpc(cr, uid, p.data_endpoint, access_token)
            validation.update(data)
        return validation

    def auth_oauth(self, cr, uid, provider, params, context=None):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        access_token = params.get('access_token')
        validation = self._auth_oauth_validate(cr, uid, provider, access_token)
        # required
        oauth_uid = validation['user_id']
        if not oauth_uid:
            raise openerp.exceptions.AccessDenied()
        email = validation.get('email', 'provider_%d_user_%d' % (provider, oauth_uid))
        login = email
        # optional
        name = validation.get('name', email)
        res = self.search(cr, uid, [("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
        if res:
            assert len(res) == 1
            user = self.browse(cr, uid, res[0], context=context)
            login = user.login
            user.write({'oauth_access_token': access_token})
        else:
            # New user if signup module available
            if not hasattr(self, '_signup_create_user'):
                raise openerp.exceptions.AccessDenied()

            new_user = {
                'name': name,
                'login': login,
                'user_email': email,
                'oauth_provider_id': provider,
                'oauth_uid': oauth_uid,
                'oauth_access_token': access_token,
                'active': True,
            }
            # TODO pass signup token to allow attach new user to right partner
            self._signup_create_user(cr, uid, new_user)

        credentials = (cr.dbname, login, access_token)
        return credentials

    def check_credentials(self, cr, uid, password):
        try:
            return super(res_users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:
            res = self.search(cr, SUPERUSER_ID, [('id', '=', uid), ('oauth_access_token', '=', password)])
            if not res:
                raise

#
