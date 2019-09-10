##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.modules.registry import RegistryManager
from openerp.osv import osv, fields
import openerp.exceptions
from openerp import tools

import utils

class res_users(osv.osv):
    _inherit = 'res.users'

    # TODO create helper fields for autofill openid_url and openid_email -> http://pad.openerp.com/web-openid

    _columns = {
        'openid_url': fields.char('OpenID URL', size=1024, copy=False),
        'openid_email': fields.char('OpenID Email', size=256, copy=False,
                                    help="Used for disambiguation in case of a shared OpenID URL"),
        'openid_key': fields.char('OpenID Key', size=utils.KEY_LENGTH,
                                  readonly=True, copy=False),
    }

    def _check_openid_url_email(self, cr, uid, ids, context=None):
        return all(self.search_count(cr, uid, [('active', '=', True), ('openid_url', '=', u.openid_url), ('openid_email', '=', u.openid_email)]) == 1 \
                   for u in self.browse(cr, uid, ids, context) if u.active and u.openid_url)

    def _check_openid_url_email_msg(self, cr, uid, ids, context):
        return "There is already an active user with this OpenID Email for this OpenID URL"

    _constraints = [
        (_check_openid_url_email, lambda self, *a, **kw: self._check_openid_url_email_msg(*a, **kw), ['active', 'openid_url', 'openid_email']),
    ]

    def _login(self, db, login, password):
        result = super(res_users, self)._login(db, login, password)
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

    def check_credentials(self, cr, uid, password):
        try:
            return super(res_users, self).check_credentials(cr, uid, password)
        except openerp.exceptions.AccessDenied:
            cr.execute('''SELECT COUNT(1)
                            FROM res_users
                           WHERE id=%s
                             AND openid_key=%s
                             AND active=%s''',
                        (int(uid), password, True))
            if not cr.fetchone()[0]:
                raise

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
