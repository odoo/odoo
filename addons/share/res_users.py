# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
