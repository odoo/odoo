# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Event(models.Model):
    _inherit = "event.event"

    @api.depends('event_type_id', 'website_menu')
    def _compute_community_menu(self):
        """ At type onchange: synchronize. At website_menu update: synchronize. """
        for event in self:
            # If we activate website_menu and there is event_type, take event type value, unless exhibitor menu is already activated.
            if event.event_type_id and (event.event_type_id != event._origin.event_type_id) or (
                    event.website_menu and not event.community_menu):
                event.community_menu = event.event_type_id.community_menu
            # If no event type, or if there is event type but exhibitor_menu is already set when setting website_menu, simply take same value as website_menu
            else:
                event.community_menu = event.website_menu

    @api.onchange('website_menu')
    def _onchange_website_menu_community_menu(self):
        """use onchange to make sure that website_track has the correct value
        when the user makes changes inside the form, what we want is that when
        the user activates the website menu the website_track field to be set to
        the value of the template, if the event is not linked
        to a template, the value of website_track will be set to True.
        When the menu is deactivated it should always be false"""
        super(Event, self)._onchange_website_menu()
        for event in self:
            if event.website_menu and event.event_type_id:
                event.community_menu = event.event_type_id.community_menu
            else:
                event.community_menu = event.website_menu

    @api.onchange('event_type_id')
    def _onchange_event_type(self):
        """use onchange to make sure that website_track has the same value
        as in the event type when the user makes changes inside the form"""
        super(Event, self)._onchange_event_type()
        for event in self:
            if event.event_type_id:
                event.community_menu = event.event_type_id.community_menu

    def toggle_website_menu(self, val):
        super(Event, self).toggle_website_menu(val)
        if val:
            if self.event_type_id:
                self.community_menu = self.event_type_id.community_menu
            else:
                self.community_menu = self.website_menu
