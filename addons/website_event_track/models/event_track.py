# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from pytz import utc
from random import randint

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv import expression
from odoo.tools.mail import is_html_empty
from odoo.tools.translate import _, html_translate


class Track(models.Model):
    _name = "event.track"
    _description = 'Event Track'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.seo.metadata', 'website.published.mixin']

    @api.model
    def _get_default_stage_id(self):
        return self.env['event.track.stage'].search([], limit=1).id

    # description
    name = fields.Char('Title', required=True, translate=True)
    event_id = fields.Many2one('event.event', 'Event', required=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', related='event_id.company_id')
    tag_ids = fields.Many2many('event.track.tag', string='Tags')
    description = fields.Html(translate=html_translate, sanitize_attributes=False, sanitize_form=False)
    color = fields.Integer('Color')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'),
        ('2', 'High'), ('3', 'Highest')],
        'Priority', required=True, default='1')
    # management
    stage_id = fields.Many2one(
        'event.track.stage', string='Stage', ondelete='restrict',
        index=True, copy=False, default=_get_default_stage_id,
        group_expand='_read_group_stage_ids',
        required=True, tracking=True)
    is_accepted = fields.Boolean('Is Accepted', related='stage_id.is_accepted', readonly=True)
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True, tracking=True,
        help="A track's kanban state indicates special situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the progress of this track\n"
             " * Green indicates the track is ready to be pulled to the next stage")
    # speaker
    partner_id = fields.Many2one('res.partner', 'Speaker')
    partner_name = fields.Char(
        string='Name', compute='_compute_partner_name',
        readonly=False, store=True, tracking=10)
    partner_email = fields.Char(
        string='Email', compute='_compute_partner_email',
        readonly=False, store=True, tracking=20)
    partner_phone = fields.Char(
        string='Phone', compute='_compute_partner_phone',
        readonly=False, store=True, tracking=30)
    partner_biography = fields.Html(
        string='Biography', compute='_compute_partner_biography',
        readonly=False, store=True)
    partner_function = fields.Char(
        'Job Position', related='partner_id.function',
        compute_sudo=True, readonly=True)
    partner_company_name = fields.Char(
        'Company Name', related='partner_id.parent_name',
        compute_sudo=True, readonly=True)
    image = fields.Image(
        string="Speaker Photo", compute="_compute_speaker_image",
        readonly=False, store=True,
        max_width=256, max_height=256)
    location_id = fields.Many2one('event.track.location', 'Location')
    # time information
    date = fields.Datetime('Track Date')
    date_end = fields.Datetime('Track End Date', compute='_compute_end_date', store=True)
    duration = fields.Float('Duration', default=1.5, help="Track duration in hours.")
    is_track_live = fields.Boolean(
        'Is Track Live', compute='_compute_track_time_data',
        help="Track has started and is ongoing")
    is_track_soon = fields.Boolean(
        'Is Track Soon', compute='_compute_track_time_data',
        help="Track begins soon")
    is_track_today = fields.Boolean(
        'Is Track Today', compute='_compute_track_time_data',
        help="Track begins today")
    is_track_upcoming = fields.Boolean(
        'Is Track Upcoming', compute='_compute_track_time_data',
        help="Track is not yet started")
    is_track_done = fields.Boolean(
        'Is Track Done', compute='_compute_track_time_data',
        help="Track is finished")
    track_start_remaining = fields.Integer(
        'Minutes before track starts', compute='_compute_track_time_data',
        help="Remaining time before track starts (seconds)")
    track_start_relative = fields.Integer(
        'Minutes compare to track start', compute='_compute_track_time_data',
        help="Relative time compared to track start (seconds)")
    # frontend description
    website_image = fields.Image(string="Website Image", max_width=1024, max_height=1024)
    website_image_url = fields.Char(
        string='Image URL', compute='_compute_website_image_url',
        compute_sudo=True, store=False)
    # wishlist / visitors management
    event_track_visitor_ids = fields.One2many(
        'event.track.visitor', 'track_id', string="Track Visitors",
        groups="event.group_event_user")
    is_reminder_on = fields.Boolean('Is Reminder On', compute='_compute_is_reminder_on')
    wishlist_visitor_ids = fields.Many2many(
        'website.visitor', string="Visitor Wishlist",
        compute="_compute_wishlist_visitor_ids", compute_sudo=True,
        search="_search_wishlist_visitor_ids",
        groups="event.group_event_user")
    wishlist_visitor_count = fields.Integer(
        string="# Wishlisted",
        compute="_compute_wishlist_visitor_ids", compute_sudo=True,
        groups="event.group_event_user")
    wishlisted_by_default = fields.Boolean(
        string='Always Wishlisted',
        help="""If set, the talk will be starred for each attendee registered to the event. The attendee won't be able to un-star this talk.""")
    # Call to action
    website_cta = fields.Boolean('Magic Button')
    website_cta_title = fields.Char('Button Title')
    website_cta_url = fields.Char('Button Target URL')
    website_cta_delay = fields.Integer('Button appears')
    # time information for CTA
    is_website_cta_live = fields.Boolean(
        'Is CTA Live', compute='_compute_cta_time_data',
        help="CTA button is available")
    website_cta_start_remaining = fields.Integer(
        'Minutes before CTA starts', compute='_compute_cta_time_data',
        help="Remaining time before CTA starts (seconds)")

    @api.depends('name')
    def _compute_website_url(self):
        super(Track, self)._compute_website_url()
        for track in self:
            if track.id:
                track.website_url = '/event/%s/track/%s' % (slug(track.event_id), slug(track))

    # SPEAKER

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for track in self:
            if not track.partner_name or track.partner_id:
                track.partner_name = track.partner_id.name

    @api.depends('partner_id')
    def _compute_partner_email(self):
        for track in self:
            if not track.partner_email or track.partner_id:
                track.partner_email = track.partner_id.email

    @api.depends('partner_id')
    def _compute_partner_phone(self):
        for track in self:
            if not track.partner_phone or track.partner_id:
                track.partner_phone = track.partner_id.phone

    @api.depends('partner_id')
    def _compute_partner_biography(self):
        for track in self:
            if not track.partner_biography:
                track.partner_biography = track.partner_id.website_description
            elif track.partner_id and is_html_empty(track.partner_biography) and \
                not is_html_empty(track.partner_id.website_description):
                track.partner_biography = track.partner_id.website_description

    @api.depends('partner_id')
    def _compute_speaker_image(self):
        for track in self:
            if not track.image:
                track.image = track.partner_id.image_256

    # TIME

    @api.depends('date', 'duration')
    def _compute_end_date(self):
        for track in self:
            if track.date:
                delta = timedelta(minutes=60 * track.duration)
                track.date_end = track.date + delta
            else:
                track.date_end = False


    # FRONTEND DESCRIPTION

    @api.depends('image', 'partner_id.image_256')
    def _compute_website_image_url(self):
        for track in self:
            if track.website_image:
                track.website_image_url = self.env['website'].image_url(track, 'website_image', size=1024)
            else:
                track.website_image_url = '/website_event_track/static/src/img/event_track_default_%d.jpeg' % (track.id % 2)

    # WISHLIST / VISITOR MANAGEMENT

    @api.depends('wishlisted_by_default', 'event_track_visitor_ids.visitor_id',
                 'event_track_visitor_ids.partner_id', 'event_track_visitor_ids.is_wishlisted',
                 'event_track_visitor_ids.is_blacklisted')
    @api.depends_context('uid')
    def _compute_is_reminder_on(self):
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            for track in self:
                track.is_reminder_on = track.wishlisted_by_default
        else:
            if self.env.user._is_public():
                domain = [('visitor_id', '=', current_visitor.id)]
            elif current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]

            event_track_visitors = self.env['event.track.visitor'].sudo().search_read(
                expression.AND([
                    domain,
                    [('track_id', 'in', self.ids)]
                ]), fields=['track_id', 'is_wishlisted', 'is_blacklisted']
            )

            wishlist_map = {
                track_visitor['track_id'][0]: {
                    'is_wishlisted': track_visitor['is_wishlisted'],
                    'is_blacklisted': track_visitor['is_blacklisted']
                } for track_visitor in event_track_visitors
            }
            for track in self:
                if wishlist_map.get(track.id):
                    track.is_reminder_on = wishlist_map.get(track.id)['is_wishlisted'] or (track.wishlisted_by_default and not wishlist_map[track.id]['is_blacklisted'])
                else:
                    track.is_reminder_on = track.wishlisted_by_default

    @api.depends('event_track_visitor_ids.visitor_id', 'event_track_visitor_ids.is_wishlisted')
    def _compute_wishlist_visitor_ids(self):
        results = self.env['event.track.visitor'].read_group(
            [('track_id', 'in', self.ids), ('is_wishlisted', '=', True)],
            ['track_id', 'visitor_id:array_agg'],
            ['track_id']
        )
        visitor_ids_map = {result['track_id'][0]: result['visitor_id'] for result in results}
        for track in self:
            track.wishlist_visitor_ids = visitor_ids_map.get(track.id, [])
            track.wishlist_visitor_count = len(visitor_ids_map.get(track.id, []))

    def _search_wishlist_visitor_ids(self, operator, operand):
        if operator == "not in":
            raise NotImplementedError("Unsupported 'Not In' operation on track wishlist visitors")

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('visitor_id', operator, operand),
            ('is_wishlisted', '=', True)
        ])
        return [('id', 'in', track_visitors.track_id.ids)]

    # TIME

    @api.depends('date', 'date_end')
    def _compute_track_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            if not track.date:
                track.is_track_live = track.is_track_soon = track.is_track_today = track.is_track_upcoming = track.is_track_done = False
                track.track_start_relative = track.track_start_remaining = 0
                continue
            date_begin_utc = utc.localize(track.date, is_dst=False)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_track_live = date_begin_utc <= now_utc < date_end_utc
            track.is_track_soon = (date_begin_utc - now_utc).total_seconds() < 30*60 if date_begin_utc > now_utc else False
            track.is_track_today = date_begin_utc.date() == now_utc.date()
            track.is_track_upcoming = date_begin_utc > now_utc
            track.is_track_done = date_end_utc <= now_utc
            if date_begin_utc >= now_utc:
                track.track_start_relative = int((date_begin_utc - now_utc).total_seconds())
                track.track_start_remaining = track.track_start_relative
            else:
                track.track_start_relative = int((now_utc - date_begin_utc).total_seconds())
                track.track_start_remaining = 0

    @api.depends('date', 'date_end', 'website_cta', 'website_cta_delay')
    def _compute_cta_time_data(self):
        """ Compute start and remaining time for track itself. Do everything in
        UTC as we compute only time deltas here. """
        now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
        for track in self:
            if not track.website_cta:
                track.is_website_cta_live = track.website_cta_start_remaining = False
                continue

            date_begin_utc = utc.localize(track.date, is_dst=False) + timedelta(minutes=track.website_cta_delay or 0)
            date_end_utc = utc.localize(track.date_end, is_dst=False)
            track.is_website_cta_live = date_begin_utc <= now_utc <= date_end_utc
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                track.website_cta_start_remaining = int(td.total_seconds())
            else:
                track.website_cta_start_remaining = 0

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('website_cta_url'):
                values['website_cta_url'] = self.env['res.partner']._clean_website(values['website_cta_url'])

        tracks = super(Track, self).create(vals_list)

        for track in tracks:
            email_values = {} if self.env.user.email else {'email_from': self.env.company.catchall_formatted}
            track.event_id.message_post_with_view(
                'website_event_track.event_track_template_new',
                values={'track': track},
                subject=track.name,
                subtype_id=self.env.ref('website_event_track.mt_event_track').id,
                **email_values,
            )
            track._synchronize_with_stage(track.stage_id)

        return tracks

    def write(self, vals):
        if vals.get('website_cta_url'):
            vals['website_cta_url'] = self.env['res.partner']._clean_website(vals['website_cta_url'])
        if 'stage_id' in vals and 'kanban_state' not in vals:
            vals['kanban_state'] = 'normal'
        if vals.get('stage_id'):
            stage = self.env['event.track.stage'].browse(vals['stage_id'])
            self._synchronize_with_stage(stage)
        res = super(Track, self).write(vals)
        if vals.get('partner_id'):
            self.message_subscribe([vals['partner_id']])
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Always display all stages """
        return stages.search([], order=order)

    def _synchronize_with_stage(self, stage):
        if stage.is_done:
            self.is_published = True
        elif stage.is_cancel:
            self.is_published = False

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _track_template(self, changes):
        res = super(Track, self)._track_template(changes)
        track = self[0]
        if 'stage_id' in changes and track.stage_id.mail_template_id:
            res['stage_id'] = (track.stage_id.mail_template_id, {
                'composition_mode': 'comment',
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return self.env.ref('website_event_track.mt_track_blocked')
        elif 'kanban_state' in init_values and self.kanban_state == 'done':
            return self.env.ref('website_event_track.mt_track_ready')
        return super(Track, self)._track_subtype(init_values)

    def _message_get_suggested_recipients(self):
        recipients = super(Track, self)._message_get_suggested_recipients()
        for track in self:
            if track.partner_email and track.partner_email != track.partner_id.email:
                track._message_add_suggested_recipient(recipients, email=track.partner_email, reason=_('Speaker Email'))
        return recipients

    def _message_post_after_hook(self, message, msg_vals):
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
        return super(Track, self)._message_post_after_hook(message, msg_vals)

    # ------------------------------------------------------------
    # ACTION
    # ------------------------------------------------------------

    def open_track_speakers_list(self):
        return {
            'name': _('Speakers'),
            'domain': [('id', 'in', self.mapped('partner_id').ids)],
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    def get_backend_menu_id(self):
        return self.env.ref('event.event_main_menu').id

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_event_track_visitors(self, force_create=False):
        self.ensure_one()

        force_visitor_create = self.env.user._is_public()
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request(force_create=force_visitor_create)
        if visitor_sudo:
            visitor_sudo._update_visitor_last_visit()

        if self.env.user._is_public():
            domain = [('visitor_id', '=', visitor_sudo.id)]
        elif visitor_sudo:
            domain = [
                '|',
                ('partner_id', '=', self.env.user.partner_id.id),
                ('visitor_id', '=', visitor_sudo.id)
            ]
        else:
            domain = [('partner_id', '=', self.env.user.partner_id.id)]

        track_visitors = self.env['event.track.visitor'].sudo().search(
            expression.AND([domain, [('track_id', 'in', self.ids)]])
        )
        missing = self - track_visitors.track_id
        if missing and force_create:
            track_visitors += self.env['event.track.visitor'].sudo().create([{
                'visitor_id': visitor_sudo.id,
                'partner_id': self.env.user.partner_id.id if not self.env.user._is_public() else False,
                'track_id': track.id,
            } for track in missing])

        return track_visitors

    def _get_track_suggestions(self, restrict_domain=None, limit=None):
        """ Returns the next tracks suggested after going to the current one
        given by self. Tracks always belong to the same event.

        Heuristic is

          * live first;
          * then ordered by start date, finished being sent to the end;
          * wishlisted (manually or by default);
          * tag matching with current track;
          * location matching with current track;
          * finally a random to have an "equivalent wave" randomly given;

        :param restrict_domain: an additional domain to restrict candidates;
        :param limit: number of tracks to return;
        """
        self.ensure_one()

        base_domain = [
            '&',
            ('event_id', '=', self.event_id.id),
            ('id', '!=', self.id),
        ]
        if restrict_domain:
            base_domain = expression.AND([
                base_domain,
                restrict_domain
            ])

        track_candidates = self.search(base_domain, limit=None, order='date asc')
        if not track_candidates:
            return track_candidates

        track_candidates = track_candidates.sorted(
            lambda track:
                (track.is_published,
                 track.track_start_remaining == 0  # First get the tracks that started less than 10 minutes ago ...
                 and track.track_start_relative < (10 * 60)
                 and not track.is_track_done,  # ... AND not finished
                 track.track_start_remaining > 0,  # Then the one that will begin later (the sooner come first)
                 -1 * track.track_start_remaining,
                 track.is_reminder_on,
                 not track.wishlisted_by_default,
                 len(track.tag_ids & self.tag_ids),
                 track.location_id == self.location_id,
                 randint(0, 20),
                ), reverse=True
        )

        return track_candidates[:limit]
