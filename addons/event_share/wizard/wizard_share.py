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

UID_ROOT = 1
EVENT_ACCESS = ('perm_read', 'perm_write', 'perm_create')

class share_wizard_event(osv.osv_memory):
    """Inherited share wizard to automatically create appropriate
       menus in the selected portal upon sharing with a portal group."""
    _inherit = "share.wizard"
    
    def _add_access_rights_for_share_group(self, cr, uid, group_id, mode, fields_relations, context=None):
        print "Calling _add_access_rights_for_share_group.....!!!"
        """Adds access rights to group_id on object models referenced in ``fields_relations``,
           intersecting with access rights of current user to avoid granting too much rights
        """
        res = super(share_wizard_event, self)._add_access_rights_for_share_group(cr, uid, group_id, mode, fields_relations, context=context)
        access_model = self.pool.get('ir.model.access')
        
        access_ids =  access_model.search(cr,uid,[('group_id','=',group_id)],context = context)
        for record in access_model.browse(cr,uid,access_ids,context = context):
            if record.model_id.model == 'event.registration':
                access_model.write(cr, uid, record.id, {'perm_read': True, 'perm_write': True,'perm_create':True})

share_wizard_event()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: