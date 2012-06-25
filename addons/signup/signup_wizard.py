from functools import partial
from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'

    _sql_constraints = [
        ('email_uniq', 'UNIQUE (user_email)', 'You can not have two users with the same email!')
    ]


class signup_wizard(osv.TransientModel):
    _name = 'signup.wizard'
    _columns = {
        'name': fields.char('Name', size=64),
        'email': fields.char('Email', size=64),
        'pw': fields.char('Password', size=64),
        'cpw': fields.char('Confirm Password', size=64),
        'state': fields.selection([(x, x) for x in 'draft done missmatch'.split()], required=True),
    }
    _defaults = {
        'state': 'draft',
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)

        name = values.get('name')
        email = values.get('email')
        pw = values.get('pw')
        cpw = values.get('cpw')

        if pw != cpw:
            raise osv.except_osv('Error', 'Passwords missmatch')

        Users = self.pool.get('res.users')

        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'signup.user_template_id', 0)
        if user_template_id:
            func = partial(Users.copy, cr, 1, user_template_id, context=context)
        else:
            func = partial(Users.create, cr, 1, context=context)

        func({
            'name': name,
            'login': email,
            'user_email': email,
            'password': pw,
            'active': True,
        })

        values = {'state': 'done'}
        return super(signup_wizard, self).create(cr, uid, values, context)

    def signup(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'login',
        }

    def onchange_pw(self, cr, uid, ids, pw, cpw, context=None):
        if pw != cpw:
            return {'value': {'state': 'missmatch'}}
        return {'value': {'state': 'draft'}}
