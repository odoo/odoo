# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.mail import is_html_empty


class EventTrackSpeaker(models.Model):
    """ Speaker of a track. All speakers of a track are equal, their sequence
    is only their display order.

    Values default from the contact but can be overridden for this talk, and
    stay readable on the website without giving public access to res.partner.
    """
    _name = 'event.track.speaker'
    _description = 'Event Track Speaker'
    _order = 'sequence, id'

    track_id = fields.Many2one('event.track', string='Track', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    partner_id = fields.Many2one('res.partner', string='Contact', index='btree_not_null')
    # details are copied as the contact would only fill the empty ones; the
    # name is not required as a track may only know the email of its speaker
    name = fields.Char(
        string='Name', compute='_compute_name',
        readonly=False, store=True, precompute=True, copy=True)
    email = fields.Char(
        string='Email', compute='_compute_email',
        readonly=False, store=True, precompute=True, copy=True)
    phone = fields.Char(
        string='Phone', compute='_compute_phone',
        readonly=False, store=True, precompute=True, copy=True)
    function = fields.Char(
        string='Job Position', compute='_compute_function',
        readonly=False, store=True, precompute=True, copy=True)
    company_name = fields.Char(
        string='Company Name', compute='_compute_company_name',
        readonly=False, store=True, precompute=True, copy=True)
    biography = fields.Html(
        string='Biography', compute='_compute_biography',
        readonly=False, store=True, precompute=True, copy=True, sanitize_attributes=False)
    image = fields.Image(
        string='Photo', compute='_compute_image',
        readonly=False, store=True, precompute=True, copy=True,
        max_width=256, max_height=256)
    tag_line = fields.Char(string='Tag Line', compute='_compute_tag_line')

    @api.depends('name', 'email')
    def _compute_display_name(self):
        # a track may only know the email of a speaker
        for speaker in self:
            speaker.display_name = speaker.name or speaker.email or ''

    # the contact only fills the empty values: the ones set for the talk are
    # kept when the contact changes. One compute per field, as giving one of
    # the fields of a shared compute at create leaves the others empty.

    @api.depends('partner_id')
    def _compute_name(self):
        for speaker in self:
            speaker.name = speaker.name or speaker.partner_id.name

    @api.depends('partner_id')
    def _compute_email(self):
        for speaker in self:
            speaker.email = speaker.email or speaker.partner_id.email

    @api.depends('partner_id')
    def _compute_phone(self):
        for speaker in self:
            speaker.phone = speaker.phone or speaker.partner_id.phone

    @api.depends('partner_id')
    def _compute_function(self):
        for speaker in self:
            speaker.function = speaker.function or speaker.partner_id.function

    @api.depends('partner_id')
    def _compute_company_name(self):
        for speaker in self:
            if speaker.partner_id.is_company:
                speaker.company_name = speaker.partner_id.name
            else:
                speaker.company_name = speaker.company_name or speaker.partner_id.parent_id.name

    @api.depends('partner_id')
    def _compute_biography(self):
        for speaker in self:
            if is_html_empty(speaker.biography) and not is_html_empty(speaker.partner_id.website_description):
                speaker.biography = speaker.partner_id.website_description
            else:
                speaker.biography = speaker.biography

    @api.depends('partner_id')
    def _compute_image(self):
        for speaker in self:
            speaker.image = speaker.image or speaker.partner_id.image_256

    @api.depends('name', 'function', 'company_name')
    def _compute_tag_line(self):
        for speaker in self:
            if not speaker.name:
                speaker.tag_line = False
            elif speaker.function and speaker.company_name:
                speaker.tag_line = self.env._(
                    '%(name)s, %(function)s at %(company)s',
                    name=speaker.name, function=speaker.function, company=speaker.company_name)
            elif speaker.function:
                speaker.tag_line = f'{speaker.name}, {speaker.function}'
            elif speaker.company_name:
                speaker.tag_line = self.env._(
                    '%(name)s from %(company)s', name=speaker.name, company=speaker.company_name)
            else:
                speaker.tag_line = speaker.name
