# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import slug


class Event(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def _get_menu_entries(self):
        """ Deprecate old method as a new one with more information is used
        starting with website_event_online module. """
        return []

    def _get_menu_entries_online(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules.

        Each menu entry is a tuple containing :
          * name: menu item name
          * url: if set, url to a route (do not use xml_id in that case);
          * xml_id: template linked to the page (do not use url in that case);
          * sequence: specific sequence of menu entry to be set on the menu;
          * menu_type: type of menu entry (used in inheriting modules to ease
            menu management; not used in this module in 13.3 due to technical
            limitations);
        """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro', 1, False),
            (_('Location'), False, 'website_event.template_location', 50, False),
            (_('Register'), '/event/%s/register' % slug(self), False, 100, False),
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        """ Synchronize event configuration and its menu entries for frontend. """
        super(Event, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.website_menu and (not menus_update_by_field or event in menus_update_by_field.get('website_menu')):
                for name, url, xml_id, menu_sequence, menu_type in event._get_menu_entries_online():
                    event._create_menu(menu_sequence, name, url, xml_id, menu_type=menu_type)
