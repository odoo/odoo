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

class groups_wizard(osv.osv_memory):
    _name = 'res.portal.groups'
    _description = 'Portal Groups Wizard'
    _columns = {
        'portal_id': fields.many2one('res.portal', required=True, readonly=True,
            string='Portal'),
        'add_group_ids': fields.many2many('res.groups',
            'portal_groups_add', 'portal_groups_id', 'group_ids',
            string='Add Groups'),
        'remove_group_ids': fields.many2many('res.groups',
            'portal_groups_remove', 'portal_groups_id', 'group_ids',
            string='Remove Groups'),
    }
    _defaults = {
        'portal_id': (lambda self,cr,uid,context: context and context.get('active_id'))
    }
    
    def do_apply(self, cr, uid, ids, context=None, *args):
        assert len(ids) == 1
        wizard = self.browse(cr, uid, ids[0], context)
        
        # select all portal users except admin
        user_ids = [u.id for u in wizard.portal_id.user_ids if u.id != 1]
        
        # apply group adds and removals to portal users
        add_gids = [(4, g.id) for g in wizard.add_group_ids]
        rem_gids = [(3, g.id) for g in wizard.remove_group_ids]
        user_values = {'groups_id': add_gids + rem_gids}
        self.pool.get('res.users').write(cr, uid, user_ids, user_values, context)
        
        # return an empty dictionary to close the wizard window
        return {}

groups_wizard()

