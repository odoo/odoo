import base64
import hashlib
import simplejson
import time
import urlparse

from openerp.tools import config
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

TWENTY_FOUR_HOURS = 24 * 60 * 60

def message_sign(data, secret):
    src = simplejson.dumps([data, secret], indent=None, separators=(',', ':'), sort_keys=True)
    sign = hashlib.sha1(src).hexdigest()
    msg = simplejson.dumps([data, sign], indent=None, separators=(',', ':'), sort_keys=True)
    # pad message to avoid '='
    pad = (3 - len(msg) % 3) % 3
    msg = msg + " " * pad
    msg = base64.urlsafe_b64encode(msg)
    return msg, sign

def message_check(msg, secret):
    msg = base64.urlsafe_b64decode(msg)
    l = simplejson.loads(msg)
    msg_data = l[0]
    msg_sign = l[1]
    tmp, sign = message_sign(msg_data, secret)
    if msg_sign == sign:
        return msg_data

class res_users(osv.osv):
    _inherit = 'res.users'

    _sql_constraints = [
        ('email_uniq', 'UNIQUE (user_email)', 'You can not have two users with the same email!')
    ]

    def _auth_reset_password_secret(self, cr, uid, context=None):
        uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
        res = {
            'dbname': cr.dbname,
            'uuid': uuid,
            'admin_passwd': config['admin_passwd']
        }
        return res

    def _auth_reset_password_host(self, cr, uid, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', '')

    def _auth_reset_password_link(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        host = self._auth_reset_password_host(cr, uid, context)
        secret = self._auth_reset_password_secret(cr, uid, context)
        msg_src = {
            'time': time.time(),
            'uid': ids[0],
        }
        msg, sign = message_sign(msg_src, secret)
        link = urlparse.urljoin(host, '/login?db=%s&login=anonymous&key=anonymous#action=reset_password&token=%s' % (cr.dbname, msg))
        return link

    def _auth_reset_password_check_token(self, cr, uid, token, context=None):
        secret = self._auth_reset_password_secret(cr, uid, context)
        data = message_check(token, secret)
        if data and (time.time() - data['time'] < TWENTY_FOUR_HOURS):
            return data
        return None

    def _auth_reset_password_send_email(self, cr, uid, email_to, tpl_name, res_id, context=None):
        model, tpl_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_reset_password', tpl_name)
        assert model == 'email.template'

        msg_id = self.pool.get(model).send_mail(cr, uid, tpl_id, res_id, force_send=False, context=context)
        MailMessage = self.pool.get('mail.message')
        MailMessage.write(cr, uid, [msg_id], {'email_to': email_to}, context=context)
        MailMessage.send(cr, uid, [msg_id], context=context)

    def send_reset_password_request(self, cr, uid, email, context=None):
        ids = self.pool.get('res.users').search(cr, SUPERUSER_ID, [('user_email', '=', email)], context=context)
        if ids:
            self._auth_reset_password_send_email(cr, SUPERUSER_ID, email, 'reset_password_email', ids[0], context=context)
            return True
        #else:
        #    _m, company_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'main_company')
        #    self._auth_reset_password_send_email(cr, uid, email, 'email_no_user', company_id, context=context)
        return False

class auth_reset_password(osv.TransientModel):
    _name = 'auth.reset_password'
    _rec_name = 'password'
    _columns = {
        'password': fields.char('Password', size=64),
        'password_confirmation': fields.char('Confirm Password', size=64),
        'token': fields.char('Token', size=128),
        'state': fields.selection([(x, x) for x in 'draft done missmatch error'.split()], required=True),
    }
    _defaults = {
        'state': 'draft',
    }

    def create(self, cr, uid, values, context=None):
        # NOTE here, invalid values raises exceptions to avoid storing
        # sensitive data into the database (which then are available to anyone)

        pw = values.get('password')
        if not pw or pw != values.get('password_confirmation'):
            raise osv.except_osv('Error', 'Passwords missmatch')

        Users = self.pool.get('res.users')
        data = Users._auth_reset_password_check_token(cr, uid, values.get('token', ''))
        if data:
            Users.write(cr, SUPERUSER_ID, data['uid'], {'password': pw}, context=context)
        else:
            raise osv.except_osv('Error', 'Invalid token')

        # Dont store password
        values = {'state': 'done'}
        return super(auth_reset_password, self).create(cr, uid, values, context)

    def change(self, cr, uid, ids, context=None):
        return True

    def onchange_pw(self, cr, uid, ids, password, password_confirmation, context=None):
        if password != password_confirmation:
            return {'value': {'state': 'missmatch'}}
        return {'value': {'state': 'draft'}}

    def onchange_token(self, cr, uid, ids, token, context=None):
        Users = self.pool.get('res.users')
        if not Users._auth_reset_password_check_token(cr, uid, token, context=context):
            return {'value': {'state': 'error'}}
        return {}
