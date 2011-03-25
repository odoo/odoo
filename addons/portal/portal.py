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
        """ extend write() to assign the portal menu and groups to users """
        user_object = self.pool.get('res.users')
        
        # first apply changes on the portals themselves
        super(portal, self).write(cr, uid, ids, values, context)
        
        # then reflect changes on the users of each portal
        #
        # PERFORMANCE NOTE.  The loop below performs N write() operations, where
        # N=len(ids).  This may seem inefficient, but in practice it is not,
        # because: (1) N is pretty small (typically N=1), and (2) it is too
        # complex (read: bug-prone) to write those updates as a single batch.
        #
        plist = self.browse(cr, uid, ids, context)
        for p in plist:
            user_ids  = get_browse_ids(p.user_ids)
            user_values = {
                'menu_id': get_browse_id(p.menu_id),
                'groups_id': [(6, 0, get_browse_ids(p.group_ids))],
            }
            user_object.write(cr, uid, user_ids, user_values, context)
        
        return True

portal()

class users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'
    _columns = {
        'portal_id': fields.many2one('res.portal', string='Portal',
            help='If given, the portal defines customized menu and access rules'),
    }

users()

# utils
def get_browse_id(obj):
    """ return the id of a browse() object, or None """
    return (obj and obj.id or None)

def get_browse_ids(objs):
    """ return the ids of a list of browse() objects """
    return [(obj and obj.id or default) for obj in objs]

