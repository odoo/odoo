# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug


class event_event(models.Model):
    _inherit = "event.event"

    @api.multi
    def _count_tracks(self):
        track_data = self.env['event.track'].read_group([('state', '!=', 'cancel')],
                                                        ['event_id', 'state'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in track_data)
        for event in self:
            event.count_tracks = result.get(event.id, 0)

    @api.one
    def _count_sponsor(self):
        self.count_sponsor = len(self.sponsor_ids)

    @api.one
    @api.depends('track_ids.tag_ids')
    def _get_tracks_tag_ids(self):
        self.tracks_tag_ids = self.track_ids.mapped('tag_ids').ids

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    show_track_proposal = fields.Boolean('Tracks Proposals', compute='_get_show_menu', inverse='_set_show_menu', store=True)
    show_tracks = fields.Boolean('Show Tracks on Website', compute='_get_show_menu', inverse='_set_show_menu', store=True)
    count_tracks = fields.Integer('Tracks', compute='_count_tracks')
    allowed_track_tag_ids = fields.Many2many('event.track.tag', relation='event_allowed_track_tags_rel', string='Available Track Tags')
    tracks_tag_ids = fields.Many2many('event.track.tag', relation='event_track_tags_rel', string='Track Tags', compute='_get_tracks_tag_ids', store=True)
    count_sponsor = fields.Integer('# Sponsors', compute='_count_sponsor')

    @api.one
    def _get_new_menu_pages(self):
        result = super(event_event, self)._get_new_menu_pages()[0]  # TDE CHECK api.one -> returns a list with one item ?
        if self.show_tracks:
            result.append((_('Talks'), '/event/%s/track' % slug(self)))
            result.append((_('Agenda'), '/event/%s/agenda' % slug(self)))
        if self.show_track_proposal:
            result.append((_('Talk Proposals'), '/event/%s/track_proposal' % slug(self)))
        return result

    @api.one
    def _set_show_menu(self):
        # if the number of menu items have changed, then menu items must be regenerated
        if self.menu_id:
            nbr_menu_items = len(self._get_new_menu_pages()[0])
            if nbr_menu_items != len(self.menu_id.child_id):
                self.menu_id.unlink()
        return super(event_event, self)._set_show_menu()[0]


class event_sponsors_type(models.Model):
    _name = "event.sponsor.type"
    _order = "sequence"

    name = fields.Char('Sponsor Type', required=True, translate=True)
    sequence = fields.Integer('Sequence')


class event_sponsors(models.Model):
    _name = "event.sponsor"
    _order = "sequence"

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one('event.sponsor.type', 'Sponsoring Type', required=True)
    partner_id = fields.Many2one('res.partner', 'Sponsor/Customer', required=True)
    url = fields.Char('Sponsor Website')
    sequence = fields.Integer('Sequence', store=True, related='sponsor_type_id.sequence')
    image_medium = fields.Binary(string='Logo', related='partner_id.image_medium', store=True, attachment=True)
