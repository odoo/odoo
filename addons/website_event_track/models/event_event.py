# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug


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
        """ Propagate event_type configuration (only at change); otherwise propagate
        website_menu updated value. Also force True is track_proposal changes. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track = event.event_type_id.website_track
            elif event.website_menu != event._origin.website_menu or not event.website_menu or not event.website_track:
                event.website_track = event.website_menu
            elif event.website_track_proposal and not event.website_track:
                event.website_track = True

    @api.depends('event_type_id', 'website_track')
    def _compute_website_track_proposal(self):
        """ Propagate event_type configuration (only at change); otherwise propagate
        website_track updated value (both together True or False at update). """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track_proposal = event.event_type_id.website_track_proposal
            elif event.website_track != event._origin.website_track or not event.website_track or not event.website_track_proposal:
                event.website_track_proposal = event.website_track

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
        return super(Event, self)._get_menu_update_fields() + ['website_track', 'website_track_proposal']

    def _update_website_menus(self, menus_update_by_field=None):
        super(Event, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if (not menus_update_by_field) or (event in menus_update_by_field.get('website_track')):
                event._update_website_menu_entry('website_track', 'track_menu_ids', '_get_track_menu_entries')
            if (not menus_update_by_field) or (event in menus_update_by_field.get('website_track_proposal')):
                event._update_website_menu_entry('website_track_proposal', 'track_proposal_menu_ids', '_get_track_proposal_menu_entries')

    def _update_website_menu_entry(self, fname_bool, fname_o2m, method_name):
        """ Generic method to create menu entries based on a flag on event. This
        method is a bit obscure, but is due to preparation of adding new menus
        entries and pages for event in a stable version, leading to some constraints
        while developing.

        :param fname_bool: field name (e.g. website_track)
        :param fname_o2m: o2m linking towards website.event.menu matching the
          boolean fields (normally an entry ot website.event.menu with type matching
          the boolean field name)
        :param method_name: method returning menu entries information: url, sequence, ...
        """
        self.ensure_one()
        new_menu = None

        if self[fname_bool] and not self[fname_o2m]:
            # menus not found but boolean True: get menus to create
            for sequence, menu_data in enumerate(getattr(self, method_name)()):
                # some modules have 4 data: name, url, xml_id, menu_type; however we
                # plan to support sequence in future modules, so this hackish code is
                # necessary to avoid crashing. Not nice, but stable target = meh.
                if len(menu_data) == 4:
                    (name, url, xml_id, menu_type) = menu_data
                    menu_sequence = sequence
                elif len(menu_data) == 5:
                    (name, url, xml_id, menu_sequence, menu_type) = menu_data
                new_menu = self._create_menu(menu_sequence, name, url, xml_id, menu_type=menu_type)
        elif not self[fname_bool]:
            # will cascade delete to the website.event.menu
            self[fname_o2m].mapped('menu_id').sudo().unlink()

        return new_menu

    def _create_menu(self, sequence, name, url, xml_id, menu_type=False):
        """ Override menu creation from website_event to link a website.event.menu
        to the newly create menu (either page and url). """
        website_menu = super(Event, self)._create_menu(sequence, name, url, xml_id, menu_type=menu_type)
        if menu_type:
            self.env['website.event.menu'].create({
                'menu_id': website_menu.id,
                'event_id': self.id,
                'menu_type': menu_type,
            })
        return website_menu

    def _get_menu_type_field_matching(self):
        return {'track_proposal': 'website_track_proposal'}

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
        return [
            (_('Talks'), '/event/%s/track' % slug(self), False, 'track'),
            (_('Agenda'), '/event/%s/agenda' % slug(self), False, False)]

    def _get_track_proposal_menu_entries(self):
        """ See website_event_track._get_track_menu_entries() """
        self.ensure_one()
        return [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 'track_proposal')]
