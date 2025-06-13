# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
import pytz

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.fields import Domain
from odoo.tools import email_normalize, format_date, formataddr
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class EventRegistration(models.Model):
    _name = 'event.registration'
    _description = 'Event Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _mail_defaults_to_email = True

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
        'event.event', string='Event', required=True, tracking=True, index=True)
    is_multi_slots = fields.Boolean(string="Is Event Multi Slots", related="event_id.is_multi_slots")
    event_slot_id = fields.Many2one(
        "event.slot", string="Slot", ondelete='restrict', tracking=True, index="btree_not_null",
        domain="[('event_id', '=', event_id)]")
    event_ticket_id = fields.Many2one(
        'event.event.ticket', string='Ticket Type', ondelete='restrict', tracking=True, index='btree_not_null')
    active = fields.Boolean(default=True)
    barcode = fields.Char(string='Barcode', default=lambda self: self._get_random_barcode(), readonly=True, copy=False)
    # utm informations
    utm_campaign_id = fields.Many2one('utm.campaign', 'Campaign', index=True, ondelete='set null')
    utm_source_id = fields.Many2one('utm.source', 'Source', index=True, ondelete='set null')
    utm_medium_id = fields.Many2one('utm.medium', 'Medium', index=True, ondelete='set null')
    # attendee
    partner_id = fields.Many2one('res.partner', string='Booked by', tracking=1, index='btree_not_null')
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
    event_begin_date = fields.Datetime("Event Start Date", compute="_compute_event_begin_date", search="_search_event_begin_date")
    event_end_date = fields.Datetime("Event End Date", compute="_compute_event_end_date", search="_search_event_end_date")
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

    _barcode_event_uniq = models.Constraint(
        'unique(barcode)',
        'Barcode should be unique',
    )

    @api.constrains('active', 'state', 'event_id', 'event_slot_id', 'event_ticket_id')
    def _check_seats_availability(self):
        tocheck = self.filtered(lambda registration: registration.state in ('open', 'done') and registration.active)
        for event, registrations in tocheck.grouped('event_id').items():
            event._verify_seats_availability([
                (slot, ticket, 0)
                for slot, ticket in self.env['event.registration']._read_group(
                    [('id', 'in', registrations.ids)],
                    ['event_slot_id', 'event_ticket_id']
                )
            ])

    @api.model
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
                    fnames={'phone'},
                )
                registration.phone = partner_values.get('phone') or False

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

    @api.depends("event_id", "event_slot_id", "partner_id")
    def _compute_date_range(self):
        for registration in self:
            registration.event_date_range = registration.event_id._get_date_range_str(
                start_datetime=registration.event_slot_id.start_datetime,
                lang_code=registration.partner_id.lang,
            )

    @api.depends("event_id", "event_slot_id")
    def _compute_event_begin_date(self):
        for registration in self:
            registration.event_begin_date = registration.event_slot_id.start_datetime or registration.event_id.date_begin

    @api.model
    def _search_event_begin_date(self, operator, value):
        return Domain.OR([
            ["&", ("event_slot_id", "!=", False), ("event_slot_id.start_datetime", operator, value)],
            ["&", ("event_slot_id", "=", False), ("event_id.date_begin", operator, value)],
        ])

    @api.depends("event_id", "event_slot_id")
    def _compute_event_end_date(self):
        for registration in self:
            registration.event_end_date = registration.event_slot_id.end_datetime or registration.event_id.date_end

    @api.model
    def _search_event_end_date(self, operator, value):
        return Domain.OR([
            ["&", ("event_slot_id", "!=", False), ("event_slot_id.end_datetime", operator, value)],
            ["&", ("event_slot_id", "=", False), ("event_id.date_end", operator, value)],
        ])

    @api.constrains('event_id', 'event_slot_id')
    def _check_event_slot(self):
        if any(registration.event_id != registration.event_slot_id.event_id for registration in self if registration.event_slot_id):
            raise ValidationError(_('Invalid event / slot choice'))
        if any(not registration.event_slot_id for registration in self if registration.is_multi_slots):
            raise ValidationError(_('Slot choice is mandatory on multi-slots events.'))

    @api.constrains('event_id', 'event_ticket_id')
    def _check_event_ticket(self):
        if any(registration.event_id != registration.event_ticket_id.event_id for registration in self if registration.event_ticket_id):
            raise ValidationError(_('Invalid event / ticket choice'))

    def _synchronize_partner_values(self, partner, fnames=None):
        if fnames is None:
            fnames = {'name', 'email', 'phone'}
        if partner:
            contact_id = partner.address_get().get('contact', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                return dict((fname, contact[fname]) for fname in fnames if contact[fname])
        return {}

    @api.onchange('event_id')
    def _onchange_event(self):
        if self.event_slot_id and self.event_id != self.event_slot_id.event_id:
            self.event_slot_id = False
        if self.event_ticket_id and self.event_id != self.event_ticket_id.event_id:
            self.event_ticket_id = False

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

        registrations = super().create(vals_list)
        registrations._update_mail_schedulers()
        return registrations

    def write(self, vals):
        confirming = vals.get('state') in {'open', 'done'}
        to_confirm = (self.filtered(lambda registration: registration.state in {'draft', 'cancel'})
                      if confirming else None)
        ret = super().write(vals)
        if confirming:
            to_confirm._update_mail_schedulers()

        if vals.get('state') == 'done':
            message = _("Attended on %(attended_date)s", attended_date=format_date(env=self.env, value=fields.Datetime.now(), date_format='short'))
            self._message_log_batch(bodies={registration.id: message for registration in self})

        return ret

    def _compute_display_name(self):
        """ Custom display_name in case a registration is nott linked to an attendee
        """
        for registration in self:
            registration.display_name = registration.name or f"#{registration.id}"

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
            self.env.ref('mail.ir_cron_mail_scheduler_action')._trigger()
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
                    scheduler._warn_error(e)

    # ------------------------------------------------------------
    # MAILING / GATEWAY
    # ------------------------------------------------------------

    @api.model
    def _mail_template_default_values(self):
        return {
            "email_from": "{{ (object.event_id.organizer_id.email_formatted or object.event_id.company_id.email_formatted or user.email_formatted or '') }}",
            "lang": "{{ object.event_id.lang or object.partner_id.lang }}",
            "use_default_to": True,
        }

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

    def _message_add_default_recipients(self):
        # Prioritize registration email over partner_id, which may be shared when a single
        # partner booked multiple seats
        results = super()._message_add_default_recipients()
        for record in self:
            email_to_lst = results[record.id]['email_to_lst']
            if len(email_to_lst) == 1:
                email_normalized = email_normalize(email_to_lst[0])
                if email_normalized and email_normalized == email_normalize(record.email):
                    results[record.id]['email_to_lst'] = [formataddr((record.name or "", email_normalized))]
        return results

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

        is_date_closed_today = False
        if self.date_closed:
            event_tz = pytz.timezone(self.event_id.date_tz)
            now = fields.Datetime.now(pytz.UTC).astimezone(event_tz)
            closed_date = self.date_closed.astimezone(event_tz)
            is_date_closed_today = now.date() == closed_date.date()

        return {
            'id': self.id,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'slot_name': self.event_slot_id.display_name,
            'ticket_name': self.event_ticket_id.name,
            'event_id': self.event_id.id,
            'event_display_name': self.event_id.display_name,
            'registration_answers': self.registration_answer_ids.filtered('value_answer_id').mapped('display_name'),
            'company_name': self.company_name,
            'badge_format': self.event_id.badge_format,
            'date_closed_formatted': format_date(env=self.env, value=self.date_closed, date_format='short') if self.date_closed else False,
            'is_date_closed_today': is_date_closed_today,
        }
