# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessDenied

from odoo import api, models, registry, SUPERUSER_ID


class Users(models.Model):
    _inherit = "res.users"

    @classmethod
    def _login(cls, db, login, password):
        try:
            return super(Users, cls)._login(db, login, password)
        except AccessDenied as e:
            with registry(db).cursor() as cr:
                cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
                res = cr.fetchone()
                if res:
                    raise e

                env = api.Environment(cr, SUPERUSER_ID, {})
                Ldap = env['res.company.ldap']
                for conf in Ldap._get_ldap_dicts():
                    entry = Ldap._authenticate(conf, login, password)
                    if entry:
                        return Ldap._get_or_create_user(conf, login, entry)
                raise e

    def _check_credentials(self, password):
        try:
            super(Users, self)._check_credentials(password)
        except AccessDenied:
            if self.env.user.active:
                Ldap = self.env['res.company.ldap']
                for conf in Ldap._get_ldap_dicts():
                    if Ldap._authenticate(conf, self.env.user.login, password):
                        return
            raise

    @api.model
    def change_password(self, old_passwd, new_passwd):
        if new_passwd:
            Ldap = self.env['res.company.ldap']
            for conf in Ldap._get_ldap_dicts():
                changed = Ldap._change_password(conf, self.env.user.login, old_passwd, new_passwd)
                if changed:
                    uid = self.env.user.id
                    self._set_empty_password(uid)
                    self.invalidate_cache(['password'], [uid])
                    return True
        return super(Users, self).change_password(old_passwd, new_passwd)

    def _set_empty_password(self, uid):
        self.env.cr.execute(
            'UPDATE res_users SET password=NULL WHERE id=%s',
            (uid,)
        )
