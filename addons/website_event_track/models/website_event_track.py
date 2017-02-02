# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.translate import _, html_translate
from odoo.addons.website.models.website import slug
from odoo.exceptions import AccessError


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
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin','mail.activity.mixin']

    @api.model
    def _get_default_stage_id(self):
        event_id = self.env.context.get('default_event_id')
        if not event_id:
            return False
        return self.stage_find(event_id, [('fold', '=', False)])

    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    speaker_name = fields.Char('Speaker Name')
    speaker_email = fields.Char('Speaker Email')
    speaker_phone = fields.Char('Speaker Phone')
    speaker_biography = fields.Html('Speaker Biography')
    speaker_id = fields.Many2one('res.partner', string='Speaker')
    tag_ids = fields.Many2many('event.track.tag', string='Tags')
    stage_id = fields.Many2one('event.track.stage', string='Stage', track_visibility='onchange', index=True,
                               domain="[('event_ids', '=', event_id)]", copy=False,
                               group_expand='_read_group_stage_ids',
                               default=_get_default_stage_id)
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
    image = fields.Binary('Image', related='speaker_id.image_medium', store=True, attachment=True)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        # retrieve event_id from the context, add them to already fetched columns (ids)
        if 'default_event_id' in self.env.context:
            search_domain = ['|', ('event_ids', '=', self.env.context['default_event_id'])] + search_domain
        # perform search
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.onchange('speaker_id')
    def _onchange_speaker_id(self):
        if self.speaker_id:
            self.speaker_name = self.speaker_id.name
            self.speaker_email = self.speaker_id.email
            self.speaker_phone = self.speaker_id.phone

    @api.model
    def create(self, vals):
        if not vals.get('stage_id'):
            vals['stage_id'] = self.stage_find(vals.get('event_id'), [('fold', '=', False)])
        res = super(Track, self).create(vals)
        res.message_post_with_view(
            'website_event_track.event_track_template_new',
            subject=res.name,
            subtype_id=self.env['ir.model.data'].xmlid_to_res_id('website_event_track.mt_event_track'))
        if res.speaker_id:
            res.message_subscribe(res.speaker_id.ids)
            res.message_post_with_view(
                'website_event_track.event_track_template_proposal_accept',
                subject=res.name,
                partner_ids=res.speaker_id.ids)
        return res

    @api.multi
    def write(self, vals):
        if vals.get('speaker_id'):
            self.message_subscribe([vals['speaker_id']])
        return super(Track, self).write(vals)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Track, self)._compute_website_url()
        for track in self:
            if not isinstance(track.id, models.NewId):
                track.website_url = '/event/%s/track/%s' % (slug(track.event_id), slug(track))

    def stage_find(self, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        section_ids.extend(self.mapped('event_id').ids)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('event_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        return self.env['event.track.stage'].search(search_domain, order=order, limit=1).id

    @api.multi
    def _track_template(self, tracking):
        res = super(Track, self)._track_template(tracking)
        test_track = self[0]
        changes, tracking_value_ids = tracking[test_track.id]
        if 'stage_id' in changes and test_track.stage_id.mail_template_id:
            res['stage_id'] = (test_track.stage_id.mail_template_id, {'composition_mode': 'mass_mail'})
        return res

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Track, self).message_get_suggested_recipients()
        try:
            for speaker in self:
                if speaker.speaker_email != speaker.speaker_id.email:
                    speaker._message_add_suggested_recipient(recipients, email=speaker.speaker_email, reason=_('Speaker Email'))
        except AccessError:     # no read access rights -> ignore suggested recipients
            pass
        return recipients

class TrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Track Stage'
    _order = 'sequence, id'

    def _get_default_event_ids(self):
        default_event_id = self.env.context.get('default_event_id')
        return [default_event_id] if default_event_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(default=1)
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'event.track')],
        help="If set an email will be sent to the customer when the track reaches this step.")
    fold = fields.Boolean(string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    event_ids = fields.Many2many('event.event', 'event_track_stage_rel', 'stage_id', 'event_id', string="Event", default=_get_default_event_ids)
    is_cancel = fields.Boolean(string="Is Cancel", help='To identified the cancel stage')

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
