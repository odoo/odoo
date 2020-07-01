# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    menu_location = fields.Boolean(
        string='Location on Website', compute='_compute_menu_location',
        readonly=False, store=True)
    menu_agenda = fields.Boolean(
        string='Agenda on Website', compute='_compute_menu_agenda',
        readonly=False, store=True)
    menu_location_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Location Menu',
        domain=[('menu_type', '=', 'location')])
    menu_agenda_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Agenda Menu',
        domain=[('menu_type', '=', 'agenda')])

    @api.depends('event_type_id', 'website_menu', 'menu_location')
    def _compute_menu_location(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.menu_location = event.event_type_id.menu_location
            elif event.website_menu:
                event.menu_location = True
            elif not event.website_menu or not event.menu_location:
                event.menu_location = False

    @api.depends('event_type_id', 'website_menu', 'menu_agenda')
    def _compute_menu_agenda(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.menu_agenda = event.event_type_id.menu_agenda
            elif event.website_menu:
                event.menu_agenda = True
            elif not event.website_menu or not event.menu_agenda:
                event.menu_agenda = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_menu_location(self, val):
        self.menu_location = val

    def toggle_menu_agenda(self, val):
        self.menu_agenda = val

    def _get_menu_update_fields(self):
        update_fields = super(EventEvent, self)._get_menu_update_fields()
        update_fields += ['menu_location', 'menu_agenda']
        return update_fields

    def _update_website_menus(self, split_to_update=None):
        super(EventEvent, self)._update_website_menus(split_to_update=split_to_update)
        for event in self:
            if not split_to_update or event in split_to_update.get('menu_location'):
                event._update_website_menu_entry('menu_location', 'menu_location_ids', '_get_location_menu_entries')
            if not split_to_update or event in split_to_update.get('menu_agenda'):
                event._update_website_menu_entry('menu_agenda', 'menu_agenda_ids', '_get_agenda_menu_entries')

    def _get_location_menu_entries(self):
        self.ensure_one()
        res = [(_('Location'), False, 'website_event.template_location', 50, 'location', True)]
        return res

    def _get_agenda_menu_entries(self):
        self.ensure_one()
        res = [(_('Agenda'), '/event/%s/agenda' % slug(self), False, 70, 'agenda', False)]
        return res

    # OVERRIDES: LESSEN WEBSITE_EVENT_ONLINE MENUS
    def _get_menu_entries_online(self):
        """ Remove location as those are now managed separately """
        self.ensure_one()
        res = super(EventEvent, self)._get_menu_entries_online()
        return [item for item in res if 'location' not in item[4]]

    # OVERRIDES: LESSEN WEBSITE_EVENT_TRACK MENUS
    def _get_track_menu_entries(self):
        """ Remove agenda as this is now managed separately """
        self.ensure_one()
        return [(_('Talks'), '/event/%s/track' % slug(self), False, 10, 'track', False)]

    def _get_track_proposal_menu_entries(self):
        """ See website_event_track._get_track_menu_entries() """
        self.ensure_one()
        return [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 15, 'track_proposal', False)]
