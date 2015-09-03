# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessDenied

from odoo import api, models, registry, SUPERUSER_ID


class Users(models.Model):
    _inherit = "res.users"

    def _login(self, db, login, password):
        user_id = super(Users, self)._login(db, login, password)
        if user_id:
            return user_id
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
            res = cr.fetchone()
            if res:
                return False
            Ldap = env['res.company.ldap']
            for conf in Ldap.get_ldap_dicts():
                entry = Ldap.authenticate(conf, login, password)
                if entry:
                    user_id = Ldap.sudo().get_or_create_user(conf, login, entry)
                    if user_id:
                        break
            return user_id

    @api.model
    def check_credentials(self, password):
        try:
            super(Users, self).check_credentials(password)
        except AccessDenied:
            if self.env.user.active:
                Ldap = self.env['res.company.ldap']
                for conf in Ldap.get_ldap_dicts():
                    if Ldap.authenticate(conf, self.env.user.login, password):
                        return
            raise
