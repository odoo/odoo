import urlparse
import itsdangerous
from openerp.tools import config
from openerp.osv import osv, fields

TWENTY_FOUR_HOURS = 24 * 60 * 60

def serializer(dbname):
    key = '%s.%s' % (dbname, config['admin_passwd'])
    return itsdangerous.URLSafeTimedSerializer(key)

def generate_token(dbname, user):
    s = serializer(dbname)
    return s.dumps((user.id, user.user_email))

def valid_token(dbname, token, max_age=TWENTY_FOUR_HOURS):
    try:
        unsign_token(dbname, token, max_age)
        return True
    except itsdangerous.BadSignature:
        return False

def unsign_token(dbname, token, max_age=TWENTY_FOUR_HOURS):
    # TODO avoid replay by comparing timestamp with last connection date of user ? (need a query)
    s = serializer(dbname)
    return s.loads(token, max_age)

class res_users(osv.osv):
    _inherit = 'res.users'

    _sql_constraints = [
        ('email_uniq', 'UNIQUE (user_email)', 'You can not have two users with the same email!')
    ]

    def _rp_send_email(self, cr, uid, email, tpl_name, res_id, context=None):
        model, tpl_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'reset_password', tpl_name)
        assert model == 'email.template'

        host = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', '')
        ctx = dict(context or {}, url=host)

        msg_id = self.pool.get(model).send_mail(cr, uid, tpl_id, res_id, force_send=False, context=ctx)
        MailMessage = self.pool.get('mail.message')
        MailMessage.write(cr, uid, [msg_id], {'email_to': email}, context=context)
        MailMessage.send(cr, uid, [msg_id], context=context)

    def _rp_get_link(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        user = self.browse(cr, uid, ids[0], context=context)
        host = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', '')
        token = generate_token(cr.dbname, user)
        link = urlparse.urljoin(host, '/reset_password?db=%s&token=%s' % (cr.dbname, token))
        return link

    def send_reset_password_request(self, cr, uid, email, context=None):
        uid = 1
        ids = self.search(cr, uid, [('user_email', '=', email)], context=context)
        assert len(ids) <= 1
        if not ids:
            _m, company_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'main_company')
            self._rp_send_email(cr, uid, email, 'email_no_user', company_id, context=context)
        else:
            self._rp_send_email(cr, uid, email, 'email_reset_link', ids[0], context=context)
        return True

res_users()


class reset_pw_wizard(osv.TransientModel):
    _name = 'reset_password.wizard'
    _rec_name = 'pw'
    _columns = {
        'pw': fields.char('Password', size=64),
        'cpw': fields.char('Confirm Password', size=64),
        'token': fields.char('Token', size=128),
        'state': fields.selection([(x, x) for x in 'draft done missmatch error'.split()], required=True),
    }
    _defaults = {
        'state': 'draft',
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)

        token = values.get('token')
        pw = values.get('pw')
        cpw = values.get('cpw')

        if pw != cpw:
            raise osv.except_osv('Error', 'Passwords missmatch')

        Users = self.pool.get('res.users')

        try:
            user_id, user_email = unsign_token(cr.dbname, token)
        except Exception:
            raise osv.except_osv('Error', 'Invalid token')

        Users.write(cr, 1, user_id, {'password': pw}, context=context)
        Users._rp_send_email(cr, 1, user_email, 'email_password_changed', user_id, context=context)

        values = {'state': 'done'}

        return super(reset_pw_wizard, self).create(cr, uid, values, context)

    def change(self, cr, uid, ids, context=None):
        return True

    def onchange_token(self, cr, uid, ids, token, context=None):
        if not valid_token(cr.dbname, token):
            return {'value': {'state': 'error'}}
        return {}

    def onchange_pw(self, cr, uid, ids, pw, cpw, context=None):
        if pw != cpw:
            return {'value': {'state': 'missmatch'}}
        return {'value': {'state': 'draft'}}
