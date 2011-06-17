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

UID_ROOT = 1
SHARED_DOCS_MENU = "Documents"
SHARED_DOCS_CHILD_MENU = "Shared Documents"

class share_wizard_portal(osv.osv_memory):
    """Inherited share wizard to automatically create appropriate
       menus in the selected portal upon sharing with a portal group."""
    _inherit = "share.wizard"

    _columns = {
        'user_ids': fields.many2many('res.users', 'share_wizard_res_user_rel', 'share_id', 'user_id', 'Existing users', domain=[('share', '=', True)]),
        'group_ids': fields.many2many('res.groups', 'share_wizard_res_group_rel', 'share_id', 'group_id', 'Existing groups', domain=[('share', '=', False)]),
    }

    def is_portal_manager(self, cr, uid, context=None):
        return self.has_group(cr, uid, module='portal', group_xml_id='group_portal_manager', context=context)

    def has_share(self, cr, uid, context=None):
        return self.has_extended_share(cr, uid, context=context) or \
               super(share_wizard_portal, self).has_share(cr, uid, context=context)

    def _user_type_selection(self, cr, uid, context=None):
        selection = super(share_wizard_portal, self)._user_type_selection(cr, uid, context=context)
        if self.is_portal_manager(cr, uid, context=context):
            selection.extend([('existing','Users you already shared with'),
                              ('groups','Portal Groups')])
        return selection

    def _check_preconditions(self, cr, uid, wizard_data, context=None):
        if wizard_data.user_type == 'existing':
            self._assert(wizard_data.user_ids,
                     _('Please select at least one user to share with'),
                     context=context)
        elif wizard_data.user_type == 'groups':
            self._assert(wizard_data.group_ids,
                     _('Please select at least one group to share with'),
                     context=context)
        return super(share_wizard_portal, self)._check_preconditions(cr, uid, wizard_data, context=context)

    def _create_or_get_submenu_named(self, cr, uid, parent_menu_id, menu_name, context=None):
        if not parent_menu_id:
            return
        Menus = self.pool.get('ir.ui.menu')
        parent_menu = Menus.browse(cr, uid, parent_menu_id) # No context
        menu_id = None
        max_seq = 10
        for child_menu in parent_menu.child_id:
            max_seq = max(max_seq, child_menu.sequence)
            if child_menu.name == menu_name:
                menu_id = child_menu.id
                break
        if not menu_id:
            # not found, create it
            menu_id = Menus.create(cr, UID_ROOT,
                                    {'name': menu_name,
                                     'parent_id': parent_menu.id,
                                     'sequence': max_seq + 10, # at the bottom
                                    })
        return menu_id

    def _sharing_root_menu_id(self, cr, uid, portal, context=None):
        """Create or retrieve root ID of sharing menu in portal menu

           :param portal: browse_record of portal, constructed with a context WITHOUT language
        """
        parent_menu_id = self._create_or_get_submenu_named(cr, uid, portal.parent_menu_id.id, SHARED_DOCS_MENU, context=context)
        if parent_menu_id:
            child_menu_id = self._create_or_get_submenu_named(cr, uid, parent_menu_id, SHARED_DOCS_CHILD_MENU, context=context)
            return child_menu_id

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
        """Creates the appropriate shared users and groups, and populates
           result_line_ids of wizard_data with one line for each user. 

           :return: group_ids (to which the shared access should be granted),
                    new_user_ids, and existing_user_ids.
        """
        group_ids, new_ids, existing_ids = [], [], []

        if wizard_data.user_type == 'groups':
            group_id = None
            group_ids.extend([g.id for g in wizard_data.group_ids])
            # populate result lines with the users of each group
            for group in wizard_data.group_ids:
                for user in group.users:
                    new_line = {'login': user.login,
                                'newly_created': False}
                    wizard_data.write({'result_line_ids': [(0,0,new_line)]})

            # get the list of portals and the related groups
            # and install their menus.
            Portals = self.pool.get('res.portal')
            all_portals = Portals.browse(cr, UID_ROOT, Portals.search(cr, UID_ROOT, [])) #no context!
            all_portal_group_ids = [p.group_id.id for p in all_portals]
            for group in wizard_data.group_ids:
                if group.id in all_portal_group_ids:
                    portal = all_portals[all_portal_group_ids.index(group.id)]
                    self._create_shared_data_menu(cr, uid, wizard_data, portal, context=context)

        else:
            # for other case with user_type in ('emails', 'existing'), we rely on super()
            group_ids, new_ids, existing_ids = super(share_wizard_portal,self)._create_share_users_groups(cr, uid, wizard_data, context=context)

            # must take care of existing users, by adding them to the new group, which is group_ids[0],
            # and adding the shortcut
            existing_user_ids = [x.id for x in wizard_data.user_ids] # manually selected users
            if existing_user_ids:
                self.pool.get('res.users').write(cr, UID_ROOT, existing_user_ids, {'groups_id': [(4,group_id)]})
                self._setup_action_and_shortcut(cr, uid, wizard_data, existing_ids, make_home=False, context=context)
                existing_ids.extend(existing_user_ids)
                # populate the result lines for existing users too
                for user in wizard_data.user_ids:
                    new_line = { 'login': user.login,
                                 'newly_created': False}
                    wizard_data.write({'result_line_ids': [(0,0,new_line)]})

        return group_ids, new_ids, existing_ids

share_wizard_portal()