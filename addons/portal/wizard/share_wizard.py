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

from osv import osv

UID_ROOT = 1
SHARED_DOCS_MENU = "Shared Documents"

class share_wizard_portal(osv.osv_memory):
    """Inherited share wizard to automatically create appropriate
       menus in the selected portal upon sharing with a portal group."""
    _inherit = "share.wizard"

    def _sharing_root_menu_id(self, cr, uid, portal, context=None):
        """Create or retrieve root ID of sharing menu in portal menu

           :param portal: browse_record of portal, constructed with a context WITHOUT language
        """
        if not portal.parent_menu_id:
            # no specific parent menu, cannot create the sharing menu at all.
            return
        # look for an existing SHARED_DOCS_MENU
        sharing_root_menu_id = None
        for child_menu in portal.parent_menu_id.child_id:
            if child_menu.name == SHARED_DOCS_MENU:
                sharing_root_menu_id = child_menu.id
                break
        if not sharing_root_menu_id:
            # not found, create it
            sharing_root_menu_id = self.pool.get('ir.ui.menu').create(cr, UID_ROOT,
                                            {'name': SHARED_DOCS_MENU,
                                             'parent_id': portal.parent_menu_id.id,
                                             'sequence': 999, # at the bottom
                                            })
        return sharing_root_menu

    def _create_shared_data_menu(self, cr, uid, wizard_data, portal, context=None):
        """Create sharing menus in portal menu according to share wizard options.

           :param wizard_data: browse_record of share.wizard
           :param portal: browse_record of portal, constructed with a context WITHOUT language
        """
        root_menu_id = self._sharing_root_menu_id(cr, uid, portal, context=context)
        if not root_menu_id:
            # no specific parent menu, cannot create the sharing menu at all.
            return
        # Create the shared action and menu
        action_def = self._shared_action_def(cr, uid, wizard_data, context=None)
        action_id = self.pool.get('ir.actions.act_window').create(cr, UID_ROOT, action_def)
        menu_data = {'name': action_def['name'],
                     'sequence': 10,
                     'action': 'ir.actions.act_window,'+str(action_id),
                     'parent_id': root_menu_id,
                     'icon': 'STOCK_JUSTIFY_FILL'}
        menu_id =  self.pool.get('ir.ui.menu').create(cr, UID_ROOT, menu_data)
        return menu_id

    def _create_share_users_groups(self, cr, uid, wizard_data, context=None):
        """Create sharing menus in portal menu after sharing"""
        group_ids = super(share_wizard_portal,self)._create_share_users_groups(cr, uid, wizard_data, context=context)
        if wizard_data.user_type == "groups":
            # get the list of portals and the related groups
            Portals = self.pool.get('res.portal')
            all_portals = Portals.browse(cr, UID_ROOT, Portals.search(cr, UID_ROOT, [])) #no context!
            all_portal_group_ids = [p.group_id.id for p in all_portals]
            for group in wizard_data.group_ids:
                if group.id in all_portal_group_ids:
                    portal = all_portals[all_portal_group_ids.index(group.id)]
                    self._create_shared_data_menu(cr, uid, wizard_data, portal, context=context)
        return group_ids

share_wizard_portal()