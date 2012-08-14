import urllib2
import simplejson

import openerp

from openerp.osv import osv, fields

class res_users(osv.Model):

    _inherit = 'res.users'

    _columns = {
        'oauth_provider': fields.char('OAuth Provider', size=1024),
        'oauth_uid': fields.char('OAuth User ID', size=256,
                                    help="Used for disambiguation in case of a shared OpenID URL"),
        'oauth_access_token': fields.char('OAuth Token',
                                  readonly=True),
    }

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

    def auth_oauth(self, cr, uid, params, context=None):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        validation = self.auth_oauth_fetch_user_validation(cr, uid, params)
        login = validation['email']
        oauth_uid = validation['user_id']
        name = self.auth_oauth_fetch_user_data(cr, uid, params)['name']
        r = (cr.dbname, login, oauth_uid)
        try:
            # check for existing user
            if not self.auth_signup_check(cr, uid, login, oauth_uid):
                # new user
                new_user = {
                    'name': name,
                    'login': login,
                    'user_email': login,
                    'password': oauth_uid,
                    'oauth_provider': 'Google',
                    'oauth_uid': oauth_uid,
                    'oauth_access_token': params.get('access_token'),
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

    def check(self, db, uid, passwd):
        try:
            return super(res_users, self).check(db, uid, passwd)
        except openerp.exceptions.AccesDenied:
            if not passwd:
                raise
            try:
                registry = openerp.modules.registry.RegistryManager.get(db)
                cr = registry.db.cursor()
                cr.execute('''SELECT COUNT(1)
                                FROM res_users
                               WHERE id=%s
                                 AND oauth_key=%s
                                 AND active=%s''',
                            (int(uid), passwd, True))
                if not cr.fetchone()[0]:
                    raise
                self._uid_cache.setdefault(db, {})[uid] = passwd
            finally:
                cr.close()


#
