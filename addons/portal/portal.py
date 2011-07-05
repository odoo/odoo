# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from osv import osv, fields
from tools.translate import _

class portal(osv.osv):
    _name = 'res.portal'
    _description = 'Portal'
    _rec_name = 'group_id'
    _columns = {
        'group_id': fields.many2one('res.groups', required=True,
            string='Portal Group',
            help=_('This group defines the users associated to this portal')),
        'user_ids': fields.related('group_id', 'users',
            type='many2many', relation='res.users', store=False,
            string='Portal Users'),
        'menu_action_id': fields.many2one('ir.actions.actions', readonly=True,
            string='Menu Action',
            help=_("What replaces the standard menu for the portal's users")),
        'parent_menu_id': fields.many2one('ir.ui.menu',
            string='Parent Menu',
            help=_('The menu action opens the submenus of this menu item')),
        'widget_ids': fields.one2many('res.portal.widget', 'portal_id',
            string='Widgets',
            help=_('Widgets assigned to portal users')),
    }
    _sql_constraints = [
        ('unique_group', 'UNIQUE(group_id)', _('Portals must have distinct groups.'))
    ]
    
    def copy(self, cr, uid, id, default={}, context=None):
        """ override copy(): group_id and menu_action_id must be different """
        # copy the former group_id
        groups_obj = self.pool.get('res.groups')
        group_id = self.browse(cr, uid, id, context).group_id.id
        default['group_id'] = groups_obj.copy(cr, uid, group_id, {}, context)
        default['menu_action_id'] = None
        return super(portal, self).copy(cr, uid, id, default, context)
    
    def create(self, cr, uid, values, context=None):
        """ extend create() to assign the portal group and menu to users """
        # first create the 'menu_action_id'
        assert not values.get('menu_action_id')
        values['menu_action_id'] = self._create_menu_action(cr, uid, values, context)
        
        if 'user_ids' in values:
            # set menu action of users
            user_values = {'menu_id': values['menu_action_id']}
            # values['user_ids'] should match [(6, 0, IDs)]
            for id in get_many2many(values['user_ids']):
                values['user_ids'].append((1, id, user_values))
        
        # create portal
        portal_id = super(portal, self).create(cr, uid, values, context)
        
        # assign widgets to users
        if 'user_ids' in values:
            self._assign_widgets_to_users(cr, uid, [portal_id], context)

        return portal_id
    
    def name_get(self, cr, uid, ids, context=None):
        portals = self.browse(cr, uid, ids, context)
        return [(p.id, p.group_id.name) for p in portals]
    
    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        # first search for group names that match
        groups_obj = self.pool.get('res.groups')
        group_names = groups_obj.name_search(cr, uid, name, args, operator, context, limit)
        # then search for portals that match the groups found so far
        domain = [('group_id', 'in', [gn[0] for gn in group_names])]
        ids = self.search(cr, uid, domain, context=context)
        return self.name_get(cr, uid, ids, context)
    
    def write(self, cr, uid, ids, values, context=None):
        """ extend write() to reflect menu and groups changes on users """
        # first apply portal changes
        super(portal, self).write(cr, uid, ids, values, context)
        portals = self.browse(cr, uid, ids, context)
        
        # if 'menu_action_id' has changed, set menu_id on users
        if 'menu_action_id' in values:
            user_values = {'menu_id': values['menu_action_id']}
            user_ids = [u.id for p in portals for u in p.user_ids if u.id != 1]
            self.pool.get('res.users').write(cr, uid, user_ids, user_values, context)
        
        # if parent_menu_id has changed, apply the change on menu_action_id
        if 'parent_menu_id' in values:
            act_window_obj = self.pool.get('ir.actions.act_window')
            action_ids = [p.menu_action_id.id for p in portals]
            action_values = {'domain': [('parent_id', '=', values['parent_menu_id'])]}
            act_window_obj.write(cr, uid, action_ids, action_values, context)
        
        # assign portal widgets to users, if widgets or users changed
        if ('user_ids' in values) or ('widget_ids' in values):
            self._assign_widgets_to_users(cr, uid, ids, context)
        
        return True
    
    def _create_menu_action(self, cr, uid, values, context=None):
        # create a menu action that opens the menu items below parent_menu_id
        groups_obj = self.pool.get('res.groups')
        group_name = groups_obj.browse(cr, uid, values['group_id'], context).name
        actions_obj = self.pool.get('ir.actions.act_window')
        action_values = {
            'name': group_name + ' Menu',
            'type': 'ir.actions.act_window',
            'usage': 'menu',
            'res_model': 'ir.ui.menu',
            'view_type': 'tree',
            'view_id': self._res_xml_id(cr, uid, 'base', 'view_menu'),
            'domain': [('parent_id', '=', values.get('parent_menu_id', False))],
        }
        return actions_obj.create(cr, uid, action_values, context)
    
    def do_create_menu(self, cr, uid, ids, context=None):
        """ create a parent menu for the given portals """
        menu_obj = self.pool.get('ir.ui.menu')
        menu_root = self._res_xml_id(cr, uid, 'portal', 'portal_menu')
        
        for p in self.browse(cr, uid, ids, context):
            # create a menuitem under 'portal.portal_menu'
            menu_values = {
                'name': p.group_id.name + ' Menu',
                'parent_id': menu_root,
                'groups_id': [(6, 0, [p.group_id.id])],
            }
            menu_id = menu_obj.create(cr, uid, menu_values, context)
            # set the parent_menu_id to item_id
            self.write(cr, uid, [p.id], {'parent_menu_id': menu_id}, context)
        
        return True

    def _assign_widgets_to_users(self, cr, uid, ids, context=None):
        """ assign portal widgets to users for the given portal ids """
        widget_user_obj = self.pool.get('res.widget.user')
        portals = self.browse(cr, uid, ids, context)
        for p in portals:
            for w in p.widget_ids:
                values = {'sequence': w.sequence, 'widget_id': w.widget_id.id}
                for u in p.user_ids:
                    if u.id == 1: continue
                    values['user_id'] = u.id
                    widget_user_obj.create(cr, uid, values, context)

    def onchange_group(self, cr, uid, ids, group_id, context=None):
        """ update the users list when the group changes """
        user_ids = False
        if group_id:
            group = self.pool.get('res.groups').browse(cr, uid, group_id, context)
            user_ids = [u.id for u in group.users]
        return {
            'value': {'user_ids': user_ids}
        }
    
    def _res_xml_id(self, cr, uid, module, xml_id):
        """ return the resource id associated to the given xml_id """
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, module, xml_id)
        return data_obj.browse(cr, uid, data_id).res_id

