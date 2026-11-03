# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DEFAULT_TRACK_STAGE_XMLIDS = [
    f'website_event_track.event_track_stage{index}' for index in range(6)
]


class EventEvent(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    track_count = fields.Integer('Track Count', compute='_compute_track_count')
    track_stage_ids = fields.Many2many(
        'event.track.stage', 'event_track_stage_event_rel', 'event_id', 'stage_id',
        string='Track Stages', compute='_compute_track_stage_ids',
        readonly=False, store=True)
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
    location_display_background = fields.Image("Location Display Background")
    location_display_upcoming_track_count = fields.Selection(
        selection=[('2', "2"), ('3', "3"), ('4', "4"), ('5', "5")],
        string="Coming Up Sessions",
        default='3',
        required=True,
    )

    def _compute_track_count(self):
        data = self.env['event.track']._read_group([('stage_id.is_cancel', '!=', True)], ['event_id'], ['__count'])
        result = {event.id: count for event, count in data}
        for event in self:
            event.track_count = result.get(event.id, 0)

    @api.depends('event_type_id')
    def _compute_track_stage_ids(self):
        """ Propagate the event_type stages, keeping the stages still used by
        the event tracks. Otherwise give default stages to events without any
        stage. """
        default_stages = None
        for event in self:
            type_stages = event.event_type_id.track_stage_ids
            if type_stages:
                used_stages = event.with_context(active_test=False).track_ids.stage_id
                event.track_stage_ids = type_stages | used_stages
            elif not event.track_stage_ids:
                if default_stages is None:
                    default_stages = self._get_default_track_stages()
                event.track_stage_ids = default_stages

    @api.constrains('track_stage_ids')
    def _check_track_stage_ids(self):
        if not self:
            return
        stage_data = self.env['event.track'].with_context(active_test=False)._read_group(
            [('event_id', 'in', self.ids)], ['event_id', 'stage_id'], ['__count'])
        for event, stage, count in stage_data:
            if stage and stage not in event.track_stage_ids:
                raise ValidationError(self.env._(
                    'The stage "%(stage)s" cannot be removed from the event "%(event)s" '
                    'as %(count)s track(s) are still in this stage. Move them to another stage first.',
                    stage=stage.display_name, event=event.display_name, count=count,
                ))

    @api.depends('event_type_id', 'website_menu')
    def _compute_website_track(self):
        """ Propagate event_type configuration (only at change); otherwise propagate
        website_menu updated value. Also force True is track_proposal changes. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.website_track = event.event_type_id.website_track
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.website_track):
                event.website_track = True
            elif not event.website_menu:
                event.website_track = False

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
    # BUSINESS METHODS
    # ------------------------------------------------------------

    def action_view_track_locations(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('website_event_track.action_event_track_location')
        action.update({
            'name': self.env._("Track Locations"),
            'domain': [('id', 'in', self.track_ids.location_id.ids)],
        })
        return action

    @api.model
    def _get_default_track_stages(self):
        """ Stages given to events whose template defines none. Falls back on
        the first stage when the standard ones were removed, so that tracks
        always get a stage. """
        stages = self.env['event.track.stage']
        for xmlid in DEFAULT_TRACK_STAGE_XMLIDS:
            stages |= self.env.ref(xmlid, raise_if_not_found=False) or stages
        return stages or stages.search([], limit=1)

    def _get_default_track_stage(self):
        """ Stage given to new tracks of the event: the first unfolded one. """
        self.ensure_one()
        return self.track_stage_ids.sorted(lambda stage: (stage.fold, stage.sequence, stage.id))[:1]

    def _has_published_track(self):
        self.ensure_one()
        return bool(self.track_ids.filtered('is_published'))

    def _prepare_jsonld_vals(self):
        vals = super()._prepare_jsonld_vals()
        if not vals:
            return vals
        performers = {
            # sudo only reads is_company to pick the schema type; the displayed
            # name comes from the track's own partner_name, never the partner.
            track.partner_name: 'Organization' if track.partner_id.sudo().is_company else 'Person'
            for track in self.track_ids
            if track.is_published and track.partner_name
        }
        if performers:
            vals['performer'] = [
                {'@type': schema_type, 'name': name}
                for name, schema_type in performers.items()
            ]
        return vals

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_website_track(self, val):
        self.website_track = val

    def toggle_website_track_proposal(self, val):
        self.website_track_proposal = val

    def copy_event_menus(self, old_events):
        super().copy_event_menus(old_events)
        for new_event in self:
            (new_event.track_menu_ids + new_event.track_proposal_menu_ids).menu_id.parent_id = new_event.menu_id

    def _get_menu_update_fields(self):
        return super()._get_menu_update_fields() + ['website_track', 'website_track_proposal']

    def _update_website_menus(self, menus_update_by_field=None):
        super()._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('website_track')):
                event._update_website_menu_entry('website_track', 'track_menu_ids', 'track')
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('website_track_proposal')):
                event._update_website_menu_entry('website_track_proposal', 'track_proposal_menu_ids', 'track_proposal')

    def _get_menu_type_field_matching(self):
        res = super()._get_menu_type_field_matching()
        res['track_proposal'] = 'website_track_proposal'
        return res

    def _get_website_menu_entries(self):
        self.ensure_one()
        return super()._get_website_menu_entries() + [
            (_('Talks'), '#', False, 10, 'track', False),
            (_('Talks'), '/event/%s/track' % self.env['ir.http']._slug(self), False, 10, 'track', 'track'),
            (_('Agenda'), '/event/%s/agenda' % self.env['ir.http']._slug(self), False, 15, 'track', 'track'),
            (_('Propose a talk'), '/event/%s/track_proposal' % self.env['ir.http']._slug(self), False, 20, 'track_proposal', 'track')
        ]
