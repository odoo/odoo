# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug


class event_track_tag(models.Model):
    _name = "event.track.tag"
    _description = 'Track Tag'
    _order = 'name'

    name = fields.Char('Tag')
    track_ids = fields.Many2many('event.track', string='Tracks')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class event_track_location(models.Model):
    _name = "event.track.location"
    _description = 'Track Location'

    name = fields.Char('Room')


class event_track(models.Model):
    _name = "event.track"
    _description = 'Event Track'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'website.seo.metadata', 'website.published.mixin']

    name = fields.Char('Title', required=True, translate=True)
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
    description = fields.Html('Track Description', translate=True)
    date = fields.Datetime('Track Date')
    duration = fields.Float('Duration', digits=(16, 2), default=1.5)
    location_id = fields.Many2one('event.track.location', 'Room')
    event_id = fields.Many2one('event.event', 'Event', required=True)
    color = fields.Integer('Color Index')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'),
        ('2', 'High'), ('3', 'Highest')],
        'Priority', required=True, default='1')
    image = fields.Binary('Image', compute='_compute_image', store=True, attachment=True)

    @api.one
    @api.depends('speaker_ids.image')
    def _compute_image(self):
        if self.speaker_ids:
            self.image = self.speaker_ids[0].image
        else:
            self.image = False

    @api.model
    def create(self, vals):
        res = super(event_track, self).create(vals)
        res.message_subscribe(res.speaker_ids.ids)
        res.message_post_with_view(
            'website_event_track.event_track_template_new',
            subject=res.name,
            subtype_id=self.env['ir.model.data'].sudo().xmlid_to_res_id('website_event_track.mt_event_track'))
        return res

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'published':
            vals.update({'website_published': True})
        res = super(event_track, self).write(vals)
        if vals.get('speaker_ids'):
            self.message_subscribe([speaker['id'] for speaker in self.resolve_2many_commands('speaker_ids', vals['speaker_ids'], ['id'])])
        return res

    @api.multi
    @api.depends('name')
    def _website_url(self, field_name, arg):
        res = super(event_track, self)._website_url(field_name, arg)
        res.update({(track.id, '/event/%s/track/%s' % (slug(track.event_id), slug(track))) for track in self})
        return res

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            # states = self._get_state_list(cr, uid, context=context)
            states = [('draft', 'Proposal'), ('confirmed', 'Confirmed'), ('announced', 'Announced'), ('published', 'Published'), ('cancel', 'Cancelled')]
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
                if state_value == 'cancel':
                    res[0]['__fold'] = True
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
