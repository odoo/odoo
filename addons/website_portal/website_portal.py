# -*- coding: utf-8 -*-
import threading
import openerp
from openerp.osv import orm, osv, fields
from openerp import api, tools

# We need to add access rights to website menu
class website_menu(osv.osv):
    _name = 'website.menu'
    _inherit = 'website.menu'
    _columns = {
        'groups_id': fields.many2many('res.groups', 'ir_ui_webmenu_group_rel',
        'menu_id', 'gid', 'Groups', help="If you have groups, the visibility of this menu will be based on these groups.")
    }

    # caching and acess rights adapted from ir_ui_menu
    def __init__(self, *args, **kwargs):
        cls = type(self)
        # by design, self._menu_cache is specific to the database
        cls._menu_cache_lock = threading.RLock()
        cls._menu_cache = {}
        super(website_menu, self).__init__(*args, **kwargs)
        self.pool.get('ir.model.access').register_cache_clearing_method(self._name, 'clear_cache')

    def clear_cache(self):
        with self._menu_cache_lock:
            # radical but this doesn't frequently happen
            if self._menu_cache:
                # Normally this is done by openerp.tools.ormcache
                # but since we do not use it, set it by ourself.
                self.pool._any_cache_cleared = True
            self._menu_cache.clear()

    @api.multi
    @api.returns('self')
    def _filter_visible_menus(self):
        with self._menu_cache_lock:
            groups = self.env.user.groups_id
            key = frozenset(groups._ids)
            
            # if menu cache is available for this group, we avoid unnecessary computation
            if key in self._menu_cache:
                visible = self.browse(self._menu_cache[key])

            else:
                # retrieve all menus, and determine which ones are visible
                context = {'website.menu.full_list': True}
                menus = self.with_context(context).search([])

                # discard all menus with groups the user does not have
                visible = menus.filtered(
                    lambda menu: not menu.groups_id or menu.groups_id & groups)

                self._menu_cache[key] = visible._ids

            return self.filtered(lambda menu: menu in visible)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        ids = super(website_menu, self).search(cr, uid, args, offset=0,
            limit=None, order=order, context=context, count=False)

        if not ids:
            if count:
                return 0
            return []

        # menu filtering is done only on main menu tree, not other menu lists
        if context.get('website.menu.full_list'):
            result = ids
        else:
            result = self._filter_visible_menus(cr, uid, ids, context=context)

        if offset:
            result = result[offset:]
        if limit:
            result = result[:limit]

        if count:
            return len(result)
        return result

    def create(self, cr, uid, values, context=None):
        self.clear_cache()
        return super(website_menu, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        self.clear_cache()
        return super(website_menu, self).write(cr, uid, ids, values, context=context)