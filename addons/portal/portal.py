# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
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
    """
        A portal is a group of users with specific menu, widgets, and typically
        restricted access rights.
    """
    _name = 'res.portal'
    _description = 'Portal'
    _inherits = {'res.groups': 'group_id'}
    
    _columns = {
        'group_id': fields.many2one('res.groups', required=True, ondelete='cascade',
            string='Group',
            help=_('The group extended by this portal')),
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
    
    def copy(self, cr, uid, id, values={}, context=None):
        """ override copy(): menu_action_id must be different """
        values['menu_action_id'] = None
        return super(portal, self).copy(cr, uid, id, values, context)
    
    def create(self, cr, uid, values, context=None):
        """ extend create() to assign the portal menu to users """
        if context is None:
            context = {}
        
        # first create the 'menu_action_id'
        assert not values.get('menu_action_id')
        values['menu_action_id'] = self._create_menu_action(cr, uid, values, context)
        
        # create portal (admin should not be included)
        context['noadmin'] = True
        portal_id = super(portal, self).create(cr, uid, values, context)
        
        # assign menu action and widgets to users
        self._assign_menu_to_users(cr, uid, [portal_id], context)
        self._assign_widgets_to_users(cr, uid, [portal_id], context)
        
        return portal_id
    
    def write(self, cr, uid, ids, values, context=None):
        """ extend write() to reflect menu and groups changes on users """
        # first apply portal changes
        super(portal, self).write(cr, uid, ids, values, context)
        
        # assign menu action and widgets to users
        self._assign_menu_to_users(cr, uid, ids, context)
        self._assign_widgets_to_users(cr, uid, ids, context)
        
        # if parent_menu_id has changed, apply the change on menu_action_id
        if 'parent_menu_id' in values:
            act_window_obj = self.pool.get('ir.actions.act_window')
            portals = self.browse(cr, uid, ids, context)
            action_ids = [p.menu_action_id.id for p in portals]
            action_values = {'domain': [('parent_id', '=', values['parent_menu_id'])]}
            act_window_obj.write(cr, uid, action_ids, action_values, context)
        
        return True
    
    def _create_menu_action(self, cr, uid, values, context=None):
        # create a menu action that opens the menu items below parent_menu_id
        groups_obj = self.pool.get('res.groups')
        actions_obj = self.pool.get('ir.actions.act_window')
        action_values = {
            'name': values['name'] + ' Menu',
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

    def _assign_menu_to_users(self, cr, uid, ids, context=None):
        """ assign portal menu action to users for the given portal ids """
        user_obj = self.pool.get('res.users')
        for p in self.browse(cr, uid, ids, context):
            user_values = {'menu_id': p.menu_action_id.id}
            user_obj.write(cr, uid, [u.id for u in p.users], user_values, context)

    def _assign_widgets_to_users(self, cr, uid, ids, context=None):
        """ assign portal widgets to users for the given portal ids """
        widget_user_obj = self.pool.get('res.widget.user')
        for p in self.browse(cr, uid, ids, context):
            for w in p.widget_ids:
                values = {'sequence': w.sequence, 'widget_id': w.widget_id.id}
                for u in p.user_ids:
                    if u.id == 1: continue
                    values['user_id'] = u.id
                    widget_user_obj.create(cr, uid, values, context)

    def _res_xml_id(self, cr, uid, module, xml_id):
        """ return the resource id associated to the given xml_id """
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, module, xml_id)
        return data_obj.browse(cr, uid, data_id).res_id

portal()



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



