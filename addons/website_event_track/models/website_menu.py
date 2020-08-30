# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def unlink(self):
        """ Override to synchronize event configuration fields with menu deletion.
        This should be cleaned in upcoming versions. """    
        event_updates = {}
        website_event_menus = self.env['website.event.menu'].search([('menu_id', 'in', self.ids)])
        for event_menu in website_event_menus:
            to_update = event_updates.setdefault(event_menu.event_id, list())
            # specifically check for /track in menu URL; to avoid unchecking track field when removing
            # agenda page that has also menu_type='track'
            if event_menu.menu_type == 'track' and '/track' in event_menu.menu_id.url:
                to_update.append('website_track')

        # call super that resumes the unlink of menus entries (including website event menus)
        res = super(WebsiteMenu, self).unlink()

        # update events
        for event, to_update in event_updates.items():
            if to_update:
                event.write(dict((fname, False) for fname in to_update))

        return res
