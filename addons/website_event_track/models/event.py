# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.website.models.website import slug


class Event(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks')
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    show_track_proposal = fields.Boolean('Tracks Proposals')
    show_tracks = fields.Boolean('Show Tracks on Website')
    count_tracks = fields.Integer('Tracks', compute='_count_tracks')
    allowed_track_tag_ids = fields.Many2many('event.track.tag', relation='event_allowed_track_tags_rel', string='Available Track Tags')
    tracks_tag_ids = fields.Many2many('event.track.tag', relation='event_track_tags_rel', string='Track Tags', compute='_get_tracks_tag_ids', store=True)
    count_sponsor = fields.Integer('# Sponsors', compute='_count_sponsor')
    stage_ids = fields.Many2many('event.track.stage', 'event_track_stage_rel', 'event_id', 'stage_id', string='Event Stages')

    @api.multi
    def _get_new_menu_pages(self):
        self.ensure_one()
        todo = [
            (_('Introduction'), 'website_event.template_intro'),
            (_('Location'), 'website_event.template_location')
        ]
        result = []
        for name, path in todo:
            complete_name = name + ' ' + self.name
            newpath = self.env['website'].new_page(complete_name, path, ispage=False)
            url = "/event/" + slug(self) + "/page/" + newpath
            result.append((name, url))
        result.append((_('Register'), '/event/%s/register' % slug(self)))
        if self.show_tracks:
            result.append((_('Talks'), '/event/%s/track' % slug(self)))
            result.append((_('Agenda'), '/event/%s/agenda' % slug(self)))
        if self.show_track_proposal:
            result.append((_('Talk Proposals'), '/event/%s/track_proposal' % slug(self)))
        return result

    @api.multi
    def root_menu_create(self):
        for event in self:
            root_menu = self.env['website.menu'].create({'name': event.name})
            to_create_menus = event._get_new_menu_pages()
            seq = 0
            for name, url in to_create_menus:
                self.env['website.menu'].create({
                    'name': name,
                    'url': url,
                    'parent_id': root_menu.id,
                    'sequence': seq,
                })
                seq += 1
            event.menu_id = root_menu

    @api.model
    def create(self, vals):
        event = super(Event, self).create(vals)
        if event.menu_id:
            event.menu_id.unlink()
        if not event.menu_id:
            event.root_menu_create()
        return event

    @api.multi
    def write(self, vals):
        res = super(Event, self).write(vals)
        for event in self:
            if event.menu_id:
                nbr_menu_items = len(event._get_new_menu_pages())
                if nbr_menu_items != len(event.menu_id.child_id):
                    event.menu_id.unlink()

            if (not event.menu_id and (self.show_tracks or self.show_track_proposal or not self.show_tracks or not self.show_track_proposal)):
                event.root_menu_create()
        return res

    @api.multi
    def _count_tracks(self):
        track_data = self.env['event.track'].read_group([('stage_id.is_cancel', '=', False)], ['event_id', 'stage_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in track_data)
        for event in self:
            event.count_tracks = result.get(event.id, 0)

    @api.depends('track_ids.tag_ids')
    def _get_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = event.track_ids.mapped('tag_ids').ids

    @api.multi
    def _count_sponsor(self):
        for event in self:
            event.count_sponsor = len(event.sponsor_ids)

    @api.multi
    def action_mail_send_speakers(self):
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        speaker_ids = self.mapped('track_ids.speaker_id').ids
        ctx = dict(
            default_model='event.event',
            default_partner_ids=speaker_ids,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
