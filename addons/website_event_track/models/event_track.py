# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _, html_translate
from odoo.addons.website.models.website import slug


class TrackTag(models.Model):
    _name = "event.track.tag"
    _description = 'Track Tag'
    _order = 'name'

    name = fields.Char('Tag')
    track_ids = fields.Many2many('event.track', string='Tracks')
    color = fields.Integer(string='Color Index', default=10)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class TrackLocation(models.Model):
    _name = "event.track.location"
    _description = 'Track Location'

    name = fields.Char('Room')


class Track(models.Model):
    _name = "event.track"
    _description = 'Event Track'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']

    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Proposed by')
    partner_name = fields.Char('Partner Name')
    partner_email = fields.Char('Partner Email')
    partner_phone = fields.Char('Partner Phone')
    partner_biography = fields.Html('Partner Biography')
    speaker_ids = fields.Many2many('res.partner', string='Speakers')
    tag_ids = fields.Many2many('event.track.tag', string='Tags')
    state = fields.Selection([
        ('draft', 'Proposal'), ('confirmed', 'Confirmed'), ('announced', 'Announced'), ('published', 'Published'), ('refused', 'Refused'), ('cancel', 'Cancelled')],
        'Status', default='draft', required=True, copy=False, track_visibility='onchange')
    description = fields.Html('Track Description', translate=html_translate, sanitize_attributes=False)
    date = fields.Datetime('Track Date')
    duration = fields.Float('Duration', default=1.5)
    location_id = fields.Many2one('event.track.location', 'Room')
    event_id = fields.Many2one('event.event', 'Event', required=True)
    color = fields.Integer('Color Index')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'),
        ('2', 'High'), ('3', 'Highest')],
        'Priority', required=True, default='1')
    image = fields.Binary('Image', related='speaker_ids.image_medium', store=True, attachment=True)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Track, self)._compute_website_url()
        for track in self:
            if not isinstance(track.id, models.NewId):
                track.website_url = '/event/%s/track/%s' % (slug(track.event_id), slug(track))

    @api.model
    def create(self, vals):
        res = super(Track, self).create(vals)
        res.message_subscribe(res.speaker_ids.ids)
        res.message_post_with_view(
            'website_event_track.event_track_template_new',
            subject=res.name,
            subtype_id=self.env['ir.model.data'].xmlid_to_res_id('website_event_track.mt_event_track'))
        return res

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'published':
            vals.update({'website_published': True})
        res = super(Track, self).write(vals)
        if vals.get('speaker_ids'):
            self.message_subscribe([speaker['id'] for speaker in self.resolve_2many_commands('speaker_ids', vals['speaker_ids'], ['id'])])
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            states = [('draft', 'Proposal'), ('confirmed', 'Confirmed'), ('announced', 'Announced'), ('published', 'Published'), ('cancel', 'Cancelled')]
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
                'state_count': 0,
            } for state_value, state_name in states]
            # Get standard results
            read_group_res = super(Track, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)
            # Update standard results with default results
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                if state_value == 'cancel':
                    res[0]['__fold'] = True
                res[0]['state'] = [state_value, state_name]
                result.append(res[0])
            return result
        else:
            return super(Track, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)

    @api.multi
    def open_track_speakers_list(self):
        self.ensure_one()
        return {
            'name': _('Speakers'),
            'domain': [('id', 'in', [partner.id for partner in self.speaker_ids])],
            'view_type': 'form',
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }


class SponsorType(models.Model):
    _name = "event.sponsor.type"
    _order = "sequence"

    name = fields.Char('Sponsor Type', required=True, translate=True)
    sequence = fields.Integer('Sequence')


class Sponsor(models.Model):
    _name = "event.sponsor"
    _order = "sequence"

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one('event.sponsor.type', 'Sponsoring Type', required=True)
    partner_id = fields.Many2one('res.partner', 'Sponsor/Customer', required=True)
    url = fields.Char('Sponsor Website')
    sequence = fields.Integer('Sequence', store=True, related='sponsor_type_id.sequence')
    image_medium = fields.Binary(string='Logo', related='partner_id.image_medium', store=True, attachment=True)
