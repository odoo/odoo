from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    _sql_constraints = [
        ('email_uniq', 'UNIQUE (user_email)', 'You can not have two users with the same email!')
    ]

class signup_signup(osv.TransientModel):
    _name = 'auth.signup'
    _columns = {
        'name': fields.char('Name', size=64),
        'email': fields.char('Email', size=64),
        'password': fields.char('Password', size=64),
        'password_confirmation': fields.char('Confirm Password', size=64),
        'state': fields.selection([(x, x) for x in 'draft done missmatch'.split()], required=True),
    }
    _defaults = {
        'state': 'draft',
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)
        if values['password'] != values['password_confirmation']:
            raise osv.except_osv('Error', 'Passwords missmatch')

        new_user = {
            'name': values['name'],
            'login': values['email'],
            'user_email': values['email'],
            'password': values['password'],
            'active': True,
        }

        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth.signup_template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, 1, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, 1, new_user, context=context)

        # Dont store the password
        values = {'state': 'done'}
        return super(signup_signup, self).create(cr, uid, values, context)

    def signup(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'login',
        }

    def onchange_pw(self, cr, uid, ids, pw, cpw, context=None):
        if pw != cpw:
            return {'value': {'state': 'missmatch'}}
        return {'value': {'state': 'draft'}}

