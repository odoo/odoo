# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'

    def _is_share(self, cr, uid, ids, name, args, context=None):
        res = {}
        for user in self.browse(cr, uid, ids, context=context):
            res[user.id] = not self.has_group(cr, user.id, 'base.group_user')
        return res

    def _get_users_from_group(self, cr, uid, ids, context=None):
        result = set()
        groups = self.pool['res.groups'].browse(cr, uid, ids, context=context)
        # Clear cache to avoid perf degradation on databases with thousands of users 
        groups.invalidate_cache()
        for group in groups:
            result.update(user.id for user in group.users)
        return list(result)

    _columns = {
        'share': fields.function(_is_share, string='Share User', type='boolean',
            store={
                'res.users': (lambda self, cr, uid, ids, c={}: ids, None, 50),
                'res.groups': (_get_users_from_group, None, 50),
            }, help="External user with limited access, created only for the purpose of sharing data."),
     }


class res_groups(osv.osv):
    _name = "res.groups"
    _inherit = 'res.groups'
    _columns = {
        'share': fields.boolean('Share Group', readonly=True,
                    help="Group created to set access rights for sharing data with some users.")
    }

    def init(self, cr):
        # force re-generation of the user groups view without the shared groups
        self.update_user_groups_view(cr, SUPERUSER_ID)
        parent_class = super(res_groups, self)
        if hasattr(parent_class, 'init'):
            parent_class.init(cr)

    def get_application_groups(self, cr, uid, domain=None, context=None):
        if domain is None:
            domain = []
        domain.append(('share', '=', False))
        return super(res_groups, self).get_application_groups(cr, uid, domain=domain, context=context)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
