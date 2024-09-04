# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.addons.event.tools.esc_label_tools import print_event_attendees, setup_printer, layout_96x82, layout_96x134
from odoo.tools import email_normalize, email_normalize_all
from odoo.exceptions import AccessError, ValidationError
_logger = logging.getLogger(__name__)


class EventRegistration(models.Model):
    _name = 'event.registration'
    _description = 'Event Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.model
    def _get_random_barcode(self):
        """Generate a string representation of a pseudo-random 8-byte number for barcode
        generation.

        A decimal serialisation is longer than a hexadecimal one *but* it
        generates a more compact barcode (Code128C rather than Code128A).

        Generate 8 bytes (64 bits) barcodes as 16 bytes barcodes are not
        compatible with all scanners.
         """
        return str(int.from_bytes(os.urandom(8), 'little'))

    # event
    event_id = fields.Many2one(
        'event.event', string='Event', required=True)
    event_ticket_id = fields.Many2one(
        'event.event.ticket', string='Ticket Type', ondelete='restrict')
    active = fields.Boolean(default=True)
    barcode = fields.Char(string='Barcode', default=lambda self: self._get_random_barcode(), readonly=True, copy=False)
    # utm informations
    utm_campaign_id = fields.Many2one('utm.campaign', 'Campaign', index=True, ondelete='set null')
    utm_source_id = fields.Many2one('utm.source', 'Source', index=True, ondelete='set null')
    utm_medium_id = fields.Many2one('utm.medium', 'Medium', index=True, ondelete='set null')
    # attendee
    partner_id = fields.Many2one('res.partner', string='Booked by', tracking=1)
    name = fields.Char(
        string='Attendee Name', index='trigram',
        compute='_compute_name', readonly=False, store=True, tracking=2)
    email = fields.Char(string='Email', compute='_compute_email', readonly=False, store=True, tracking=3)
    phone = fields.Char(string='Phone', compute='_compute_phone', readonly=False, store=True, tracking=4)
    company_name = fields.Char(
        string='Company Name', compute='_compute_company_name', readonly=False, store=True, tracking=5)
    # organization
    date_closed = fields.Datetime(
        string='Attended Date', compute='_compute_date_closed',
        readonly=False, store=True)
    event_begin_date = fields.Datetime(string="Event Start Date", related='event_id.date_begin', readonly=True)
    event_end_date = fields.Datetime(string="Event End Date", related='event_id.date_end', readonly=True)
    event_date_range = fields.Char("Date Range", compute="_compute_date_range")
    event_organizer_id = fields.Many2one(string='Event Organizer', related='event_id.organizer_id', readonly=True)
    event_user_id = fields.Many2one(string='Event Responsible', related='event_id.user_id', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='event_id.company_id',
        store=True, readonly=False)
    state = fields.Selection([
        ('draft', 'Unconfirmed'),
        ('open', 'Registered'),
        ('done', 'Attended'),
        ('cancel', 'Cancelled')],
        string='Status', default='open',
        readonly=True, copy=False, tracking=6,
        help='Unconfirmed: registrations in a pending state waiting for an action (specific case, notably with sale status)\n'
             'Registered: registrations considered taken by a client\n'
             'Attended: registrations for which the attendee attended the event\n'
             'Cancelled: registrations cancelled manually')
    # questions
    registration_answer_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Answers')
    registration_answer_choice_ids = fields.One2many('event.registration.answer', 'registration_id', string='Attendee Selection Answers',
        domain=[('question_type', '=', 'simple_choice')])
    # scheduled mails
    mail_registration_ids = fields.One2many(
        'event.mail.registration', 'registration_id',
        string="Scheduler Emails", readonly=True)
    # properties
    registration_properties = fields.Properties(
        'Properties', definition='event_id.registration_properties_definition', copy=True)

    _sql_constraints = [
        ('barcode_event_uniq', 'unique(barcode)', "Barcode should be unique")
    ]

    @api.constrains('state', 'event_id', 'event_ticket_id')
    def _check_seats_availability(self):
        registrations_confirmed = self.filtered(lambda registration: registration.state in ('open', 'done'))
        registrations_confirmed.event_id._check_seats_availability()
        registrations_confirmed.event_ticket_id._check_seats_availability()

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
                    fnames={'name'},
                ).get('name') or False

    @api.depends('partner_id')
    def _compute_email(self):
        for registration in self:
            if not registration.email and registration.partner_id:
                registration.email = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames={'email'},
                ).get('email') or False

    @api.depends('partner_id')
    def _compute_phone(self):
        for registration in self:
            if not registration.phone and registration.partner_id:
                partner_values = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames={'phone', 'mobile'},
                )
                registration.phone = partner_values.get('phone') or partner_values.get('mobile') or False

    @api.depends('partner_id')
    def _compute_company_name(self):
        for registration in self:
            if not registration.company_name and registration.partner_id:
                registration.company_name = registration._synchronize_partner_values(
                    registration.partner_id,
                    fnames={'company_name'},
                ).get('company_name') or False

    @api.depends('state')
    def _compute_date_closed(self):
        for registration in self:
            if not registration.date_closed:
                if registration.state == 'done':
                    registration.date_closed = self.env.cr.now()
                else:
                    registration.date_closed = False

    @api.depends("event_id", "partner_id")
    def _compute_date_range(self):
        for registration in self:
            registration.event_date_range = registration.event_id._get_date_range_str(registration.partner_id.lang)

    @api.constrains('event_id', 'event_ticket_id')
    def _check_event_ticket(self):
        if any(registration.event_id != registration.event_ticket_id.event_id for registration in self if registration.event_ticket_id):
            raise ValidationError(_('Invalid event / ticket choice'))

    def _synchronize_partner_values(self, partner, fnames=None):
        if fnames is None:
            fnames = {'name', 'email', 'phone', 'mobile'}
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
            self.phone = self._phone_format(fname='phone', country=country) or self.phone

    @api.model
    def register_attendee(self, barcode, event_id):
        attendee = self.search([('barcode', '=', barcode)], limit=1)
        if not attendee:
            return {'error': 'invalid_ticket'}
        res = attendee._get_registration_summary()
        if attendee.state == 'cancel':
            status = 'canceled_registration'
        elif attendee.state == 'draft':
            status = 'unconfirmed_registration'
        elif attendee.event_id.is_finished:
            status = 'not_ongoing_event'
        elif attendee.state != 'done':
            if event_id and attendee.event_id.id != event_id:
                status = 'need_manual_confirmation'
            else:
                attendee.action_set_done()
                status = 'confirmed_registration'
        else:
            status = 'already_registered'
        res.update({'status': status})
        return res

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # format numbers: prefetch side records, then try to format according to country
        all_partner_ids = set(values['partner_id'] for values in vals_list if values.get('partner_id'))
        all_event_ids = set(values['event_id'] for values in vals_list if values.get('event_id'))
        for values in vals_list:
            if not values.get('phone'):
                continue

            related_country = self.env['res.country']
            if values.get('partner_id'):
                related_country = self.env['res.partner'].with_prefetch(all_partner_ids).browse(values['partner_id']).country_id
            if not related_country and values.get('event_id'):
                related_country = self.env['event.event'].with_prefetch(all_event_ids).browse(values['event_id']).country_id
            if not related_country:
                related_country = self.env.company.country_id
            values['phone'] = self._phone_format(number=values['phone'], country=related_country) or values['phone']

        registrations = super(EventRegistration, self).create(vals_list)
        registrations._update_mail_schedulers()
        return registrations

    def write(self, vals):
        confirming = vals.get('state') in {'open', 'done'}
        to_confirm = (self.filtered(lambda registration: registration.state in {'draft', 'cancel'})
                      if confirming else None)
        ret = super(EventRegistration, self).write(vals)
        if confirming:
            to_confirm._update_mail_schedulers()

        return ret

    def _compute_display_name(self):
        """ Custom display_name in case a registration is nott linked to an attendee
        """
        for registration in self:
            registration.display_name = registration.name or f"#{registration.id}"

    def toggle_active(self):
        pre_inactive = self - self.filtered(self._active_name)
        super().toggle_active()
        # Necessary triggers as changing registration states cannot be used as triggers for the
        # Event(Ticket) models constraints.
        if pre_inactive:
            pre_inactive.event_id._check_seats_availability()
            pre_inactive.event_ticket_id._check_seats_availability()

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
            default_res_ids=self.ids,
            default_template_id=template.id if template else False,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
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
        if self.env.context.get("install_mode", False):
            # running the scheduler for demo data can cause an issue where wkhtmltopdf runs during
            # server start and hangs indefinitely, leading to serious crashes
            # we currently avoid this by not running the scheduler, would be best to find the actual
            # reason for this issue and fix it so we can remove this check
            return

        open_registrations = self.filtered(lambda registration: registration.state == 'open')
        if not open_registrations:
            return

        onsubscribe_schedulers = self.env['event.mail'].sudo().search([
            ('event_id', 'in', open_registrations.event_id.ids),
            ('interval_type', '=', 'after_sub'),
        ])
        if not onsubscribe_schedulers:
            return

        # either trigger the cron, either run schedulers immediately (scaling choice)
        async_scheduler = self.env['ir.config_parameter'].sudo().get_param('event.event_mail_async')
        if async_scheduler:
            self.env.ref('event.event_mail_scheduler')._trigger()
        else:
            # we could simply call _create_missing_mail_registrations and let cron do their job
            # but it currently leads to several delays. We therefore call execute until
            # cron triggers are correctly used
            for scheduler in onsubscribe_schedulers:
                try:
                    scheduler.with_context(
                        event_mail_registration_ids=open_registrations.ids
                    ).with_user(SUPERUSER_ID).execute()
                except Exception as e:
                    _logger.exception("Failed to run scheduler %s", scheduler.id)
                    self.env["event.mail"]._warn_template_error(scheduler, e)

    # ------------------------------------------------------------
    # MAILING / GATEWAY
    # ------------------------------------------------------------

    def _message_compute_subject(self):
        if self.name:
            return _(
                "%(event_name)s - Registration for %(attendee_name)s",
                event_name=self.event_id.name,
                attendee_name=self.name,
            )
        return _(
            "%(event_name)s - Registration #%(registration_id)s",
            event_name=self.event_id.name,
            registration_id=self.id,
        )

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        public_users = self.env['res.users'].sudo()
        public_groups = self.env.ref("base.group_public", raise_if_not_found=False)
        if public_groups:
            public_users = public_groups.sudo().with_context(active_test=False).mapped("users")
        try:
            is_public = self.sudo().with_context(active_test=False).partner_id.user_ids in public_users if public_users else False
            if self.partner_id and not is_public:
                self._message_add_suggested_recipient(recipients, partner=self.partner_id, reason=_('Customer'))
            elif self.email:
                self._message_add_suggested_recipient(recipients, email=self.email, reason=_('Customer Email'))
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

    def _get_registration_summary(self):
        self.ensure_one()
        if self.event_id.badge_format in ["96x82", "96x134"] and self.env.get("iot.device") is not None:
            badge_printers = self.env["iot.device"].search([("subtype", "=", "label_printer")])
            iot_printers = badge_printers.mapped(lambda printer: {
                "id": printer.id,
                "name": printer.name,
                "identifier": printer.identifier,
                "iotIdentifier": printer.iot_id.identifier,
                "ip": printer.iot_id.ip,
                "ipUrl": printer.iot_id.ip_url
            })
        else:
            iot_printers = []
        return {
            'id': self.id,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'ticket_name': self.event_ticket_id.name,
            'event_id': self.event_id.id,
            'event_display_name': self.event_id.display_name,
            'registration_answers': self.registration_answer_ids.filtered('value_answer_id').mapped('display_name'),
            'company_name': self.company_name,
            'iot_printers': iot_printers,
            'badge_format': self.event_id.badge_format
        }

    def _get_registration_print_details(self):
        return {
            'name': self.name,
            'ticket_name': self.event_ticket_id.name if self.event_ticket_id else None,
            'ticket_color': self.event_ticket_id.color if self.event_ticket_id else None,
            'ticket_text_color': self.event_ticket_id._get_ticket_printing_color() if self.event_ticket_id else None,
            'registration_answers': self.registration_answer_choice_ids.mapped('display_name'),
            'company_name': self.company_name
        }

    def _generate_esc_label_badges(self, is_small_badge: bool):
        badge_layout = layout_96x82 if is_small_badge else layout_96x134
        command = setup_printer(badge_layout)

        attendees_per_event = self.grouped("event_id").items()
        for (event, attendees) in attendees_per_event:
            attendees_details = attendees.mapped(lambda attendee: attendee._get_registration_print_details())
            command.concat(print_event_attendees(event._get_event_print_details(), attendees_details, badge_layout))

        return command.to_string()
