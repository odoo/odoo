# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ldap
import openerp.exceptions
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
from openerp.modules.registry import RegistryManager

class users(osv.osv):
    _inherit = "res.users"
    def _login(self, db, login, password):
        user_id = super(users, self)._login(db, login, password)
        if user_id:
            return user_id
        registry = RegistryManager.get(db)
        with registry.cursor() as cr:
            cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
            res = cr.fetchone()
            if res:
                return False
            ldap_obj = registry.get('res.company.ldap')
            for conf in ldap_obj.get_ldap_dicts(cr):
                entry = ldap_obj.authenticate(conf, login, password)
                if entry:
                    user_id = ldap_obj.get_or_create_user(
                        cr, SUPERUSER_ID, conf, login, entry)
                    if user_id:
                        break
            return user_id

    def check_credentials(self, cr, uid, password):
        try:
            super(users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:

            cr.execute('SELECT login FROM res_users WHERE id=%s AND active=TRUE',
                       (int(uid),))
            res = cr.fetchone()
            if res:
                ldap_obj = self.pool['res.company.ldap']
                for conf in ldap_obj.get_ldap_dicts(cr):
                    if ldap_obj.authenticate(conf, res[0], password):
                        return
            raise
        