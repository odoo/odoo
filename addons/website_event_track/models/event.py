# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.website.models.website import slug


class Event(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    show_track_proposal = fields.Boolean('Tracks Proposals', compute='_get_show_menu', inverse='_set_show_menu', store=True)
    show_tracks = fields.Boolean('Show Tracks on Website', compute='_get_show_menu', inverse='_set_show_menu', store=True)
    count_tracks = fields.Integer('Tracks', compute='_count_tracks')
    allowed_track_tag_ids = fields.Many2many('event.track.tag', relation='event_allowed_track_tags_rel', string='Available Track Tags')
    tracks_tag_ids = fields.Many2many('event.track.tag', relation='event_track_tags_rel', string='Track Tags', compute='_get_tracks_tag_ids', store=True)
    count_sponsor = fields.Integer('# Sponsors', compute='_count_sponsor')

    @api.multi
    def _get_new_menu_pages(self):
        self.ensure_one()
        result = super(Event, self)._get_new_menu_pages()
        if self.show_tracks:
            result.append((_('Talks'), '/event/%s/track' % slug(self)))
            result.append((_('Agenda'), '/event/%s/agenda' % slug(self)))
        if self.show_track_proposal:
            result.append((_('Talk Proposals'), '/event/%s/track_proposal' % slug(self)))
        return result

    @api.multi
    def _set_show_menu(self):
        for event in self:
            # if the number of menu items have changed, then menu items must be regenerated
            if event.menu_id:
                nbr_menu_items = len(event._get_new_menu_pages())
                if nbr_menu_items != len(event.menu_id.child_id):
                    event.menu_id.unlink()
        return super(Event, self)._set_show_menu()

    @api.multi
    def _count_tracks(self):
        track_data = self.env['event.track'].read_group([('state', '!=', 'cancel')], ['event_id', 'state'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in track_data)
        for event in self:
            event.count_tracks = result.get(event.id, 0)

    @api.multi
    @api.depends('track_ids.tag_ids')
    def _get_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = event.track_ids.mapped('tag_ids').ids

    @api.multi
    def _count_sponsor(self):
        for event in self:
            event.count_sponsor = len(event.sponsor_ids)
