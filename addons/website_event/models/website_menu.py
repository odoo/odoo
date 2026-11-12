# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def _can_be_edited_by_event_editor(self, parent_menus=None):
        """ Determines if the current user can write these menus without having
        designer rights, only if:

        - The user is an event manager and a restricted editor
        - All impacted menus are in the menu trees of events the user can write on
        - The event menus themselves are not modified
        """
        if not (self.env.user.has_group('event.group_event_manager') and self.env.user.has_group('website.group_website_restricted_editor')):
            return False

        root_menus_sudo = self.sudo().browse()
        for menu in self.sudo() | (parent_menus or self.browse()).sudo():
            while menu.parent_id:
                menu = menu.parent_id
            root_menus_sudo |= menu

        if not root_menus_sudo:
            return False

        events_sudo = self.env['event.event'].sudo().search([('menu_id', 'in', root_menus_sudo.ids)])
        return (
            events_sudo.menu_id == root_menus_sudo           # All menus are part of an event
            and not (self & events_sudo.menu_id)             # The event menus themselves are not modified
            and events_sudo.sudo(False).has_access('write')  # User can write on events without sudo
        )

    def unlink(self):
        """ Override to synchronize event configuration fields with menu deletion. """
        event_updates = {}
        website_event_menus = self.env['website.event.menu'].search([('menu_id', 'in', self.ids)])
        for event_menu in website_event_menus:
            to_update = event_updates.setdefault(event_menu.event_id, list())
            for menu_type, fname in event_menu.event_id._get_menu_type_field_matching().items():
                if event_menu.menu_type == menu_type:
                    to_update.append(fname)

        unlinked_menus = self

        if website_event_menus:
            # Manually remove website_event_menus to call their ``unlink`` method. Otherwise
            # super unlinks at db level and skip model-specific behavior.
            # Since website.event.menu unlink removes:
            # - the related ir.ui.view records
            # - which cascade deletes the website.page records
            # - which cascade deletes the website.menu records
            # -> we only call super unlink on the remaining website.menu records
            cascaded_menus = website_event_menus.view_id.page_ids.menu_ids
            unlinked_menus = self - cascaded_menus
            website_event_menus.unlink()

        res = super(WebsiteMenu, unlinked_menus).unlink()

        # update events
        for event, to_update in event_updates.items():
            if to_update:
                event.write(dict((fname, False) for fname in to_update))

        return res

    @api.model
    def save(self, website_id, data):
        """
        Method context:

        This method takes a data argument that follows the following format:
         [
           { 'id': 4, url: '/mypage' },
           { 'id': 'menu_xxx_...', url: '/anotherpage' }
         ]

         The new menu entries are identified by their ID being a string and not an integer value.
         Note that when going through super() call, those id entries are replaced by their created
         menu ID (integer), so we need to identify new menu entries before calling super.

         Override purpose:

         All sub-menus of an event are children of a 'main' website.menu, linking to the event main page.

         We abuse that information to determine if the added menu is part of an event or not:
         If we find a website.event.menu item that has the same parent as the menu we just created
         -> it means that we just created a menu inside an event.

         Once we have identified that, we force its URL to be part of the event pages, and we create
         a matching website.event.menu record for it. """

        # Restricted editors bypass check
        if not self.env.su:
            to_save_menu_ids = {menu['id'] for menu in data['data'] if isinstance(menu['id'], int)}
            to_delete_menu_ids = set(data.get('to_delete') or [])
            modified_menu_ids = to_save_menu_ids | to_delete_menu_ids

            # All new or modified menus must have a parent otherwise they are not part of an event
            WebsiteMenuSudo = self.sudo()
            parent_menu_ids = {menu.get('parent_id') for menu in data['data'] if 'parent_id' in menu or menu['id'] not in modified_menu_ids}
            if all(parent_menu_ids) and WebsiteMenuSudo.browse(modified_menu_ids)._can_be_edited_by_event_editor(
                parent_menus=WebsiteMenuSudo.browse([menu_id for menu_id in parent_menu_ids if isinstance(menu_id, int)]),
            ):
                return WebsiteMenuSudo.save(website_id, data)

        old_menu_ids = [menu['id'] for menu in data['data'] if isinstance(menu['id'], int)]
        has_new_menus = any(isinstance(menu['id'], str) for menu in data['data'])
        res = super().save(website_id, data)

        if not has_new_menus:
            return res

        menus_by_parent_id = {}
        for menu in data['data']:
            if not menu.get('parent_id'):
                continue
            if not menus_by_parent_id.get(menu['parent_id']):
                menus_by_parent_id[menu['parent_id']] = []

            menus_by_parent_id[menu['parent_id']].append(menu)

        for parent_id, menus in menus_by_parent_id.items():
            new_menus = filter(lambda menu: menu['id'] not in old_menu_ids, menus)
            if not new_menus:
                continue

            parent = self.env['website.menu'].browse(parent_id)
            while parent.parent_id:  # get the top-most parent to handle sub-menus
                parent = parent.parent_id

            if parent_event_menu := self.env['website.event.menu'].search([
                ('menu_id.parent_id', '=', parent.id)
            ], limit=1):
                event_url = parent_event_menu.event_id.website_url.rstrip('/')
                event_menu_values = []
                for new_menu in new_menus:
                    menu_record = self.env['website.menu'].browse(new_menu['id'])
                    menu_record_url = menu_record.url.lstrip("/")
                    if not menu_record_url or menu_record_url == '#':
                        # prevent blank URLs, use 't' prefix to avoid slug syntax
                        menu_record_url = f"t{int(datetime.now().timestamp())}"

                    menu_record.write({
                        'url': f'{event_url}/page/{menu_record_url}'
                    })
                    event_menu_values.append({
                        'menu_id': menu_record.id,
                        'event_id': parent_event_menu.event_id.id,
                        'menu_type': 'other',
                    })

                # if the current user can create website.menu, then he should be able to
                # create website.event.menu (e.g: website designer group)
                self.env['website.event.menu'].sudo().create(event_menu_values)

        return res
