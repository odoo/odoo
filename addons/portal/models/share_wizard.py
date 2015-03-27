# -*- coding: utf-8 -*-

import logging

from openerp import api, fields, models, _

_logger = logging.getLogger(__name__)

SHARED_DOCS_MENU = "Documents"
SHARED_DOCS_CHILD_MENU = "Shared Documents"

class ShareWizardPortal(models.TransientModel):
    """Inherited share wizard to automatically create appropriate
       menus in the selected portal upon sharing with a portal group."""
    _inherit = "share.wizard"

    @api.model
    def _user_type_selection(self):
        selection = super(ShareWizardPortal, self)._user_type_selection()
        selection.extend([('existing',_('Users you already shared with')),
                          ('groups',_('Existing Groups (e.g Portal Groups)'))])
        return selection

    user_ids = fields.Many2many('res.users', 'share_wizard_res_user_rel', 'share_id', 'user_id', string='Existing users', domain=[('share', '=', True)])
    group_ids = fields.Many2many('res.groups', 'share_wizard_res_group_rel', 'share_id', 'group_id', string='Existing groups', domain=[('share', '=', False)])

    @api.model
    def _check_preconditions(self):
        if self.user_type == 'existing':
            self._assert(self.user_ids,
                     _('Please select at least one user to share with'))
        elif self.user_type == 'groups':
            self._assert(self.group_ids,
                     _('Please select at least one group to share with'))
        return super(ShareWizardPortal, self)._check_preconditions()

    def _create_or_get_submenu_named(self, parent_menu_id, menu_name):
        if not parent_menu_id:
            return
        Menus = self.env['ir.ui.menu']
        parent_menu = Menus.browse(parent_menu_id) # No context
        menu_id = None
        max_seq = 10
        for child_menu in parent_menu.child_id:
            max_seq = max(max_seq, child_menu.sequence)
            if child_menu.name == menu_name:
                menu_id = child_menu.id
                break
        if not menu_id:
            # not found, create it
            menu_id = Menus.sudo().create({'name': menu_name,
                                     'parent_id': parent_menu.id,
                                     'sequence': max_seq + 10, # at the bottom
                                    })
        return menu_id

    def _sharing_root_menu_id(self, portal):
        """Create or retrieve root ID of sharing menu in portal menu

           :param portal: browse_record of portal, constructed with a context WITHOUT language
        """
        parent_menu_id = self._create_or_get_submenu_named(portal, SHARED_DOCS_MENU)
        if parent_menu_id:
            child_menu_id = self._create_or_get_submenu_named(parent_menu_id, SHARED_DOCS_CHILD_MENU)
            return child_menu_id

    def _create_shared_data_menu(self, portal):
        """Create sharing menus in portal menu according to share wizard options.

           :param portal: browse_record of portal, constructed with a context WITHOUT language
        """
        root_menu_id = self._sharing_root_menu_id(portal)
        if not root_menu_id:
            # no specific parent menu, cannot create the sharing menu at all.
            return
        # Create the shared action and menu
        action_def = self._shared_action_def()
        action_id = self.env['ir.actions.act_window'].sudo().create(action_def)
        menu_data = {'name': action_def['name'],
                     'sequence': 10,
                     'action': 'ir.actions.act_window,'+str(action_id.id),
                     'parent_id': root_menu_id,
                     'icon': 'STOCK_JUSTIFY_FILL'}
        menu_id =  self.env['ir.ui.menu'].sudo().create(menu_data)
        return menu_id

    @api.one
    def _create_share_users_group(self):
        # Override of super() to handle the possibly selected "existing users"
        # and "existing groups".
        # In both cases, we call super() to create the share group, but when
        # sharing with existing groups, we will later delete it, and copy its
        # access rights and rules to the selected groups.

        super_result = super(ShareWizardPortal,self)._create_share_users_group()
        # For sharing with existing groups, we don't create a share group, instead we'll
        # alter the rules of the groups so they can see the shared data
        if self.group_ids:
            # get the list of portals and the related groups to install their menus.
            ResGroups = self.env['res.groups']
            all_portal_group = ResGroups.sudo().search([('is_portal', '=', True)])

            # populate result lines with the users of each group and
            # setup the menu for portal groups
            for group in self.group_ids:
                if group in all_portal_group:
                    self._create_shared_data_menu(group.id)

                for user in group.users:
                    new_line = {'user_id': user.id,
                                'newly_created': False}
                    self.write({'result_line_ids': [(0,0,new_line)]})

        elif self.user_ids:
            # must take care of existing users, by adding them to the new group, which is super_result[0],
            # and adding the shortcut
            self.user_ids.sudo().write({'groups_id': [(4, super_result[0])]})
            self._setup_action_and_shortcut(self.user_ids, make_home=False)
            # populate the result lines for existing users too
            for user in self.user_ids:
                new_line = { 'user_id': user.id,
                             'newly_created': False}

                self.write({'result_line_ids': [(0,0,new_line)]})
        return super_result

