# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.addons.resource.models.utils import float_to_time
from odoo.tools import is_html_empty
from odoo.tools.translate import html_translate


class EventSponsor(models.Model):
    _name = 'event.sponsor'
    _description = 'Event Sponsor'
    _order = "sequence, sponsor_type_id"
    # _order = 'sponsor_type_id, sequence' TDE FIXME
    _rec_name = 'name'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'website.published.mixin',
        'website.searchable.mixin',
        'chat.room.mixin'
    ]

    def _default_sponsor_type_id(self):
        return self.env['event.sponsor.type'].search([], order="sequence desc", limit=1).id

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one(
        'event.sponsor.type', 'Sponsorship Level',
        default=lambda self: self._default_sponsor_type_id(), required=True, auto_join=True)
    url = fields.Char('Sponsor Website', compute='_compute_url', readonly=False, store=True)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean(default=True)
    # description
    subtitle = fields.Char('Slogan')
    exhibitor_type = fields.Selection(
        [('sponsor', 'Footer Logo Only'), ('exhibitor', 'Exhibitor'), ('online', 'Online Exhibitor')],
        string="Sponsor Type", default="sponsor")
    website_description = fields.Html(
        'Description', compute='_compute_website_description',
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=True, translate=html_translate,
        readonly=False, store=True)
    # contact information
    partner_id = fields.Many2one('res.partner', 'Partner', required=True, auto_join=True)
    partner_name = fields.Char('Name', related='partner_id.name')
    partner_email = fields.Char('Email', related='partner_id.email')
    partner_phone = fields.Char('Phone', related='partner_id.phone')
    partner_mobile = fields.Char('Mobile', related='partner_id.mobile')
    name = fields.Char('Sponsor Name', compute='_compute_name', readonly=False, store=True)
    email = fields.Char('Sponsor Email', compute='_compute_email', readonly=False, store=True)
    phone = fields.Char('Sponsor Phone', compute='_compute_phone', readonly=False, store=True)
    mobile = fields.Char('Sponsor Mobile', compute='_compute_mobile', readonly=False, store=True)
    # image
    image_512 = fields.Image(
        string="Logo", max_width=512, max_height=512,
        compute='_compute_image_512', readonly=False, store=True)
    image_256 = fields.Image("Image 256", related="image_512", max_width=256, max_height=256, store=False)
    image_128 = fields.Image("Image 128", related="image_512", max_width=128, max_height=128, store=False)
    website_image_url = fields.Char(
        string='Image URL',
        compute='_compute_website_image_url', compute_sudo=True, store=False)
    # live mode
    hour_from = fields.Float('Opening hour', default=8.0)
    hour_to = fields.Float('End hour', default=18.0)
    event_date_tz = fields.Selection(string='Timezone', related='event_id.date_tz', readonly=True)
    is_in_opening_hours = fields.Boolean(
        'Within opening hours', compute='_compute_is_in_opening_hours')
    # chat room
    chat_room_id = fields.Many2one(readonly=False)
    room_name = fields.Char(readonly=False)
    # country information (related to ease frontend templates)
    country_id = fields.Many2one(
        'res.country', string='Country',
        related='partner_id.country_id', readonly=True)
    country_flag_url = fields.Char(
        string='Country Flag',
        compute='_compute_country_flag_url', compute_sudo=True)

    @api.depends('partner_id')
    def _compute_url(self):
        for sponsor in self:
            if sponsor.partner_id.website or not sponsor.url:
                sponsor.url = sponsor.partner_id.website

    @api.depends('partner_id')
    def _compute_name(self):
        self._synchronize_with_partner('name')

    @api.depends('partner_id')
    def _compute_email(self):
        self._synchronize_with_partner('email')

    @api.depends('partner_id')
    def _compute_phone(self):
        self._synchronize_with_partner('phone')

    @api.depends('partner_id')
    def _compute_mobile(self):
        self._synchronize_with_partner('mobile')

    @api.depends('partner_id')
    def _compute_image_512(self):
        self._synchronize_with_partner('image_512')

    @api.depends('image_512', 'partner_id.image_256')
    def _compute_website_image_url(self):
        for sponsor in self:
            if sponsor.image_512:
                # image_512 is stored, image_256 is derived from it dynamically
                sponsor.website_image_url = self.env['website'].image_url(sponsor, 'image_256', size=256)
            elif sponsor.partner_id.image_256:
                sponsor.website_image_url = self.env['website'].image_url(sponsor.partner_id, 'image_256', size=256)
            else:
                sponsor.website_image_url = '/website_event_exhibitor/static/src/img/event_sponsor_default.svg'

    def _synchronize_with_partner(self, fname):
        """ Synchronize with partner if not set. Setting a value does not write
        on partner as this may be event-specific information. """
        for sponsor in self:
            if not sponsor[fname]:
                sponsor[fname] = sponsor.partner_id[fname]

    @api.onchange('exhibitor_type')
    def _onchange_exhibitor_type(self):
        """ Keep an explicit onchange to allow configuration of room names, even
        if this field is normally a related on chat_room_id.name. It is not a real
        computed field, an onchange used in form view is sufficient. """
        for sponsor in self:
            if sponsor.exhibitor_type == 'online' and not sponsor.room_name:
                if sponsor.name:
                    room_name = "odoo-exhibitor-%s" % sponsor.name
                else:
                    room_name = self.env['chat.room']._default_name(objname='exhibitor')
                sponsor.room_name = self._jitsi_sanitize_name(room_name)
            if sponsor.exhibitor_type == 'online' and not sponsor.room_max_capacity:
                sponsor.room_max_capacity = '8'

    @api.depends('partner_id')
    def _compute_website_description(self):
        for sponsor in self:
            if is_html_empty(sponsor.website_description):
                sponsor.website_description = sponsor.partner_id.website_description

    @api.depends('event_id.is_ongoing', 'hour_from', 'hour_to', 'event_id.date_begin', 'event_id.date_end')
    def _compute_is_in_opening_hours(self):
        """ Opening hours: hour_from and hour_to are given within event TZ or UTC.
        Now() must therefore be computed based on that TZ. """
        for sponsor in self:
            if not sponsor.event_id.is_ongoing:
                sponsor.is_in_opening_hours = False
            elif sponsor.hour_from is False or sponsor.hour_to is False:
                sponsor.is_in_opening_hours = True
            else:
                event_tz = timezone(sponsor.event_id.date_tz)
                # localize now, begin and end datetimes in event tz
                dt_begin = sponsor.event_id.date_begin.astimezone(event_tz)
                dt_end = sponsor.event_id.date_end.astimezone(event_tz)
                now_utc = utc.localize(fields.Datetime.now().replace(microsecond=0))
                now_tz = now_utc.astimezone(event_tz)

                # compute opening hours
                opening_from_tz = event_tz.localize(datetime.combine(now_tz.date(), float_to_time(sponsor.hour_from)))
                opening_to_tz = event_tz.localize(datetime.combine(now_tz.date(), float_to_time(sponsor.hour_to)))
                if sponsor.hour_to == 0:
                    # when closing 'at midnight', we consider it's at midnight the next day
                    opening_to_tz = opening_to_tz + timedelta(days=1)

                opening_from = max([dt_begin, opening_from_tz])
                opening_to = min([dt_end, opening_to_tz])

                sponsor.is_in_opening_hours = opening_from <= now_tz < opening_to

    @api.depends('partner_id.country_id.image_url')
    def _compute_country_flag_url(self):
        for sponsor in self:
            if sponsor.partner_id.country_id:
                sponsor.country_flag_url = sponsor.partner_id.country_id.image_url
            else:
                sponsor.country_flag_url = False

    # ------------------------------------------------------------
    # MIXINS
    # ---------------------------------------------------------

    @api.depends('name', 'event_id.name')
    def _compute_website_url(self):
        super()._compute_website_url()
        for sponsor in self:
            if sponsor.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                sponsor.website_url = f'/event/{self.env["ir.http"]._slug(sponsor.event_id)}/exhibitor/{self.env["ir.http"]._slug(sponsor)}'

    @api.depends('event_id.website_id.domain')
    def _compute_website_absolute_url(self):
        super()._compute_website_absolute_url()

    @api.model
    def _search_get_detail(self, website, order, options):
        event_id = self.env['ir.http']._unslug(options['event'])[1]
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
            'description': {'name': 'website_description', 'type': 'text', 'truncate': True, 'html': True},
        }
        return {
            'model': 'event.sponsor',
            'base_domain': [[('event_id', '=', event_id), ('exhibitor_type', '!=', 'sponsor')]],
            'search_fields': ['name', 'website_description'],
            'fetch_fields': ['name', 'website_url', 'website_description'],
            'mapping': mapping,
            'icon': 'fa-black-tie',
            'order': order,
        }

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if values.get('is_exhibitor') and not values.get('room_name'):
                exhibitor_name = values['name'] if values.get('name') else self.env['res.partner'].browse(values['partner_id']).name
                name = 'odoo-exhibitor-%s' % exhibitor_name or 'sponsor'
                values['room_name'] = name
        return super().create(values_list)

    def write(self, values):
        toupdate = self.env['event.sponsor']
        if values.get('is_exhibitor') and not values.get('chat_room_id') and not values.get('room_name'):
            toupdate = self.filtered(lambda exhibitor: not exhibitor.chat_room_id)
            # go into sequential update in order to create a custom room name for each sponsor
            for exhibitor in toupdate:
                values['room_name'] = 'odoo-exhibitor-%s' % exhibitor.name
                super(EventSponsor, exhibitor).write(values)
        return super(EventSponsor, self - toupdate).write(values)

    # ------------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------

    def get_backend_menu_id(self):
        return self.env.ref('event.event_main_menu').id

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.partner_id:
            self._message_add_suggested_recipient(
                recipients,
                partner=self.partner_id,
                reason=_('Sponsor')
            )
        return recipients

    # ------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------
    def get_base_url(self):
        """As website_id is not defined on this record, we rely on event website_id for base URL."""
        return self.event_id.get_base_url()
