import openerp
from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    def auth_signup_create(self, cr, uid, new_user, context=None):
        # add login, email, name passowrd
        # if options groups
        # add groups
        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth.signup_template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, 1, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, 1, new_user, context=context)

    def auth_signup_check(self, cr, uid, login, key, context=None):
        res = self.search(cr, uid, [("login","=",login)])
        if res:
            user_id = res[0]['id']
            self.check(cr.dbname, user_id, key)
            return user_id
        return False

    def auth_signup(self, cr, uid, name, login, password, context=None):
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
