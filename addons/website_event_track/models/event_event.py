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
    website_exhibitor = fields.Boolean(
        string='Exhibitors on Website', compute='_compute_website_menu_data',
        readonly=False, store=True)
    website_lobby = fields.Boolean(
        string="Lobby on Website", compute='_compute_website_menu_data',
        readonly=False, store=True
    )

    @api.depends('website_menu')
    def _compute_website_menu_data(self):
        for event_type in self:
            if not event_type.website_menu:
                event_type.website_track = False
                event_type.website_track_proposal = False
                event_type.website_exhibitor = False
                event_type.website_lobby = False


class Event(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    track_count = fields.Integer('Track Count', compute='_compute_track_count')
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    sponsor_count = fields.Integer('Sponsor Count', compute='_compute_sponsor_count')
    exhibitor_ids = fields.One2many('event.exhibitor', 'event_id', 'Exhibitors')
    exhibitor_count = fields.Integer('Exhibitor Count', compute='_compute_exhibitor_count')
    website_track = fields.Boolean(
        'Tracks on Website', compute='_compute_website_track',
        readonly=False, store=True)
    website_track_proposal = fields.Boolean(
        'Proposals on Website', compute='_compute_website_track_proposal',
        readonly=False, store=True)
    website_exhibitor = fields.Boolean(
        'Exhibitors on Website', compute='_compute_website_exhibitor',
        readonly=False, store=True)
    website_lobby = fields.Boolean(
        'Lobby on Website', compute='_compute_website_lobby',
        readonly=False, store=True)
    track_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Event Tracks Menus', domain=[('menu_type', '=', 'track')])
    track_proposal_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Event Proposals Menus', domain=[('menu_type', '=', 'track_proposal')])
    exhibitor_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Exhibitors Menus', domain=[('menu_type', '=', 'exhibitor')])
    lobby_menu_ids = fields.One2many('website.event.menu', 'event_id', string='Lobby Menus', domain=[('menu_type', '=', 'lobby')])
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

    def _compute_exhibitor_count(self):
        data = self.env['event.exhibitor'].read_group([], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.exhibitor_count = result.get(event.id, 0)

    @api.depends('event_type_id', 'website_menu', 'website_track_proposal')
    def _compute_website_track(self):
        """ Explicitly checks that event_type has changed before copying its value
        on the event itself. Changing website_menu trigger should not mess with the
        behavior of event_type. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track = event.event_type_id.website_track
            elif not event.website_menu:
                event.website_track = False
            elif event.website_track_proposal and not event.website_track:
                event.website_track = True

    @api.depends('event_type_id', 'website_track')
    def _compute_website_track_proposal(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track_proposal = event.event_type_id.website_track_proposal
            elif not event.website_track:
                event.website_track_proposal = False

    @api.depends('event_type_id', 'website_exhibitor')
    def _compute_website_exhibitor(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_exhibitor = event.event_type_id.website_exhibitor
            elif not event.website_exhibitor:
                event.website_exhibitor = False

    @api.depends('event_type_id', 'website_lobby')
    def _compute_website_lobby(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_lobby = event.event_type_id.website_lobby
            elif not event.website_lobby:
                event.website_lobby = False

    @api.depends('track_ids.tag_ids', 'track_ids.tag_ids.color')
    def _compute_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = event.track_ids.mapped('tag_ids').filtered(lambda tag: tag.color != 0).ids

    def _update_website_menus(self):
        super(Event, self)._update_website_menus()
        for event in self:
            for menu_type, menu_entries in event._get_track_module_menu_entries().items():
                if event['website_%s' % menu_type] and not event['%s_menu_ids' % menu_type]:
                    for sequence, (name, url) in enumerate(menu_entries):
                        menu = super(Event, event)._create_menu(sequence, name, url, False)
                        event.env['website.event.menu'].create({
                            'menu_id': menu.id,
                            'event_id': event.id,
                            'menu_type': menu_type,
                        })
                elif not event['website_%s' % menu_type]:
                    event['%s_menu_ids' % menu_type].mapped('menu_id').unlink()

    def write(self, values):
        """ Checks menus:
        - that were activated and are not anymore
        - that were deactivated and are now active

        Then calls '_update_website_menus' on matching ones. """

        previous_values = {}
        menu_types = ['track', 'track_proposal', 'exhibitor', 'lobby']
        for menu_type in menu_types:
            previous_values['%s_activated' % menu_type] = self.filtered(lambda event: event['website_%s' % menu_type])
            previous_values['%s_deactivated' % menu_type] = self.filtered(lambda event: not event['website_%s' % menu_type])

        super(Event, self).write(values)

        menus_to_update = self.env['event.event']
        for menu_type in menu_types:
            menus_to_update |= previous_values['%s_activated' % menu_type].filtered(lambda event: not event['website_%s' % menu_type])
            menus_to_update |= previous_values['%s_deactivated' % menu_type].filtered(lambda event: event['website_%s' % menu_type])

        menus_to_update._update_website_menus()

    def _get_track_module_menu_entries(self):
        self.ensure_one()
        return {
            'track': [
                (_('Talks'), '/event/%s/track' % slug(self)),
                (_('Agenda'), '/event/%s/agenda' % slug(self))
            ],
            'track_proposal': [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self))],
            'exhibitor': [(_('Exhibitors'), '/event/%s/exhibitor' % slug(self))],
            'lobby': [(_('Lobby'), '/event/%s/lobby' % slug(self))]
        }

    def toggle_website_track(self, val):
        self.website_track = val

    def toggle_website_track_proposal(self, val):
        self.website_track_proposal = val

    def toggle_website_exhibitor(self, val):
        self.website_exhibitor = val

    def toggle_website_lobby(self, val):
        self.website_lobby = val
