from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    _sql_constraints = [
        ('email_uniq', 'UNIQUE (email)', 'You can not have two users with the same email!')
    ]

class signup_signup(osv.TransientModel):
    _name = 'auth.signup'

    # TODO add captcha
    _columns = {
        'name': fields.char('Name', size=64),
        'email': fields.char('Email', size=64),
        'password': fields.char('Password', size=64),
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)

        new_user = {
            'name': values['name'],
            'login': values['email'],
            'email': values['email'],
            'password': values['password'],
            'active': True,
        }

        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth.signup_template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, 1, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, 1, new_user, context=context)

        # Dont store anything
        return 0
