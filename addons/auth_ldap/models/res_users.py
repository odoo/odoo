# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessDenied

from odoo import models
from odoo.modules.registry import Registry


class ResUsers(models.Model):
    _inherit = "res.users"

    def _login(self, credential, user_agent_env):
        try:
            return super()._login(credential, user_agent_env=user_agent_env)
        except AccessDenied:
            login = credential['login']
            self.env.cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
            res = self.env.cr.fetchone()
            if res:
                raise

            Ldap = self.env['res.company.ldap'].sudo()
            for conf in Ldap._get_ldap_dicts():
                entry = Ldap._authenticate(conf, login, credential['password'])
                if entry:
                    return {
                        'uid': Ldap._get_or_create_user(conf, login, entry),
                        'auth_method': 'ldap',
                        'mfa': 'default',
                    }
            raise

    def _check_credentials(self, credential, env):
        try:
            return super()._check_credentials(credential, env)
        except AccessDenied:
            if not (credential['type'] == 'password' and credential.get('password')):
                raise
            passwd_allowed = env['interactive'] or not self.env.user._rpc_api_keys_only()
            if passwd_allowed and self.env.user.active:
                Ldap = self.env['res.company.ldap']
                for conf in Ldap._get_ldap_dicts():
                    if Ldap._authenticate(conf, self.env.user.login, credential['password']):
                        return {
                            'uid': self.env.user.id,
                            'auth_method': 'ldap',
                            'mfa': 'default',
                        }
            raise

    def _change_password(self, new_passwd):
        if new_passwd:
            Ldap = self.env['res.company.ldap']
            for conf in Ldap._get_ldap_dicts():
                changed = Ldap._change_password(conf, self.login, new_passwd)
                if changed:
                    self._log_change_password("LDAP password")
                    self._set_empty_password()
                    return True
        return super()._change_password(new_passwd)

    def _set_empty_password(self):
        self.flush_recordset(['password'])
        self.env.cr.execute(
            'UPDATE res_users SET password=NULL WHERE id=%s',
            (self.id,)
        )
        self.invalidate_recordset(['password'])
