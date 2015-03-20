# -*- coding: utf-8 -*-

from .. import utils

from openerp import api, fields, models, tools
from openerp.exceptions import AccessDenied, ValidationError
from openerp.modules.registry import RegistryManager


class ResUsers(models.Model):

    _inherit = 'res.users'

    # TODO create helper fields for autofill openid_url and openid_email -> http://pad.openerp.com/web-openid

    openid_url = fields.Char(string='OpenID URL', copy=False)
    openid_email = fields.Char(string='OpenID Email', size=256, copy=False, help="Used for disambiguation in case of a shared OpenID URL")
    openid_key = fields.Char(string='OpenID Key', size=utils.KEY_LENGTH, readonly=True, copy=False)

    @api.one
    @api.constrains('active', 'openid_url', 'openid_email')
    def _check_openid_url_email(self):
        if self.active and self.openid_url and self.env['res.users'].search_count([('active', '=', True), ('openid_url', '=', self.openid_url), ('openid_email', '=', self.openid_email)]) == 2:
            raise ValidationError("There is already an active user with this OpenID Email for this OpenID URL")

    def _login(self, db, login, password):
        result = super(ResUsers, self)._login(db, login, password)
        if result:
            return result
        else:
            with RegistryManager.get(db).cursor() as cr:
                cr.execute("""UPDATE res_users
                                SET login_date=now() AT TIME ZONE 'UTC'
                                WHERE login=%s AND openid_key=%s AND active=%s RETURNING id""",
                           (tools.ustr(login), tools.ustr(password), True))
                # beware: record cache may be invalid
                res = cr.fetchone()
                cr.commit()
                return res[0] if res else False

    def check(self, db, uid, passwd):
        try:
            return super(ResUsers, self).check(db, uid, passwd)
        except AccessDenied:
            if not passwd:
                raise
            with RegistryManager.get(db).cursor() as cr:
                cr.execute('''SELECT COUNT(1) FROM res_users WHERE id=%s AND openid_key=%s AND active=%s''', (int(uid), passwd, True))
                if not cr.fetchone()[0]:
                    raise
                self._uid_cache.setdefault(db, {})[uid] = passwd
