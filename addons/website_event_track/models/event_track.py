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


class TrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Track Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    mail_template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.track')],
        help="If set an email will be sent to the customer when the track reaches this step.")
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_done = fields.Boolean(string='Accepted Stage')
    is_cancel = fields.Boolean(string='Canceled Stage')


class Track(models.Model):
    _name = "event.track"
    _description = 'Event Track'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.seo.metadata', 'website.published.mixin']
    _mail_mass_mailing = _('Track Speakers')

    @api.model
    def _get_default_stage_id(self):
        return self.env['event.track.stage'].search([], limit=1).id

    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Speaker')
    partner_name = fields.Char('Speaker Name')
    partner_email = fields.Char('Speaker Email')
    partner_phone = fields.Char('Speaker Phone')
    partner_biography = fields.Html('Speaker Biography')
    tag_ids = fields.Many2many('event.track.tag', string='Tags')
    stage_id = fields.Many2one(
        'event.track.stage', string='Stage',
        index=True, copy=False, default=_get_default_stage_id,
        group_expand='_read_group_stage_ids',
        required=True, track_visibility='onchange')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True, track_visibility='onchange',
        help="A track's kanban state indicates special situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the progress of this track\n"
             " * Green indicates the track is ready to be pulled to the next stage")
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
    image = fields.Binary('Image', related='partner_id.image_medium', store=True, attachment=True)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Track, self)._compute_website_url()
        for track in self:
            if not isinstance(track.id, models.NewId):
                track.website_url = '/event/%s/track/%s' % (slug(track.event_id), slug(track))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name
            self.partner_email = self.partner_id.email
            self.partner_phone = self.partner_id.phone
            self.partner_biography = self.partner_id.website_description

    @api.model
    def create(self, vals):
        track = super(Track, self).create(vals)

        track.event_id.message_post_with_view(
            'website_event_track.event_track_template_new',
            values={'track': track},
            subject=track.name,
            subtype_id=self.env.ref('website_event_track.mt_event_track').id,
        )

        return track

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals and 'kanban_state' not in vals:
            vals['kanban_state'] = 'normal'
        res = super(Track, self).write(vals)
        if vals.get('partner_id'):
            self.message_subscribe(vals['partner_id'])
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Always display all stages """
        return stages.search([], order=order)

    @api.multi
    def _track_template(self, tracking):
        res = super(Track, self)._track_template(tracking)
        track = self[0]
        changes, tracking_value_ids = tracking[track.id]
        if 'stage_id' in changes and track.stage_id.mail_template_id:
            res['stage_id'] = (track.stage_id.mail_template_id, {'composition_mode': 'mass_mail'})
        return res

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return 'website_event_track.mt_track_blocked'
        elif 'kanban_state' in init_values and self.kanban_state == 'done':
            return 'website_event_track.mt_track_ready'
        return super(Track, self)._track_subtype(init_values)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Track, self).message_get_suggested_recipients()
        for track in self:
            if track.partner_email != track.partner_id.email:
                track._message_add_suggested_recipient(recipients, email=track.partner_email, reason=_('Speaker Email'))
        return recipients

    def _message_post_after_hook(self, message):
        if self.partner_email and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.partner_email)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('partner_email', '=', new_partner.email),
                    ('stage_id.is_cancel', '=', False),
                ]).write({'partner_id': new_partner.id})
        return super(Track, self)._message_post_after_hook(message)

    @api.multi
    def open_track_speakers_list(self):
        return {
            'name': _('Speakers'),
            'domain': [('id', 'in', self.mapped('partner_id').ids)],
            'view_type': 'form',
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }


class SponsorType(models.Model):
    _name = "event.sponsor.type"
    _description = 'Event Sponsor Type'
    _order = "sequence"

    name = fields.Char('Sponsor Type', required=True, translate=True)
    sequence = fields.Integer('Sequence')


class Sponsor(models.Model):
    _name = "event.sponsor"
    _description = 'Event Sponsor'
    _order = "sequence"

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one('event.sponsor.type', 'Sponsoring Type', required=True)
    partner_id = fields.Many2one('res.partner', 'Sponsor/Customer', required=True)
    url = fields.Char('Sponsor Website')
    sequence = fields.Integer('Sequence', store=True, related='sponsor_type_id.sequence')
    image_medium = fields.Binary(string='Logo', related='partner_id.image_medium', store=True, attachment=True)
