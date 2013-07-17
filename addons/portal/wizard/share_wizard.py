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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

UID_ROOT = 1
SHARED_DOCS_MENU = "Documents"
SHARED_DOCS_CHILD_MENU = "Shared Documents"

class share_wizard_portal(osv.TransientModel):
    """Inherited share wizard to automatically create appropriate
       menus in the selected portal upon sharing with a portal group."""
    _inherit = "share.wizard"

    def _user_type_selection(self, cr, uid, context=None):
        selection = super(share_wizard_portal, self)._user_type_selection(cr, uid, context=context)
        selection.extend([('existing',_('Users you already shared with')),
                          ('groups',_('Existing Groups (e.g Portal Groups)'))])
        return selection

    _columns = {
        'user_ids': fields.many2many('res.users', 'share_wizard_res_user_rel', 'share_id', 'user_id', 'Existing users', domain=[('share', '=', True)]),
        'group_ids': fields.many2many('res.groups', 'share_wizard_res_group_rel', 'share_id', 'group_id', 'Existing groups', domain=[('share', '=', False)]),
    }

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

    def _create_share_users_group(self, cr, uid, wizard_data, context=None):
        # Override of super() to handle the possibly selected "existing users"
        # and "existing groups".
        # In both cases, we call super() to create the share group, but when
        # sharing with existing groups, we will later delete it, and copy its
        # access rights and rules to the selected groups.
        super_result = super(share_wizard_portal,self)._create_share_users_group(cr, uid, wizard_data, context=context)

        # For sharing with existing groups, we don't create a share group, instead we'll
        # alter the rules of the groups so they can see the shared data
        if wizard_data.group_ids:
            # get the list of portals and the related groups to install their menus.
            res_groups = self.pool.get('res.groups')
            all_portal_group_ids = res_groups.search(cr, UID_ROOT, [('is_portal', '=', True)])

            # populate result lines with the users of each group and
            # setup the menu for portal groups
            for group in wizard_data.group_ids:
                if group.id in all_portal_group_ids:
                    self._create_shared_data_menu(cr, uid, wizard_data, group.id, context=context)

                for user in group.users:
                    new_line = {'user_id': user.id,
                                'newly_created': False}
                    wizard_data.write({'result_line_ids': [(0,0,new_line)]})

        elif wizard_data.user_ids:
            # must take care of existing users, by adding them to the new group, which is super_result[0],
            # and adding the shortcut
            selected_user_ids = [x.id for x in wizard_data.user_ids]
            self.pool.get('res.users').write(cr, UID_ROOT, selected_user_ids, {'groups_id': [(4, super_result[0])]})
            self._setup_action_and_shortcut(cr, uid, wizard_data, selected_user_ids, make_home=False, context=context)
            # populate the result lines for existing users too
            for user in wizard_data.user_ids:
                new_line = { 'user_id': user.id,
                             'newly_created': False}
                wizard_data.write({'result_line_ids': [(0,0,new_line)]})

        return super_result

    def copy_share_group_access_and_delete(self, cr, wizard_data, share_group_id, context=None):
        # In the case of sharing with existing groups, the strategy is to copy
        # access rights and rules from the share group, so that we can
        if not wizard_data.group_ids: return
        Groups = self.pool.get('res.groups')
        Rules = self.pool.get('ir.rule')
        Rights = self.pool.get('ir.model.access')
        share_group = Groups.browse(cr, UID_ROOT, share_group_id)
        share_rule_ids = [r.id for r in share_group.rule_groups]
        for target_group in wizard_data.group_ids:
            # Link the rules to the group. This is appropriate because as of
            # v6.1, the algorithm for combining them will OR the rules, hence
            # extending the visible data.
            Rules.write(cr, UID_ROOT, share_rule_ids, {'groups': [(4,target_group.id)]})
            _logger.debug("Linked sharing rules from temporary sharing group to group %s", target_group)

            # Copy the access rights. This is appropriate too because
            # groups have the UNION of all permissions granted by their
            # access right lines.
            for access_line in share_group.model_access:
                Rights.copy(cr, UID_ROOT, access_line.id, default={'group_id': target_group.id})
            _logger.debug("Copied access rights from temporary sharing group to group %s", target_group)

        # finally, delete it after removing its users
        Groups.write(cr, UID_ROOT, [share_group_id], {'users': [(6,0,[])]})
        Groups.unlink(cr, UID_ROOT, [share_group_id])
        _logger.debug("Deleted temporary sharing group %s", share_group_id)

    def _finish_result_lines(self, cr, uid, wizard_data, share_group_id, context=None):
        super(share_wizard_portal,self)._finish_result_lines(cr, uid, wizard_data, share_group_id, context=context)
        self.copy_share_group_access_and_delete(cr, wizard_data, share_group_id, context=context)

share_wizard_portal()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
