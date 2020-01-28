# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.tools import format_datetime
from odoo.exceptions import AccessError, ValidationError

from dateutil.relativedelta import relativedelta


class EventRegistration(models.Model):
    _name = 'event.registration'
    _description = 'Event Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # event
    origin = fields.Char(
        string='Source Document', readonly=True,
        help="Reference of the document that created the registration, for example a sales order")
    event_id = fields.Many2one(
        'event.event', string='Event', required=True,
        readonly=True, states={'draft': [('readonly', False)]})
    # attendee
    partner_id = fields.Many2one(
        'res.partner', string='Contact',
        states={'done': [('readonly', True)]})
    name = fields.Char(string='Attendee Name', index=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    # organization
    date_open = fields.Datetime(string='Registration Date', readonly=True, default=lambda self: fields.Datetime.now())  # weird crash is directly now
    date_closed = fields.Datetime(string='Attended Date', readonly=True)
    event_begin_date = fields.Datetime(string="Event Start Date", related='event_id.date_begin', readonly=True)
    event_end_date = fields.Datetime(string="Event End Date", related='event_id.date_end', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='event_id.company_id',
        store=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Unconfirmed'), ('cancel', 'Cancelled'),
        ('open', 'Confirmed'), ('done', 'Attended')],
        string='Status', default='draft', readonly=True, copy=False, tracking=True)

    @api.constrains('event_id', 'state')
    def _check_seats_limit(self):
        for registration in self:
            if registration.event_id.seats_availability == 'limited' and registration.event_id.seats_max and registration.event_id.seats_available < (1 if registration.state == 'draft' else 0):
                raise ValidationError(_('No more seats available for this event.'))

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            self.update(self._synchronize_partner_values(self.partner_id))

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model
    def create(self, vals):
        # update missing pieces of information from partner
        if vals.get('partner_id'):
            partner_vals = self._synchronize_partner_values(
                self.env['res.partner'].browse(vals['partner_id'])
            )
            vals = dict(partner_vals, **vals)

        registration = super(EventRegistration, self).create(vals)
        if registration._check_auto_confirmation():
            registration.sudo().action_confirm()

        return registration

    def write(self, vals):
        if vals.get('state') == 'done' and 'date_closed' not in vals:
            vals['date_closed'] = fields.Datetime.now()

        ret = super(EventRegistration, self).write(vals)

        # update missing pieces of information from partner
        if vals.get('partner_id'):
            partner_vals = self._synchronize_partner_values(
                self.env['res.partner'].browse(vals['partner_id'])
            )
            for registration in self:
                partner_info = dict((key, val) for key, val in partner_vals.items() if not registration[key])
                if partner_info:
                    registration.write(partner_info)

        if vals.get('state') == 'open':
            # auto-trigger after_sub (on subscribe) mail schedulers, if needed
            onsubscribe_schedulers = self.mapped('event_id.event_mail_ids').filtered(lambda s: s.interval_type == 'after_sub')
            onsubscribe_schedulers.execute()

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

    def _check_auto_confirmation(self):
        if self._context.get('registration_force_draft'):
            return False
        if any(not registration.event_id.auto_confirm or
               (not registration.event_id.seats_available and registration.event_id.seats_availability == 'limited') for registration in self):
            return False
        return True

    def _synchronize_partner_values(self, partner):
        if partner:
            contact_id = partner.address_get().get('contact', False)
            if contact_id:
                contact = self.env['res.partner'].browse(contact_id)
                return dict((fname, contact[fname]) for fname in ['name', 'email', 'phone', 'mobile'] if contact[fname])
        return {}

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
        return {r.id: {
            'partner_ids': [],
            'email_to': r.email,
            'email_cc': False}
            for r in self}

    def _message_post_after_hook(self, message, msg_vals):
        if self.email and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.email)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('email', '=', new_partner.email),
                    ('state', 'not in', ['cancel']),
                ]).write({'partner_id': new_partner.id})
        return super(EventRegistration, self)._message_post_after_hook(message, msg_vals)

    def action_send_badge_email(self):
        """ Open a window to compose an email, with the template - 'event_badge'
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('event.event_registration_mail_template_badge')
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='event.registration',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_light",
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

    def get_date_range_str(self):
        self.ensure_one()
        today = fields.Datetime.now()
        event_date = self.event_begin_date
        diff = (event_date.date() - today.date())
        if diff.days <= 0:
            return _('today')
        elif diff.days == 1:
            return _('tomorrow')
        elif (diff.days < 7):
            return _('in %d days') % (diff.days, )
        elif (diff.days < 14):
            return _('next week')
        elif event_date.month == (today + relativedelta(months=+1)).month:
            return _('next month')
        else:
            return _('on ') + format_datetime(self.env, self.event_begin_date, tz=self.event_id.date_tz, dt_format='medium')

    def summary(self):
        self.ensure_one()
        return {'information': []}
