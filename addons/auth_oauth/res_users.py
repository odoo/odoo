import urllib2
import simplejson

import openerp

from openerp.osv import osv, fields

class res_users(osv.Model):

    _inherit = 'res.users'

    def auth_oauth(self, cr, uid, params, context=None):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        login = self.auth_oauth_fetch_user_validation(cr, uid, params)['email']
        password = self.auth_oauth_fetch_user_validation(cr, uid, params)['user_id']
        name = self.auth_oauth_fetch_user_data(cr, uid, params)['name']
        r = (cr.dbname, login, password)
        try:
            # check for existing user
            if not self.auth_signup_check(cr, uid, login, password):
                # new user
                new_user = {
                    'name': name,
                    'login': login,
                    'user_email': login,
                    'password': password,
                    'active': True,
                }
                self.auth_signup_create(cr, uid, new_user)
                return r
            else:
                # already existing with same password
                return r
        except openerp.exceptions.AccessDenied:
            # already existing with diffrent password
            raise
    def auth_oauth_rpc(self, cr, uid, endpoint, params, context=None):
        url = endpoint + params.get('access_token')
        f = urllib2.urlopen(url)
        validation = f.read()
        return simplejson.loads(validation)

    def auth_oauth_fetch_user_validation(self, cr, uid, params, context=None):
        endpoint = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='    
        return self.auth_oauth_rpc(cr, uid, endpoint, params)

    def auth_oauth_fetch_user_data(self, cr, uid, params):
        endpoint = 'https://www.googleapis.com/oauth2/v1/userinfo?access_token='
        return self.auth_oauth_rpc(cr, uid, endpoint, params)

#
