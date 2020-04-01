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

    @api.depends('track_ids.tag_ids', 'track_ids.tag_ids.color')
    def _compute_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = event.track_ids.mapped('tag_ids').filtered(lambda tag: tag.color != 0).ids

    def _update_website_menus(self):
        super(Event, self)._update_website_menus()
        for event in self:
            if event.website_track and not event.track_menu_ids:
                for sequence, (name, url, xml_id, menu_type) in enumerate(event._get_track_menu_entries()):
                    menu = super(Event, event)._create_menu(sequence, name, url, xml_id)
                    event.env['website.event.menu'].create({
                        'menu_id': menu.id,
                        'event_id': event.id,
                        'menu_type': menu_type,
                    })
            elif not event.website_track:
                event.track_menu_ids.mapped('menu_id').unlink()
            if event.website_track_proposal and not event.track_proposal_menu_ids:
                for sequence, (name, url, xml_id, menu_type) in enumerate(event._get_track_proposal_menu_entries()):
                    menu = super(Event, event)._create_menu(sequence, name, url, xml_id)
                    event.env['website.event.menu'].create({
                        'menu_id': menu.id,
                        'event_id': event.id,
                        'menu_type': menu_type,
                    })
            elif not event.website_track_proposal:
                event.track_proposal_menu_ids.mapped('menu_id').unlink()

    def write(self, values):
        track_activated = self.filtered(lambda event: event.website_track)
        track_deactivated = self.filtered(lambda event: not event.website_track)
        track_proposal_activated = self.filtered(lambda event: event.website_track_proposal)
        track_proposal_deactivated = self.filtered(lambda event: not event.website_track_proposal)
        super(Event, self).write(values)
        to_deactivate = track_activated.filtered(lambda event: not event.website_track)
        to_activate = track_deactivated.filtered(lambda event: event.website_track)
        track_proposal_to_deactivate = track_proposal_activated.filtered(lambda event: not event.website_track_proposal)
        track_proposal_to_activate = track_proposal_deactivated.filtered(lambda event: event.website_track_proposal)
        (to_activate | to_deactivate | track_proposal_to_activate | track_proposal_to_deactivate)._update_website_menus()

    def _get_track_menu_entries(self):
        self.ensure_one()
        res = [
            (_('Talks'), '/event/%s/track' % slug(self), False, 'track'),
            (_('Agenda'), '/event/%s/agenda' % slug(self), False, 'track')]
        return res

    def _get_track_proposal_menu_entries(self):
        self.ensure_one()
        res = [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 'track_proposal')]
        return res

    def toggle_website_menu(self, val):
        self.website_menu = val

    def toggle_website_track(self, val):
        self.website_track = val

    def toggle_website_track_proposal(self, val):
        self.website_track_proposal = val