portal()



class users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    
    def default_get(self, cr, uid, fields, context=None):
        """ override default value of menu_id for portal users """
        defs = super(users, self).default_get(cr, uid, fields, context)
        
        # the value of 'menu_id' is passed in context by the portal form view
        if ('menu_id' in context) and ('menu_id' in fields):
            defs['menu_id'] = context['menu_id']
        
        return defs

users()



class portal_widget(osv.osv):
    """
        Similar to res.widget.user (res_widget.py), but with a portal instead.
        New users in a portal are assigned the portal's widgets.
    """
    _name='res.portal.widget'
    _description = 'Portal Widgets'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'portal_id': fields.many2one('res.portal', select=1,
            string='Portal'),
        'widget_id': fields.many2one('res.widget', required=True, ondelete='cascade',
            string='Widget'),
    }

    def create(self, cr, uid, values, context=None):
        domain = [('portal_id', '=', values.get('portal_id')),
                  ('widget_id', '=', values.get('widget_id'))]
        existing = self.search(cr, uid, domain, context=context)
        if existing:
            res = existing[0]
        else:
            res = super(portal_widget, self).create(cr, uid, values, context=context)
        return res

portal_widget()



# utils
def get_browse_id(obj):
    """ return the id of a browse() object, or None """
    return (obj and obj.id or None)

def get_browse_ids(objs):
    """ return the ids of a list of browse() objects """
    return map(get_browse_id, objs)

def get_many2many(arg):
    """ get the list of ids from a many2many 'values' field """
    assert len(arg) == 1 and arg[0][0] == 6             # arg = [(6, _, IDs)]
    return arg[0][2]

