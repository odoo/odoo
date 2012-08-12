import urllib2

import openerp

from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    def auth_oauth(self, cr, uid, params, context=None):
        print params
        url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + params.get('access_token')
        f = urllib2.urlopen(url)
        validation = f.read()
        print validation
        r = (cr.dbname, login, password)
        try:
            # check for existing user
            if not self.auth_signup_check(cr, uid, login, password):
                print "NEW USER"
                # new user
                new_user = {
                    'name': name,
                    'login': login,
                    'user_email': login,
                    'password': password,
                    'active': True,
                }
                self.auth_signup_create(cr,uid, new_user)
                return r
            else:
                print "Existing same"
                # already existing with same password
                return r
        except openerp.exceptions.AccessDenied:
            print "Existing different"
            # already existing with diffrent password
            raise

#
