import openerp
from openerp.osv import osv

class res_users(osv.Model):
    _inherit = 'res.users'

    def auth_signup_create(self, cr, uid, new_user, context=None):
        # new_user:
        #   login
        #   email
        #   name (optional)
        #   partner_id (optional)
        #   groups (optional)
        #   sign (for partner_id and groups)
        #
        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth.signup_template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, 1, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, 1, new_user, context=context)

    def auth_signup(self, cr, uid, name, login, password, context=None):
        r = (cr.dbname, login, password)
        res = self.search(cr, uid, [("login", "=", login)])
        if res:
            # Existing user
            user_id = res[0]
            try:
                self.check(cr.dbname, user_id, password)
                # Same password
            except openerp.exceptions.AccessDenied:
                # Different password
                raise
        else:
            # New user
            new_user = {
                'name': name,
                'login': login,
                'user_email': login,
                'password': password,
                'active': True,
            }
            self.auth_signup_create(cr, uid, new_user)
        return r

#
