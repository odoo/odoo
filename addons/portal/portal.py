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
import random

class portal(osv.osv):
    _name = 'res.portal'
    _description = 'Portal'
    _columns = {
        'name': fields.char(string='Name', size=64, required=True),
        'menu_id': fields.many2one('ir.actions.actions', required="True",
            string='Menu Action',
            help="The customized menu of the portal's users"),
        'user_ids': fields.one2many('res.users', 'portal_id',
            string='Users',
            help='Gives the set of users associated to this portal'),
        'group_ids': fields.many2many('res.groups', 'res_portals_groups_rel', 'pid', 'gid',
            string='Groups',
            help='Users of this portal automatically belong to those groups'),
    }
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Portals must have different names.')
    ]
    
    def copy(self, cr, uid, id, defaults, context=None):
        """ override copy() to not copy the portal users """
        # find an unused name of the form "old_name [N]" for some random N
        old_name = self.browse(cr, uid, id, context).name
        new_name = copy_random(old_name)
        while self.search(cr, uid, [('name', '=', new_name)], limit=1, context=context):
            new_name = copy_random(old_name)
        
        defaults['name'] = new_name
        defaults['user_ids'] = []
        return super(portal, self).copy(cr, uid, id, defaults, context)
    
    def create(self, cr, uid, values, context=None):
        """ extend create() to assign the portal menu and groups to users """
        # as 'user_ids' is a many2one relation, values['user_ids'] must be a
        # list of tuples of the form (0, 0, {values})
        for op, _, user_values in values['user_ids']:
            assert op == 0
            user_values['menu_id'] = values['menu_id']
            user_values['groups_id'] = values['group_ids']
        
        return super(portal, self).create(cr, uid, values, context)
    
    def write(self, cr, uid, ids, values, context=None):
        """ extend write() to reflect menu and groups changes on users """
        
        # analyse groups changes, and determine how to change users
        groups_diff = []
        for change in values.get('group_ids', []):
            if change[0] in [0, 5, 6]:          # change creates or sets groups,
                groups_diff = None              # must compute per-portal diff
                break
            if change[0] in [3, 4]:             # change add or remove group,
                groups_diff.append(change)      # add or remove group on users
        
        if groups_diff is None:
            return self._write_compute_diff(cr, uid, ids, values, context)
        else:
            return self._write_diff(cr, uid, ids, values, groups_diff, context)
    
    def _write_diff(self, cr, uid, ids, values, groups_diff, context=None):
        """ perform write() and apply groups_diff on users """
        # first apply portal changes
        super(portal, self).write(cr, uid, ids, values, context)
        
        # then apply menu and group changes on their users
        user_values = {}
        if 'menu_id' in values:
            user_values['menu_id'] = values['menu_id']
        if groups_diff:
            user_values['groups_id'] = groups_diff
        
        if user_values:
            user_ids = []
            for p in self.browse(cr, uid, ids, context):
                user_ids += get_browse_ids(p.user_ids)
            self.pool.get('res.users').write(cr, uid, user_ids, user_values, context)
        
        return True
    
    def _write_compute_diff(self, cr, uid, ids, values, context=None):
        """ perform write(), then compute and apply groups_diff on each portal """
        # read group_ids before write() to compute groups_diff
        old_group_ids = {}
        for p in self.browse(cr, uid, ids, context):
            old_group_ids[p.id] = get_browse_ids(p.group_ids)
        
        # apply portal changes
        super(portal, self).write(cr, uid, ids, values, context)
        
        # the changes to apply on users
        user_object = self.pool.get('res.users')
        user_values = {}
        if 'menu_id' in values:
            user_values['menu_id'] = values['menu_id']
        
        # compute groups_diff on each portal, and apply them on users
        for p in self.browse(cr, uid, ids, context):
            old_groups = set(old_group_ids[p.id])
            new_groups = set(get_browse_ids(p.group_ids))
            # groups_diff: [(3, UNLINKED_ID), ..., (4, LINKED_ID), ...]
            user_values['groups_id'] = \
                [(3, g) for g in (old_groups - new_groups)] + \
                [(4, g) for g in (new_groups - old_groups)]
            user_ids = get_browse_ids(p.user_ids)
            user_object.write(cr, uid, user_ids, user_values, context)
        
        return True
    
    def action_create_menu(self, cr, uid, ids, context=None):
        """ create a menu for this portal """
        if len(ids) != 1:
            raise ValueError("portal.action_create_menu() applies to one portal only")
        portal_name = self.browse(cr, uid, ids[0], context).name
        
        # create a menuitem under 'portal.portal_menu_tree'
        item_data = {
            'name': portal_name,
            'parent_id': self._get_res_id(cr, uid, 'portal', 'portal_menu_tree'),
        }
        item_id = self.pool.get('ir.ui.menu').create(cr, uid, item_data, context)
        
        # create an action to open the menuitems under item_id
        action_data = {
            'name': portal_name,
            'type': 'ir.actions.act_window',
            'usage': 'menu',
            'res_model': 'ir.ui.menu',
            'view_type': 'tree',
            'view_id': self._get_res_id(cr, uid, 'base', 'view_menu'),
            'domain': [('parent_id', '=', item_id)],
        }
        action_id = self.pool.get('ir.actions.act_window').create(cr, uid, action_data, context)
        
        # set the portal menu_id to action_id
        return self.write(cr, uid, ids, {'menu_id': action_id}, context)
    
    def _get_res_id(self, cr, uid, module, xml_id):
        """ return the resource id associated to the given xml_id """
        ir_model_data_obj = self.pool.get('ir.model.data')
        record_id = ir_model_data_obj._get_id(cr, uid, module, xml_id)
        record_data = ir_model_data_obj.read(cr, uid, [record_id], ['res_id'])
        assert (len(record_data) == 1) and ('res_id' in record_data[0])
        return record_data[0]['res_id']

portal()

class users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    _columns = {
        'portal_id': fields.many2one('res.portal', string='Portal',
            help='If given, the portal defines customized menu and access rules'),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ override default values of menu_id and groups_id for portal users """
        others = {}
        # How it works: the values of 'menu_id' and 'groups_id' are passed in
        # context by the portal form view
        if ('menu_id' in context) and ('menu_id' in fields):
            fields.remove('menu_id')
            others['menu_id'] = context['menu_id']
        if ('groups_id' in context) and ('groups_id' in fields):
            fields.remove('groups_id')
            others['groups_id'] = get_many2many(context['groups_id'])
        # the remaining fields use inherited defaults
        defs = super(users, self).default_get(cr, uid, fields, context)
        defs.update(others)
        return defs

users()

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

def copy_random(name):
    """ return "name [N]" for some random integer N """
    return "%s [%s]" % (name, random.choice(xrange(1000000)))

