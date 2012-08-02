import base64
import hashlib
import simplejson
import time
import urlparse

from openerp.tools import config
from openerp.osv import osv, fields

TWENTY_FOUR_HOURS = 24 * 60 * 60

def message_sign(data, secret):
    src = simplejson.dumps([data,secret], indent=None, separators=(',', ':'), sort_keys=True)
    sign = hashlib.sha1(src).hexdigest()
    msg = simplejson.dumps([data,sign], indent=None, separators=(',', ':'), sort_keys=True)
    # pad message to avoid '='
    pad = (3-len(msg)%3)%3
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

    def _auth_reset_password_secret(self, cr, uid, ids, context=None):
        uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
        res = {
            'dbname': cr.dbname,
            'uuid': uuid,
            'admin_passwd': config['admin_passwd']
        }
        return res

    def _auth_reset_password_host(self, cr, uid, ids, context=None):
        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', '')

    def _auth_reset_password_link(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        user = self.browse(cr, uid, ids[0], context=context)
        host = self._auth_reset_password_host(cr, uid, ids, context)
        secret = self._auth_reset_password_secret(cr, uid, ids, context)
        msg_src = {
            'time' : time.time(),
            'uid' : ids[0],
        }
        msg, sign = message_sign(msg_src, secret)
        link = urlparse.urljoin(host, '/web/webclient/home#action_id=reset_password&token=%s' % msg)
        return link

    def _auth_reset_password_check_token(self, cr, uid, token, context=None):
        secret = self._auth_reset_password_secret(cr, uid, ids, context)
        data = message_check(token, secret)
        if data and (time.time() - data['time'] < TWENTY_FOUR_HOURS):
            return data

    def send_reset_password_request(self, cr, uid, email, context=None):
        ids = self.pool.get('res.users').search(cr, 1, [('user_email', '=', email)], context=context)
        if ids:
            model, template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'auth_reset_password', 'reset_password_email')
            msg_id = self.pool.get('email.template').send_mail(cr, uid, template_id, ids[0], context=ctx)
        return True

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

        if values['password'] != values['password_confirmation']:
            raise osv.except_osv('Error', 'Passwords missmatch')

        Users = self.pool.get('res.users')
        data = Users._auth_reset_password_check_token(self, cr, uid, values['token'])
        if data:
            Users.write(cr, 1, data['uid'], {'password': pw}, context=context)
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

