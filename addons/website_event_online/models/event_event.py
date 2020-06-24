# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv import expression


class Event(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    def _compute_is_participating(self):
        """ Override is_participating to improve heuristic that is now

          * public, no visitor: not participating as we have no information;
          * public and visitor: check visitor is linked to a registration. As
            visitors are merged on the top parent, current visitor check is
            sufficient event for successive visits;
          * logged, no visitor: check partner is linked to a registration. Do
            not check the email as it is not really secure;
          * logged ad visitor: check partner or visitor are linked to a
            registration;
        """
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            self.is_participating = False
        elif self.env.user._is_public():
            participating = self.env['event.registration'].sudo().search([
                ('event_id', 'in', self.ids),
                ('visitor_id', '=', current_visitor.id),
            ]).event_id
            for event in self:
                event.is_participating = event in participating
        else:
            if current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]
            participating = self.env['event.registration'].sudo().search(
                expression.AND([
                    domain,
                    [('event_id', 'in', self.ids)]
                ])
            ).event_id
            for event in self:
                event.is_participating = event in participating

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
            limitations;
          * force_track: if xml_id: activate visitor tracking on that page.
            Otherwise tracking is set on the template rendered by the URL;
        """
        self.ensure_one()
        return [
            (_('Introduction'), False, 'website_event.template_intro', 1, False, False),
            (_('Location'), False, 'website_event.template_location', 50, False, False),
            (_('Register'), '/event/%s/register' % slug(self), False, 100, False, False),
        ]

    def _update_website_menus(self, split_to_update=None):
        """ Synchronize event configuration and its menu entries for frontend. """
        super(Event, self)._update_website_menus(split_to_update=split_to_update)
        for event in self:
            if event.website_menu and (not split_to_update or event in split_to_update.get('website_menu')):
                for name, url, xml_id, menu_sequence, menu_type, force_track in event._get_menu_entries_online():
                    event._create_menu(menu_sequence, name, url, xml_id, menu_type=menu_type, force_track=force_track)
