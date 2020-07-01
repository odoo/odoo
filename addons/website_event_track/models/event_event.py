# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventType(models.Model):
    _inherit = 'event.type'

    website_track = fields.Boolean(
        string='Tracks on Website', compute='_compute_website_menu_data',
        readonly=False, store=True)
    website_track_proposal = fields.Boolean(
        string='Tracks Proposals on Website', compute='_compute_website_menu_data',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_website_menu_data(self):
        for event_type in self:
            if not event_type.website_menu:
                event_type.website_track = False
                event_type.website_track_proposal = False


class Event(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    track_count = fields.Integer('Track Count', compute='_compute_track_count')
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    sponsor_count = fields.Integer('Sponsor Count', compute='_compute_sponsor_count')
    website_track = fields.Boolean(
        'Tracks on Website', compute='_compute_website_track',
        readonly=False, store=True)
    website_track_proposal = fields.Boolean(
        'Proposals on Website', compute='_compute_website_track_proposal',
        readonly=False, store=True)
    track_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Event Tracks Menus', domain=[('menu_type', '=', 'track')])
    track_proposal_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Event Proposals Menus', domain=[('menu_type', '=', 'track_proposal')])
    allowed_track_tag_ids = fields.Many2many('event.track.tag', relation='event_allowed_track_tags_rel', string='Available Track Tags')
    tracks_tag_ids = fields.Many2many(
        'event.track.tag', relation='event_track_tags_rel', string='Track Tags',
        compute='_compute_tracks_tag_ids', store=True)

    def _compute_track_count(self):
        data = self.env['event.track'].read_group([('stage_id.is_cancel', '!=', True)], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.track_count = result.get(event.id, 0)

    def _compute_sponsor_count(self):
        data = self.env['event.sponsor'].read_group([], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.sponsor_count = result.get(event.id, 0)

    @api.depends('event_type_id', 'website_menu', 'website_track_proposal')
    def _compute_website_track(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track = event.event_type_id.website_track
            elif not event.website_menu:
                event.website_track = False
            elif event.website_track_proposal and not event.website_track:
                event.website_track = True

    @api.depends('event_type_id', 'website_menu', 'website_track')
    def _compute_website_track_proposal(self):
        """ Explicitly checks that event_type has changed before copying its value
        on the event itself. Changing website_menu trigger should not mess with the
        behavior of event_type. """
        for event in self:
            if not event.website_track:
                event.website_track_proposal = False
            elif event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track_proposal = event.event_type_id.website_track_proposal
            elif not event.website_menu or not event.website_track_proposal:
                event.website_track_proposal = False

    @api.depends('track_ids.tag_ids', 'track_ids.tag_ids.color')
    def _compute_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = event.track_ids.mapped('tag_ids').filtered(lambda tag: tag.color != 0).ids

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_website_track(self, val):
        self.website_track = val

    def toggle_website_track_proposal(self, val):
        self.website_track_proposal = val

    def _get_menu_update_fields(self):
        update_fields = super(Event, self)._get_menu_update_fields()
        update_fields += ['website_track', 'website_track_proposal']
        return update_fields

    def _update_website_menus(self, split_to_update=None):
        super(Event, self)._update_website_menus(split_to_update=split_to_update)
        for event in self:
            if not split_to_update or event in split_to_update.get('website_track'):
                event._update_website_menu_entry('website_track', 'track_menu_ids', '_get_track_menu_entries')
            if not split_to_update or event in split_to_update.get('website_track_proposal'):
                event._update_website_menu_entry('website_track_proposal', 'track_proposal_menu_ids', '_get_track_proposal_menu_entries')

    def _update_website_menu_entry(self, fname_bool, fname_o2m, method_name):
        self.ensure_one()
        new_menu = None

        if self[fname_bool] and not self[fname_o2m]:
            for sequence, menu_data in enumerate(getattr(self, method_name)()):
                if len(menu_data) == 4:
                    (name, url, xml_id, menu_type) = menu_data
                    menu_sequence, force_track = sequence, False
                elif len(menu_data) == 6:
                    (name, url, xml_id, menu_sequence, menu_type, force_track) = menu_data
                new_menu = self._create_menu(menu_sequence, name, url, xml_id, menu_type=menu_type, force_track=force_track)
        elif not self[fname_bool]:
            self[fname_o2m].mapped('menu_id').unlink()

        return new_menu

    def _create_menu(self, sequence, name, url, xml_id, menu_type=False, force_track=False):
        """ Override menu creation from website_event to link a website.event.menu
        to the newly create menu (either page and url). """
        website_menu = super(Event, self)._create_menu(sequence, name, url, xml_id, menu_type=menu_type, force_track=force_track)
        if menu_type:
            self.env['website.event.menu'].create({
                'menu_id': website_menu.id,
                'event_id': self.id,
                'menu_type': menu_type,
            })
        return website_menu

    def _get_track_menu_entries(self):
        """ Method returning menu entries to display on the website view of the
        event, possibly depending on some options in inheriting modules.

        Each menu entry is a tuple containing :
          * name: menu item name
          * url: if set, url to a route (do not use xml_id in that case);
          * xml_id: template linked to the page (do not use url in that case);
          * menu_type: key linked to the menu, used to categorize the created
            website.event.menu;
        """
        self.ensure_one()
        res = [
            (_('Talks'), '/event/%s/track' % slug(self), False, 'track'),
            (_('Agenda'), '/event/%s/agenda' % slug(self), False, 'track')]
        return res

    def _get_track_proposal_menu_entries(self):
        """ See website_event_track._get_track_menu_entries() """
        self.ensure_one()
        return [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 'track_proposal')]
