# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug


class event_track_tag(models.Model):
    _name = "event.track.tag"
    _description = 'Track Tag'
    _order = 'name'

    name = fields.Char('Tag', translate=True)
    track_ids = fields.Many2many('event.track', string='Tracks')


class event_track_location(models.Model):
    _name = "event.track.location"
    _description = 'Track Location'

    name = fields.Char('Room')


class event_track(models.Model):
    _name = "event.track"
    _description = 'Event Tracks'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'website.seo.metadata']

    @api.one
    def _compute_website_url(self):
        self.website_url = "/event/%s/track/%s" % (slug(self.event_id), slug(self))

    name = fields.Char('Title', required=True, translate=True)

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    speaker_ids = fields.Many2many('res.partner', string='Speakers')
    tag_ids = fields.Many2many('event.track.tag', string='Tags')
    state = fields.Selection([
        ('draft', 'Proposal'), ('confirmed', 'Confirmed'), ('announced', 'Announced'), ('published', 'Published')],
        'Status', default='draft', required=True, copy=False, track_visibility='onchange')
    description = fields.Html('Track Description', translate=True)
    date = fields.Datetime('Track Date')
    duration = fields.Float('Duration', digits=(16, 2), default=1.5)
    location_id = fields.Many2one('event.track.location', 'Location')
    event_id = fields.Many2one('event.event', 'Event', required=True)
    color = fields.Integer('Color Index')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'),
        ('2', 'High'), ('3', 'Highest')],
        'Priority', required=True, default='1')
    website_published = fields.Boolean('Available in the website', copy=False)
    website_url = fields.Char("Website url", compute='_compute_website_url')
    image = fields.Binary('Image', compute='_compute_image', readonly=True, store=True)

    @api.one
    @api.depends('speaker_ids.image')
    def _compute_image(self):
        if self.speaker_ids:
            self.image = self.speaker_ids[0].image
        else:
            self.image = False

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            # states = self._get_state_list(cr, uid, context=context)
            states = [('draft', 'Proposal'), ('confirmed', 'Confirmed'), ('announced', 'Announced'), ('published', 'Published')]
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
                'state_count': 0,
            } for state_value, state_name in states]
            # Get standard results
            read_group_res = super(event_track, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
            # Update standard results with default results
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                res[0]['state'] = [state_value, state_name]
                result.append(res[0])
            return result
        else:
            return super(event_track, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

    def open_track_speakers_list(self, cr, uid, track_id, context=None):
        track_id = self.browse(cr, uid, track_id, context=context)
        return {
            'name': _('Speakers'),
            'domain': [('id', 'in', [partner.id for partner in track_id.speaker_ids])],
            'view_type': 'form',
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }


class event_event(models.Model):
    _inherit = "event.event"

    @api.one
    def _count_tracks(self):
        self.count_tracks = len(self.track_ids)

    @api.one
    def _count_sponsor(self):
        self.count_sponsor = len(self.sponsor_ids)

    @api.one
    @api.depends('track_ids.tag_ids')
    def _get_tracks_tag_ids(self):
        track_tags = set(tag for track in self.track_ids for tag in track.tag_ids)
        self.tracks_tag_ids = track_tags and list(track_tags) or False

    track_ids = fields.One2many('event.track', 'event_id', 'Tracks', copy=True)
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsorships', copy=True)
    blog_id = fields.Many2one('blog.blog', 'Event Blog')
    show_track_proposal = fields.Boolean('Talks Proposals')
    show_tracks = fields.Boolean('Multiple Tracks')
    show_blog = fields.Boolean('News')
    count_tracks = fields.Integer('# Tracks', compute='_count_tracks')
    allowed_track_tag_ids = fields.Many2many('event.track.tag', relation='event_allowed_track_tags_rel', string='Available Track Tags')
    tracks_tag_ids = fields.Many2many('event.track.tag', relation='event_track_tags_rel', string='Track Tags', compute='_get_tracks_tag_ids', store=True)
    count_sponsor = fields.Integer('# Sponsors', compute='_count_sponsor')

    @api.one
    def _get_new_menu_pages(self):
        result = super(event_event, self)._get_new_menu_pages()[0]  # TDE CHECK api.one -> returns a list with one item ?
        if self.show_tracks:
            result.append((_('Talks'), '/event/%s/track' % slug(self)))
            result.append((_('Agenda'), '/event/%s/agenda' % slug(self)))
        if self.blog_id:
            result.append((_('News'), '/blogpost'+slug(self.blog_ig)))
        if self.show_track_proposal:
            result.append((_('Talk Proposals'), '/event/%s/track_proposal' % slug(self)))
        return result


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
    image_medium = fields.Binary(string='Logo', type='binary', related='partner_id.image_medium', store=True)
