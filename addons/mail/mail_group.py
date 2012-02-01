# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import tools
from osv import osv
from osv import fields
from tools.translate import _

class mail_group(osv.osv):
    """
    A mail group is a collection of users sharing messages. Mail groups are different from user groups
    because they don't have a specific field holding users. Group users are users that follow
    the mail group, using the subscription/follow mechanism of Chatter.
    """
    
    _name = 'mail.group'
    _inherits = {'res.groups': 'group_id'}

    def action_group_join(self, cr, uid, ids, context={}):
        sub_obj = self.pool.get('mail.subscription')
        menu_values = {'res_model': 'mail.group', 'user_id': uid}
        for id in ids:
            menu_values['res_id'] = id
            sub_id = sub_obj.create(cr, uid, menu_values, context=context)
        
        for group in self.browse(cr, uid, ids, context):
            self.write(cr, uid, group.id, {
                'users': [(4, uid)]
                })
        
        return True
    
    _columns = {
        'group_id': fields.many2one('res.groups', required=True, ondelete='cascade',
            string='Group',
            help='The group extended by this portal'),
        #'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'responsible_id': fields.many2one('res.users', string='Responsible',
                            ondelete='set null', required=True),
        'public': fields.boolean('Public', help='This group is visible by non members')
    }

    _defaults = {
        'public': True,
    }
    
    
    def create(self, cr, uid, values, context=None):
        """ extend create() to automatically create a menu for the group """
        if context is None: context = {}
        # create group
        group_id = super(mail_group, self).create(cr, uid, values, context)
        # create menu
        self._create_menu(cr, uid, [group_id], context)
        return group_id
    
    def _create_menu(self, cr, uid, ids, context=None):
        """ create a menu for the given groups """
        menu_obj = self.pool.get('ir.ui.menu')
        ir_data = self.pool.get('ir.model.data')
        act_win_obj = self.pool.get('ir.actions.act_window')
        menu_root = self._get_res_xml_id(cr, uid, 'mail', 'mg_groups')
        
        for group in self.browse(cr, uid, ids, context):
            # create an ir.action.act_window action
            act_values = {
                'name': '%s' % group.name,
                'res_model': 'mail.message',
                'domain': '["&", ("res_model", "=", "mail.group"), ("res_id", "=", %s)]' % group.id,
                }
            act_id = act_win_obj.create(cr, uid, act_values, context)
            # create a menuitem under 'mail.mg_groups'
            menu_values = {
                'name': _('%s') % group.name,
                'parent_id': menu_root,
                'action': 'ir.actions.act_window,%s' % (act_id),
                'groups_id': [(6, 0, [group.group_id.id])],
            }
            menu_id = menu_obj.create(cr, uid, menu_values, context)
            # create data
            data_values = {
                'name': _('%s') % group.name,
                'model': 'ir.ui.menu',
                'module': 'portal',
                'res_id': menu_id,
                'noupdate': 'True'}
            data_id = ir_data.create(cr, uid, data_values, context)
        return True
    
    def _assign_menu(self, cr, uid, ids, context=None):
        """ assign groups (ids) menu to the users joigning the groups"""
        user_obj = self.pool.get('res.users')
        for p in self.browse(cr, uid, ids, context):
            # user menu action = portal menu action if set in portal
            if p.menu_action_id:
                user_ids = [u.id for u in p.users if u.id != 1]
                user_values = {'menu_id': p.menu_action_id.id}
                user_obj.write(cr, uid, user_ids, user_values, context)
    
    def _get_res_xml_id(self, cr, uid, module, xml_id):
        """ return the resource id associated to the given xml_id """
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, module, xml_id)
        return data_obj.browse(cr, uid, data_id).res_id
    

mail_group()
