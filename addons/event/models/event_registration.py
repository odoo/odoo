# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
import pytz

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools import format_date, email_normalize, email_normalize_all
from odoo.exceptions import AccessError, ValidationError

# phone_validation is not officially in the depends of event, but we would like
# to have the formatting available in event, not in event_sms -> do a conditional
# import just to be sure
try:
    from odoo.addons.phone_validation.tools.phone_validation import phone_format
except ImportError:
    def phone_format(number, country_code, country_phone_code, force_format='INTERNATIONAL', raise_exception=True):
        return number


class EventRegistration(models.Model):
    _name = 'event.registration'
    _description = 'Event Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # event
    event_id = fields.Many2one(
        'event.event', string='Event', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    event_ticket_id = fields.Many2one(
        'event.event.ticket', string='Event Ticket', readonly=True, ondelete='restrict',
        states={'draft': [('readonly', False)]})
    active = fields.Boolean(default=True)
    # utm informations
    utm_campaign_id = fields.Many2one('utm.campaign', 'Campaign',  index=True, ondelete='set null')
    utm_source_id = fields.Many2one('utm.source', 'Source', index=True, ondelete='set null')
    utm_medium_id = fields.Many2one('utm.medium', 'Medium', index=True, ondelete='set null')
    # attendee
    partner_id = fields.Many2one('res.partner', string='Booked by', tracking=1)
    name = fields.Char(
        string='Attendee Name', index='trigram',
        compute='_compute_name', readonly=False, store=True, tracking=10)
    email = fields.Char(string='Email', compute='_compute_email', readonly=False, store=True, tracking=11)
    phone = fields.Char(string='Phone', compute='_compute_phone', readonly=False, store=True, tracking=12)
    mobile = fields.Char(string='Mobile', compute='_compute_mobile', readonly=False, store=True, tracking=13)
    # organization
    date_closed = fields.Datetime(
        string='Attended Date', compute='_compute_date_closed',
        readonly=False, store=True)
    event_begin_date = fields.Datetime(string="Event Start Date", related='event_id.date_begin', readonly=True)
    event_end_date = fields.Datetime(string="Event End Date", related='event_id.date_end', readonly=True)
    event_organizer_id = fields.Many2one(string='Event Organizer', related='event_id.organizer_id', readonly=True)
    event_user_id = fields.Many2one(string='Event Responsible', related='event_id.user_id', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='event_id.company_id',
        store=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed'), ('done', 'Attended')],
        string='Status', default='draft', readonly=True, copy=False, tracking=True)

    def default_get(self, fields):
        ret_vals = super().default_get(fields)
        utm_mixin_fields = ("campaign_id", "medium_id", "source_id")
        utm_fields = ("utm_campaign_id", "utm_medium_id", "utm_source_id")
        if not any(field in utm_fields for field in fields):
            return ret_vals
        utm_mixin_defaults = self.env['utm.mixin'].default_get(utm_mixin_fields)
        for (mixin_field, field) in zip(utm_mixin_fields, utm_fields):
            if field in fields and utm_mixin_defaults.get(mixin_field):
                ret_vals[field] = utm_mixin_defaults[mixin_field]
        return ret_vals

    @api.depends('partner_id')
    def _compute_name(self):
        for registration in self:
            if not registration.name and registration.partner_id:
                registration.name = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames=['name']
                ).get('name') or False

    @api.depends('partner_id')
    def _compute_email(self):
        for registration in self:
            if not registration.email and registration.partner_id:
                registration.email = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames=['email']
                ).get('email') or False

    @api.depends('partner_id')
    def _compute_phone(self):
        for registration in self:
            if not registration.phone and registration.partner_id:
                registration.phone = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames=['phone']
                ).get('phone') or False

    @api.depends('partner_id')
    def _compute_mobile(self):
        for registration in self:
            if not registration.mobile and registration.partner_id:
                registration.mobile = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames=['mobile']
                ).get('mobile') or False

    @api.depends('state')
    def _compute_date_closed(self):
        for registration in self:
            if not registration.date_closed:
                if registration.state == 'done':
                    registration.date_closed = self.env.cr.now()
                else:
                    registration.date_closed = False

    @api.constrains('event_id', 'event_ticket_id')
    def _check_event_ticket(self):
        if any(registration.event_id != registration.event_ticket_id.event_id for registration in self if registration.event_ticket_id):
            raise ValidationError(_('Invalid event / ticket choice'))

    def _synchronize_partner_values(self, partner, fnames=None):
        if fnames is None:
            fnames = ['name', 'email', 'phone', 'mobile']
        if partner:
            contact_id = partner.address_get().get('contact', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                return dict((fname, contact[fname]) for fname in fnames if contact[fname])
        return {}

    @api.onchange('phone', 'event_id', 'partner_id')
    def _onchange_phone_validation(self):
        if self.phone:
            country = self.partner_id.country_id or self.event_id.country_id or self.env.company.country_id
            self.phone = self._phone_format(self.phone, country)

    @api.onchange('mobile', 'event_id', 'partner_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            country = self.partner_id.country_id or self.event_id.country_id or self.env.company.country_id
            self.mobile = self._phone_format(self.mobile, country)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # format numbers: prefetch side records, then try to format according to country
        all_partner_ids = set(values['partner_id'] for values in vals_list if values.get('partner_id'))
        all_event_ids = set(values['event_id'] for values in vals_list if values.get('event_id'))
        for values in vals_list:
            if not values.get('phone') and not values.get('mobile'):
                continue

            related_country = self.env['res.country']
            if values.get('partner_id'):
                related_country = self.env['res.partner'].with_prefetch(all_partner_ids).browse(values['partner_id']).country_id
            if not related_country and values.get('event_id'):
                related_country = self.env['event.event'].with_prefetch(all_event_ids).browse(values['event_id']).country_id
            if not related_country:
                related_country = self.env.company.country_id

            for fname in {'mobile', 'phone'}:
                if values.get(fname):
                    values[fname] = self._phone_format(values[fname], related_country)

        registrations = super(EventRegistration, self).create(vals_list)

        # auto_confirm if possible; if not automatically confirmed, call mail schedulers in case
        # some were created already open
        if registrations._check_auto_confirmation():
            registrations.sudo().action_confirm()
        elif not self.env.context.get('install_mode', False):
            # running the scheduler for demo data can cause an issue where wkhtmltopdf runs during
            # server start and hangs indefinitely, leading to serious crashes
            # we currently avoid this by not running the scheduler, would be best to find the actual
            # reason for this issue and fix it so we can remove this check
            registrations._update_mail_schedulers()
        return registrations

    def write(self, vals):
        confirming = vals.get('state') in {'open', 'done'}
        to_confirm = (self.filtered(lambda registration: registration.state in {'draft', 'cancel'})
                      if confirming else None)
        ret = super(EventRegistration, self).write(vals)
        # As these Event(Ticket) methods are model constraints, it is not necessary to call them
        # explicitly when creating new registrations. However, it is necessary to trigger them here
        # as changes in registration states cannot be used as constraints triggers.
        if confirming:
            to_confirm.event_id._check_seats_availability()
            to_confirm.event_ticket_id._check_seats_availability()

            if not self.env.context.get('install_mode', False):
                # running the scheduler for demo data can cause an issue where wkhtmltopdf runs
                # during server start and hangs indefinitely, leading to serious crashes we
                # currently avoid this by not running the scheduler, would be best to find the
                # actual reason for this issue and fix it so we can remove this check
                to_confirm._update_mail_schedulers()

        return ret

    def name_get(self):
        """ Custom name_get implementation to better differentiate registrations
        linked to a given partner but with different name (one partner buying
        several registrations)

          * name, partner_id has no name -> take name
          * partner_id has name, name void or same -> take partner name
          * both have name: partner + name
        """
        ret_list = []
        for registration in self:
            if registration.partner_id.name:
                if registration.name and registration.name != registration.partner_id.name:
                    name = '%s, %s' % (registration.partner_id.name, registration.name)
                else:
                    name = registration.partner_id.name
            else:
                name = registration.name
            ret_list.append((registration.id, name))
        return ret_list

    def toggle_active(self):
        pre_inactive = self - self.filtered(self._active_name)
        super().toggle_active()
        # Necessary triggers as changing registration states cannot be used as triggers for the
        # Event(Ticket) models constraints.
        if pre_inactive:
            pre_inactive.event_id._check_seats_availability()
            pre_inactive.event_ticket_id._check_seats_availability()

    def _check_auto_confirmation(self):
        """ Checks that all registrations are for `auto-confirm` events. """
        return all(event.auto_confirm for event in self.event_id)

    def _phone_format(self, number, country):
        """ Call phone_validation formatting tool function. Returns original
        number in case formatting cannot be done (no country, wrong info, ...) """
        if not number or not country:
            return number
        new_number = phone_format(
            number,
            country.code,
            country.phone_code,
            force_format='E164',
            raise_exception=False,
        )
        return new_number if new_number else number

    # ------------------------------------------------------------
    # ACTIONS / BUSINESS
    # ------------------------------------------------------------

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_confirm(self):
        self.write({'state': 'open'})

    def action_set_done(self):
        """ Close Registration """
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_send_badge_email(self):
        """ Open a window to compose an email, with the template - 'event_badge'
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('event.event_registration_mail_template_badge', raise_if_not_found=False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='event.registration',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
            name_with_seats_availability=False,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _update_mail_schedulers(self):
        """ Update schedulers to set them as running again, and cron to be called
        as soon as possible. """
        open_registrations = self.filtered(lambda registration: registration.state == 'open')
        if not open_registrations:
            return

        onsubscribe_schedulers = self.env['event.mail'].sudo().search([
            ('event_id', 'in', open_registrations.event_id.ids),
            ('interval_type', '=', 'after_sub')
        ])
        if not onsubscribe_schedulers:
            return

        onsubscribe_schedulers.update({'mail_done': False})
        # we could simply call _create_missing_mail_registrations and let cron do their job
        # but it currently leads to several delays. We therefore call execute until
        # cron triggers are correctly used
        onsubscribe_schedulers.with_user(SUPERUSER_ID).execute()

    # ------------------------------------------------------------
    # MAILING / GATEWAY
    # ------------------------------------------------------------

    def _message_get_suggested_recipients(self):
        recipients = super(EventRegistration, self)._message_get_suggested_recipients()
        public_users = self.env['res.users'].sudo()
        public_groups = self.env.ref("base.group_public", raise_if_not_found=False)
        if public_groups:
            public_users = public_groups.sudo().with_context(active_test=False).mapped("users")
        try:
            for attendee in self:
                is_public = attendee.sudo().with_context(active_test=False).partner_id.user_ids in public_users if public_users else False
                if attendee.partner_id and not is_public:
                    attendee._message_add_suggested_recipient(recipients, partner=attendee.partner_id, reason=_('Customer'))
                elif attendee.email:
                    attendee._message_add_suggested_recipient(recipients, email=attendee.email, reason=_('Customer Email'))
        except AccessError:     # no read access rights -> ignore suggested recipients
            pass
        return recipients

    def _message_get_default_recipients(self):
        # Prioritize registration email over partner_id, which may be shared when a single
        # partner booked multiple seats
        return {r.id:
            {
                'partner_ids': [],
                'email_to': ','.join(email_normalize_all(r.email)) or r.email,
                'email_cc': False,
            } for r in self
        }

    def _message_post_after_hook(self, message, msg_vals):
        if self.email and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            email_normalized = email_normalize(self.email)
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.email or (email_normalized and partner.email_normalized == email_normalized)
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = ('email', 'in', [new_partner[0].email, new_partner[0].email_normalized])
                else:
                    email_domain = ('email', '=', new_partner[0].email)
                self.search([
                    ('partner_id', '=', False), email_domain, ('state', 'not in', ['cancel']),
                ]).write({'partner_id': new_partner[0].id})
        return super(EventRegistration, self)._message_post_after_hook(message, msg_vals)

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def get_date_range_str(self, lang_code=False):
        self.ensure_one()
        today_tz = pytz.utc.localize(fields.Datetime.now()).astimezone(pytz.timezone(self.event_id.date_tz))
        event_date_tz = pytz.utc.localize(self.event_begin_date).astimezone(pytz.timezone(self.event_id.date_tz))
        diff = (event_date_tz.date() - today_tz.date())
        if diff.days <= 0:
            return _('today')
        elif diff.days == 1:
            return _('tomorrow')
        elif (diff.days < 7):
            return _('in %d days') % (diff.days, )
        elif (diff.days < 14):
            return _('next week')
        elif event_date_tz.month == (today_tz + relativedelta(months=+1)).month:
            return _('next month')
        else:
            return _('on %(date)s', date=format_date(self.env, self.event_begin_date, lang_code=lang_code, date_format='medium'))

    def _get_registration_summary(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'ticket_name': self.event_ticket_id.name or _('None'),
            'event_id': self.event_id.id,
            'event_display_name': self.event_id.display_name,
            'company_name': self.event_id.company_id and self.event_id.company_id.name or False,
        }
