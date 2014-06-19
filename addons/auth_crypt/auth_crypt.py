import logging

from passlib.hash import md5_crypt

import openerp
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class res_users(osv.osv):
    _inherit = "res.users"

    def set_pw(self, cr, uid, id, name, value, args, context):
        if value:
            encrypted = md5_crypt.encrypt(value)
            cr.execute("update res_users set password='', password_crypt=%s where id=%s", (encrypted, id))

    def get_pw( self, cr, uid, ids, name, args, context ):
        cr.execute('select id, password from res_users where id in %s', (tuple(map(int, ids)),))
        stored_pws = cr.fetchall()
        res = {}

        for id, stored_pw in stored_pws:
            res[id] = stored_pw

        return res

    _columns = {
        'password': fields.function(get_pw, fnct_inv=set_pw, type='char', string='Password', invisible=True, store=True),
        'password_crypt': fields.char(string='Encrypted Password', invisible=True),
    }

    def check_credentials(self, cr, uid, password):
        # convert to base_crypt if needed
        cr.execute('SELECT password, password_crypt FROM res_users WHERE id=%s AND active', (uid,))
        stored_password_crypt = None
        if cr.rowcount:
            stored_password, stored_password_crypt = cr.fetchone()
            if stored_password and not stored_password_crypt:
                stored_password_crypt = md5_crypt.encrypt(stored_password)
                cr.execute("UPDATE res_users SET password='', password_crypt=%s WHERE id=%s", (stored_password_crypt, uid))
        try:
            return super(res_users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:
            # check md5crypt
            if stored_password_crypt:
                if md5_crypt.verify(password, stored_password_crypt):
                    return
            # Reraise password incorrect
            raise


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
