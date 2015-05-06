# -*- coding: utf-8 -*-

import openerp.exceptions

from openerp import api, models, SUPERUSER_ID
from openerp.modules.registry import RegistryManager

class Users(models.Model):
    _inherit = "res.users"

    def _login(self, db, login, password):
        user_id = super(Users, self)._login(db, login, password)
        if user_id:
            return user_id
        registry = RegistryManager.get(db)
        with registry.cursor() as cr:
            cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
            res = cr.fetchone()
            if res:
                return False
            env = openerp.api.Environment(cr, SUPERUSER_ID, {})
            Ldap = env['res.company.ldap']
            for ldap_conf in Ldap.search([('ldap_server', '!=', False)], order='sequence'):
                entry = ldap_conf.authenticate(login, password)
                if entry:
                    user_id = ldap_conf.get_or_create_user(login, entry)
                    if user_id:
                        break
            return user_id

    @api.model
    def check_credentials(self, password):
        try:
            super(Users, self).check_credentials(password)
        except openerp.exceptions.AccessDenied:

            if self.env.user.active:
                Ldap = self.env['res.company.ldap'].sudo()
                for ldap_conf in Ldap.search([('ldap_server', '!=', False)], order='sequence'):
                    if ldap_conf.authenticate(self.env.user.login, password):
                        return
            raise
