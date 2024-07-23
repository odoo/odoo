# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz
import textwrap

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, Command, fields, models, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_date, format_datetime, format_time, frozendict
from odoo.tools.mail import is_html_empty, html_to_inner_content
from odoo.tools.misc import formatLang
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files")
    vobject = None


class EventType(models.Model):
    _name = 'event.type'
    _description = 'Event Template'
    _order = 'sequence, id'

    def _default_event_mail_type_ids(self):
        return [(0, 0,
                 {'interval_nbr': 0,
                  'interval_unit': 'now',
                  'interval_type': 'after_sub',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_subscription').id,
                 }),
                (0, 0,
                 {'interval_nbr': 1,
                  'interval_unit': 'hours',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 }),
                (0, 0,
                 {'interval_nbr': 3,
                  'interval_unit': 'days',
                  'interval_type': 'before_event',
                  'template_ref': 'mail.template, %i' % self.env.ref('event.event_reminder').id,
                 })]

    def _default_question_ids(self):
        return [
            (0, 0, {'title': _('Name'), 'question_type': 'name', 'is_mandatory_answer': True}),
            (0, 0, {'title': _('Email'), 'question_type': 'email', 'is_mandatory_answer': True}),
            (0, 0, {'title': _('Phone'), 'question_type': 'phone'}),
        ]

    name = fields.Char('Event Template', required=True, translate=True)
    note = fields.Html(string='Note')
    sequence = fields.Integer(default=10)
    # tickets
    event_type_ticket_ids = fields.One2many('event.type.ticket', 'event_type_id', string='Tickets')
    tag_ids = fields.Many2many('event.tag', string="Tags")
    # registration
    has_seats_limitation = fields.Boolean('Limited Seats')
    seats_max = fields.Integer(
        'Maximum Registrations', compute='_compute_seats_max',
        readonly=False, store=True,
        help="It will select this default maximum value when you choose this event")
    default_timezone = fields.Selection(
        _tz_get, string='Timezone', default=lambda self: self.env.user.tz or 'UTC')
    # communication
    event_type_mail_ids = fields.One2many(
        'event.type.mail', 'event_type_id', string='Mail Schedule',
        default=_default_event_mail_type_ids)
    # ticket reports
    ticket_instructions = fields.Html('Ticket Instructions', translate=True,
        help="This information will be printed on your tickets.")
    question_ids = fields.One2many(
        'event.question', 'event_type_id', default=_default_question_ids,
        string='Questions', copy=True)

    @api.depends('has_seats_limitation')
    def _compute_seats_max(self):
        for template in self:
            if not template.has_seats_limitation:
                template.seats_max = 0


class EventEvent(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin, id'

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if 'date_begin' in fields_list and 'date_begin' not in result:
            now = fields.Datetime.now()
            # Round the datetime to the nearest half hour (e.g. 08:17 => 08:30 and 08:37 => 09:00)
            result['date_begin'] = now.replace(second=0, microsecond=0) + timedelta(minutes=-now.minute % 30)
        if 'date_end' in fields_list and 'date_end' not in result and result.get('date_begin'):
            result['date_end'] = result['date_begin'] + timedelta(days=1)
        return result

    def get_kiosk_url(self):
        return self.get_base_url() + "/odoo/registration-desk"

    def _get_default_stage_id(self):
        return self.env['event.stage'].search([], limit=1)

    def _default_description(self):
        # avoid template branding with rendering_bundle=True
        return self.env['ir.ui.view'].with_context(rendering_bundle=True) \
            ._render_template('event.event_default_descripton')

    def _default_event_mail_ids(self):
        return self.env['event.type']._default_event_mail_type_ids()

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    def _default_question_ids(self):
        return self.env['event.type']._default_question_ids()

    name = fields.Char(string='Event', translate=True, required=True)
    note = fields.Html(string='Note', store=True, compute="_compute_note", readonly=False)
    description = fields.Html(string='Description', translate=html_translate, sanitize_attributes=False, sanitize_form=False, default=_default_description)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True,
        default=lambda self: self.env.user)
    use_barcode = fields.Boolean(compute='_compute_use_barcode')
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env.company,
        required=False)
    organizer_id = fields.Many2one(
        'res.partner', string='Organizer', tracking=True,
        default=lambda self: self.env.company.partner_id,
        check_company=True)
    event_type_id = fields.Many2one(
        'event.type', string='Template', ondelete='set null',
        help="Choose a template to auto-fill tickets, communications, descriptions and other fields.")
    event_mail_ids = fields.One2many(
        'event.mail', 'event_id', string='Mail Schedule', copy=True,
        compute='_compute_event_mail_ids', readonly=False, store=True)
    tag_ids = fields.Many2many(
        'event.tag', string="Tags", readonly=False,
        store=True, compute="_compute_tag_ids")
    # properties
    registration_properties_definition = fields.PropertiesDefinition('Registration Properties')
    # Kanban fields
    kanban_state = fields.Selection([('normal', 'In Progress'), ('done', 'Done'), ('blocked', 'Blocked')], default='normal', copy=False)
    kanban_state_label = fields.Char(
        string='Kanban State Label', compute='_compute_kanban_state_label',
        store=True, tracking=True)
    stage_id = fields.Many2one(
        'event.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_expand_full', tracking=True, copy=False)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True)
    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Attendees',
        compute='_compute_seats_max', readonly=False, store=True,
        help="For each event you can define a maximum registration of seats(number of attendees), above this numbers the registrations are not accepted.")
    seats_limited = fields.Boolean('Limit Attendees', required=True, compute='_compute_seats_limited',
                                   precompute=True, readonly=False, store=True)
    seats_reserved = fields.Integer(
        string='Number of Registrations',
        store=False, readonly=True, compute='_compute_seats')
    seats_available = fields.Integer(
        string='Available Seats',
        store=False, readonly=True, compute='_compute_seats')
    seats_used = fields.Integer(
        string='Number of Attendees',
        store=False, readonly=True, compute='_compute_seats')
    seats_taken = fields.Integer(
        string='Number of Taken Seats',
        store=False, readonly=True, compute='_compute_seats')
    # Registration fields
    registration_ids = fields.One2many('event.registration', 'event_id', string='Attendees')
    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket', copy=True,
        compute='_compute_event_ticket_ids', readonly=False, store=True)
    event_registrations_started = fields.Boolean(
        'Registrations started', compute='_compute_event_registrations_started',
        help="registrations have started if the current datetime is after the earliest starting date of tickets."
    )
    event_registrations_open = fields.Boolean(
        'Registration open', compute='_compute_event_registrations_open', compute_sudo=True,
        help="Registrations are open if:\n"
        "- the event is not ended\n"
        "- there are seats available on event\n"
        "- the tickets are sellable (if ticketing is used)")
    event_registrations_sold_out = fields.Boolean(
        'Sold Out', compute='_compute_event_registrations_sold_out', compute_sudo=True,
        help='The event is sold out if no more seats are available on event. If ticketing is used and all tickets are sold out, the event will be sold out.')
    start_sale_datetime = fields.Datetime(
        'Start sale date', compute='_compute_start_sale_date',
        help='If ticketing is used, contains the earliest starting sale date of tickets.')
    # Date fields
    date_tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        compute='_compute_date_tz', precompute=True, readonly=False, store=True)
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True)
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
    date_begin_located = fields.Char(string='Start Date Located', compute='_compute_date_begin_tz')
    date_end_located = fields.Char(string='End Date Located', compute='_compute_date_end_tz')
    is_ongoing = fields.Boolean('Is Ongoing', compute='_compute_is_ongoing', search='_search_is_ongoing')
    is_one_day = fields.Boolean(compute='_compute_field_is_one_day')
    is_finished = fields.Boolean(compute='_compute_is_finished', search='_search_is_finished')
    # Location and communication
    address_id = fields.Many2one(
        'res.partner', string='Venue', default=lambda self: self.env.company.partner_id.id,
        check_company=True,
        tracking=True
    )
    address_search = fields.Many2one(
        'res.partner', string='Address', compute='_compute_address_search', search='_search_address_search')
    address_inline = fields.Char(
        string='Venue (formatted for one line uses)', compute='_compute_address_inline',
        compute_sudo=True)
    country_id = fields.Many2one(
        'res.country', 'Country', related='address_id.country_id', readonly=False, store=True)
    lang = fields.Selection(_lang_get, string='Language',
        help="All the communication emails sent to attendees will be translated in this language.")
    # ticket reports
    badge_format = fields.Selection(
        string='Badge Dimension',
        selection=[
            ('A4_french_fold', 'A4 foldable'),
            ('A6', 'A6'),
            ('four_per_sheet', '4 per sheet'),
            ('96x82', '96x82mm (Badge Printer)'),
            ('96x134', '96x134mm (Badge Printer)')
        ], default='A6', required=True)
    badge_image = fields.Image('Badge Background', max_width=1024, max_height=1024)
    ticket_instructions = fields.Html('Ticket Instructions', translate=True,
        compute='_compute_ticket_instructions', store=True, readonly=False,
        help="This information will be printed on your tickets.")
    # questions
    question_ids = fields.One2many(
        'event.question', 'event_id', 'Questions', copy=True,
        compute='_compute_question_ids', readonly=False, store=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('once_per_order', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('once_per_order', '=', False)])

    def _compute_use_barcode(self):
        use_barcode = self.env['ir.config_parameter'].sudo().get_param('event.use_event_barcode') == 'True'
        for record in self:
            record.use_barcode = use_barcode

    @api.depends('event_type_id')
    def _compute_question_ids(self):
        """ Update event questions from its event type. Depends are set only on
        event_type_id itself to emulate an onchange. Changing event type content
        itself should not trigger this method.

        When synchronizing questions:

          * lines with no registered answers are removed;
          * type lines are added;
        """
        if self._origin.question_ids:
            # lines to keep: those with already given answers
            questions_tokeep_ids = self.env['event.registration.answer'].search(
                [('question_id', 'in', self._origin.question_ids.ids)]
            ).question_id.ids
        else:
            questions_tokeep_ids = []
        for event in self:
            if not event.event_type_id and not event.question_ids:
                event.question_ids = self._default_question_ids()
                continue

            if questions_tokeep_ids:
                questions_toremove = event._origin.question_ids.filtered(
                    lambda question: question.id not in questions_tokeep_ids)
                command = [(3, question.id) for question in questions_toremove]
            else:
                command = [(5, 0)]
            event.question_ids = command

            # copy questions so changes in the event don't affect the event type
            event.question_ids += event.event_type_id.question_ids.copy({
                'event_type_id': False,
            })

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for event in self:
            if event.kanban_state == 'normal':
                event.kanban_state_label = event.stage_id.legend_normal
            elif event.kanban_state == 'blocked':
                event.kanban_state_label = event.stage_id.legend_blocked
            else:
                event.kanban_state_label = event.stage_id.legend_done

    @api.depends('seats_max', 'registration_ids.state', 'registration_ids.active')
    def _compute_seats(self):
        """ Determine available, reserved, used and taken seats. """
        # initialize fields to 0
        for event in self:
            event.seats_reserved = event.seats_used = event.seats_available = 0
        # aggregate registrations by event and by state
        state_field = {
            'open': 'seats_reserved',
            'done': 'seats_used',
        }
        base_vals = dict((fname, 0) for fname in state_field.values())
        results = dict((event_id, dict(base_vals)) for event_id in self.ids)
        if self.ids:
            query = """ SELECT event_id, state, count(event_id)
                        FROM event_registration
                        WHERE event_id IN %s AND state IN ('open', 'done') AND active = true
                        GROUP BY event_id, state
                    """
            self.env['event.registration'].flush_model(['event_id', 'state', 'active'])
            self._cr.execute(query, (tuple(self.ids),))
            res = self._cr.fetchall()
            for event_id, state, num in res:
                results[event_id][state_field[state]] = num

        # compute seats_available and expected
        for event in self:
            event.update(results.get(event._origin.id or event.id, base_vals))
            if event.seats_max > 0:
                event.seats_available = event.seats_max - (event.seats_reserved + event.seats_used)

            event.seats_taken = event.seats_reserved + event.seats_used

    @api.depends('date_tz', 'start_sale_datetime')
    def _compute_event_registrations_started(self):
        for event in self:
            event = event._set_tz_context()
            if event.start_sale_datetime:
                current_datetime = fields.Datetime.context_timestamp(event, fields.Datetime.now())
                start_sale_datetime = fields.Datetime.context_timestamp(event, event.start_sale_datetime)
                event.event_registrations_started = (current_datetime >= start_sale_datetime)
            else:
                event.event_registrations_started = True

    @api.depends('date_tz', 'event_registrations_started', 'date_end', 'seats_available', 'seats_limited', 'seats_max',
                 'event_ticket_ids.sale_available')
    def _compute_event_registrations_open(self):
        """ Compute whether people may take registrations for this event

          * event.date_end -> if event is done, registrations are not open anymore;
          * event.start_sale_datetime -> lowest start date of tickets (if any; start_sale_datetime
            is False if no ticket are defined, see _compute_start_sale_date);
          * any ticket is available for sale (seats available) if any;
          * seats are unlimited or seats are available;
        """
        for event in self:
            event = event._set_tz_context()
            current_datetime = fields.Datetime.context_timestamp(event, fields.Datetime.now())
            date_end_tz = event.date_end.astimezone(pytz.timezone(event.date_tz or 'UTC')) if event.date_end else False
            event.event_registrations_open = event.event_registrations_started and \
                (date_end_tz >= current_datetime if date_end_tz else True) and \
                (not event.seats_limited or not event.seats_max or event.seats_available) and \
                (not event.event_ticket_ids or any(ticket.sale_available for ticket in event.event_ticket_ids))

    @api.depends('event_ticket_ids.start_sale_datetime')
    def _compute_start_sale_date(self):
        """ Compute the start sale date of an event. Currently lowest starting sale
        date of tickets if they are used, of False. """
        for event in self:
            start_dates = [ticket.start_sale_datetime for ticket in event.event_ticket_ids if not ticket.is_expired]
            event.start_sale_datetime = min(start_dates) if start_dates and all(start_dates) else False

    @api.depends('event_ticket_ids.sale_available', 'seats_available', 'seats_limited')
    def _compute_event_registrations_sold_out(self):
        """Note that max seats limits for events and sum of limits for all its tickets may not be
        equal to enable flexibility.
        E.g. max 20 seats for ticket A, 20 seats for ticket B
            * With max 20 seats for the event
            * Without limit set on the event (=40, but the customer didn't explicitly write 40)
        """
        for event in self:
            event.event_registrations_sold_out = (
                (event.seats_limited and event.seats_max and not event.seats_available)
                or (event.event_ticket_ids and all(ticket.is_sold_out for ticket in event.event_ticket_ids))
            )

    @api.depends('date_tz', 'date_begin')
    def _compute_date_begin_tz(self):
        for event in self:
            if event.date_begin:
                event.date_begin_located = format_datetime(
                    self.env, event.date_begin, tz=event.date_tz, dt_format='medium')
            else:
                event.date_begin_located = False

    @api.depends('date_tz', 'date_end')
    def _compute_date_end_tz(self):
        for event in self:
            if event.date_end:
                event.date_end_located = format_datetime(
                    self.env, event.date_end, tz=event.date_tz, dt_format='medium')
            else:
                event.date_end_located = False

    @api.depends('date_begin', 'date_end')
    def _compute_is_ongoing(self):
        now = fields.Datetime.now()
        for event in self:
            event.is_ongoing = event.date_begin <= now < event.date_end

    def _search_is_ongoing(self, operator, value):
        if operator not in ['=', '!=']:
            raise UserError(_('This operator is not supported'))
        if not isinstance(value, bool):
            raise UserError(_('Value should be True or False (not %s)', value))
        now = fields.Datetime.now()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = [('date_begin', '<=', now), ('date_end', '>', now)]
        else:
            domain = ['|', ('date_begin', '>', now), ('date_end', '<=', now)]
        return domain

    @api.depends('date_begin', 'date_end', 'date_tz')
    def _compute_field_is_one_day(self):
        for event in self:
            # Need to localize because it could begin late and finish early in
            # another timezone
            event = event._set_tz_context()
            begin_tz = fields.Datetime.context_timestamp(event, event.date_begin)
            end_tz = fields.Datetime.context_timestamp(event, event.date_end)
            event.is_one_day = (begin_tz.date() == end_tz.date())

    @api.depends('date_end')
    def _compute_is_finished(self):
        for event in self:
            if not event.date_end:
                event.is_finished = False
                continue
            event = event._set_tz_context()
            current_datetime = fields.Datetime.context_timestamp(event, fields.Datetime.now())
            datetime_end = fields.Datetime.context_timestamp(event, event.date_end)
            event.is_finished = datetime_end <= current_datetime

    def _search_is_finished(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('This operator is not supported'))
        if not isinstance(value, bool):
            raise ValueError(_('Value should be True or False (not %s)'), value)
        now = fields.Datetime.now()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = [('date_end', '<=', now)]
        else:
            domain = [('date_end', '>', now)]
        return domain

    @api.depends('event_type_id')
    def _compute_date_tz(self):
        for event in self:
            if event.event_type_id.default_timezone:
                event.date_tz = event.event_type_id.default_timezone
            if not event.date_tz:
                event.date_tz = self.env.user.tz or 'UTC'

    @api.depends('address_id')
    def _compute_address_search(self):
        for event in self:
            event.address_search = event.address_id

    def _search_address_search(self, operator, value):
        if operator != 'ilike' or not isinstance(value, str):
            raise NotImplementedError(_('Operation not supported.'))

        return expression.OR([
            [('address_id.name', 'ilike', value)],
            [('address_id.street', 'ilike', value)],
            [('address_id.street2', 'ilike', value)],
            [('address_id.city', 'ilike', value)],
            [('address_id.zip', 'ilike', value)],
            [('address_id.state_id', 'ilike', value)],
            [('address_id.country_id', 'ilike', value)],
        ])


    # seats

    @api.depends('event_type_id')
    def _compute_seats_max(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method. """
        for event in self:
            if not event.event_type_id:
                event.seats_max = event.seats_max or 0
            else:
                event.seats_max = event.event_type_id.seats_max or 0

    @api.depends('event_type_id')
    def _compute_seats_limited(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method. """
        for event in self:
            if event.event_type_id.has_seats_limitation != event.seats_limited:
                event.seats_limited = event.event_type_id.has_seats_limitation
            if not event.seats_limited:
                event.seats_limited = False

    @api.depends('event_type_id')
    def _compute_event_mail_ids(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method.

        When synchronizing mails:

          * lines that are not sent and have no registrations linked are remove;
          * type lines are added;
        """
        for event in self:
            if not event.event_type_id and not event.event_mail_ids:
                event.event_mail_ids = self._default_event_mail_ids()
                continue

            # lines to keep: those with already sent emails or registrations
            mails_to_remove = event.event_mail_ids.filtered(
                lambda mail: not(mail._origin.mail_done) and not(mail._origin.mail_registration_ids)
            )
            command = [Command.unlink(mail.id) for mail in mails_to_remove]

            # lines to add: those which do not have the exact copy available in lines to keep
            if event.event_type_id.event_type_mail_ids:
                mails_to_keep_vals = {frozendict(mail._prepare_event_mail_values()) for mail in event.event_mail_ids - mails_to_remove}
                for mail in event.event_type_id.event_type_mail_ids:
                    mail_values = frozendict(mail._prepare_event_mail_values())
                    if mail_values not in mails_to_keep_vals:
                        command.append(Command.create(mail_values))
            if command:
                event.event_mail_ids = command

    @api.depends('event_type_id')
    def _compute_tag_ids(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method. """
        for event in self:
            if not event.tag_ids and event.event_type_id.tag_ids:
                event.tag_ids = event.event_type_id.tag_ids

    @api.depends('event_type_id')
    def _compute_event_ticket_ids(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method.

        When synchronizing tickets:

          * lines that have no registrations linked are remove;
          * type lines are added;

        Note that updating event_ticket_ids triggers _compute_start_sale_date
        (start_sale_datetime computation) so ensure result to avoid cache miss.
        """
        for event in self:
            if not event.event_type_id and not event.event_ticket_ids:
                event.event_ticket_ids = False
                continue

            # lines to keep: those with existing registrations
            tickets_to_remove = event.event_ticket_ids.filtered(lambda ticket: not ticket._origin.registration_ids)
            command = [Command.unlink(ticket.id) for ticket in tickets_to_remove]
            if event.event_type_id.event_type_ticket_ids:
                command += [
                    Command.create({
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.ticket']._get_event_ticket_fields_whitelist()
                    }) for line in event.event_type_id.event_type_ticket_ids
                ]
            event.event_ticket_ids = command

    @api.depends('event_type_id')
    def _compute_note(self):
        for event in self:
            if event.event_type_id and not is_html_empty(event.event_type_id.note):
                event.note = event.event_type_id.note

    @api.depends('event_type_id')
    def _compute_ticket_instructions(self):
        for event in self:
            if is_html_empty(event.ticket_instructions) and not \
               is_html_empty(event.event_type_id.ticket_instructions):
                event.ticket_instructions = event.event_type_id.ticket_instructions

    @api.depends('address_id')
    def _compute_address_inline(self):
        """Use venue address if available, otherwise its name, finally ''. """
        for event in self:
            if (event.address_id.contact_address or '').strip():
                event.address_inline = ', '.join(
                    frag.strip()
                    for frag in event.address_id.contact_address.split('\n') if frag.strip()
                )
            else:
                event.address_inline = event.address_id.name or ''

    @api.constrains('seats_max', 'seats_limited', 'registration_ids')
    def _check_seats_availability(self, minimal_availability=0):
        sold_out_events = []
        for event in self:
            if event.seats_limited and event.seats_max and event.seats_available < minimal_availability:
                sold_out_events.append(
                    (_('- "%(event_name)s": Missing %(nb_too_many)i seats.',
                        event_name=event.name, nb_too_many=-event.seats_available)))
        if sold_out_events:
            raise ValidationError(_('There are not enough seats available for:')
                                  + '\n%s\n' % '\n'.join(sold_out_events))

    @api.constrains('date_begin', 'date_end')
    def _check_closing_date(self):
        for event in self:
            if event.date_end < event.date_begin:
                raise ValidationError(_('The closing date cannot be earlier than the beginning date.'))

    @api.model_create_multi
    def create(self, vals_list):
        events = super(EventEvent, self).create(vals_list)
        for res in events:
            if res.organizer_id:
                res.message_subscribe([res.organizer_id.id])
        self.env.flush_all()
        return events

    def write(self, vals):
        if 'stage_id' in vals and 'kanban_state' not in vals:
            # reset kanban state when changing stage
            vals['kanban_state'] = 'normal'
        res = super(EventEvent, self).write(vals)
        if vals.get('organizer_id'):
            self.message_subscribe([vals['organizer_id']])
        return res

    @api.depends('event_registrations_sold_out', 'seats_limited', 'seats_max', 'seats_available')
    @api.depends_context('name_with_seats_availability')
    def _compute_display_name(self):
        """Adds ticket seats availability if requested by context."""
        if not self.env.context.get('name_with_seats_availability'):
            return super()._compute_display_name()
        for event in self:
            # event or its tickets are sold out
            if event.event_registrations_sold_out:
                name = _('%(event_name)s (Sold out)', event_name=event.name)
            elif event.seats_limited and event.seats_max:
                name = _(
                    '%(event_name)s (%(count)s seats remaining)',
                    event_name=event.name,
                    count=formatLang(self.env, event.seats_available, digits=0),
                )
            else:
                name = event.name
            event.display_name = name

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", event.name)) for event, vals in zip(self, vals_list)]

    @api.model
    def _get_mail_message_access(self, res_ids, operation, model_name=None):
        if (
            operation == 'create'
            and self.env.user.has_group('event.group_event_registration_desk')
            and (not model_name or model_name == 'event.event')
        ):
            # allow the registration desk users to post messages on Event
            # can not be done with "_mail_post_access" otherwise public user will be
            # able to post on published Event (see website_event)
            return 'read'
        return super(EventEvent, self)._get_mail_message_access(res_ids, operation, model_name)

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.date_tz or 'UTC')

    def action_set_done(self):
        """
        Action which will move the events
        into the first next (by sequence) stage defined as "Ended"
        (if they are not already in an ended stage)
        """
        first_ended_stage = self.env['event.stage'].search([('pipe_end', '=', True)], limit=1, order='sequence')
        if first_ended_stage:
            self.write({'stage_id': first_ended_stage.id})

    def mail_attendees(self, template_id, force_send=False, filter_func=lambda self: self.state not in ('cancel', 'draft')):
        for event in self:
            for attendee in event.registration_ids.filtered(filter_func):
                self.env['mail.template'].browse(template_id).send_mail(attendee.id, force_send=force_send)

    def _get_date_range_str(self, lang_code=False):
        self.ensure_one()
        today_tz = pytz.utc.localize(fields.Datetime.now()).astimezone(pytz.timezone(self.date_tz))
        event_date_tz = pytz.utc.localize(self.date_begin).astimezone(pytz.timezone(self.date_tz))
        diff = (event_date_tz.date() - today_tz.date())
        if diff.days <= 0:
            return _('today')
        if diff.days == 1:
            return _('tomorrow')
        if (diff.days < 7):
            return _('in %d days', diff.days)
        if (diff.days < 14):
            return _('next week')
        if event_date_tz.month == (today_tz + relativedelta(months=+1)).month:
            return _('next month')
        return _('on %(date)s', date=format_date(self.env, self.date_begin, lang_code=lang_code, date_format='medium'))

    def _get_external_description(self):
        """
        Description of the event shortened to maximum 1900 characters to
        leave some space for addition by sub-modules, such as the even link.
        Meant to be used for external content (ics/icalc/Gcal).

        Reference Docs for URL limit -: https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
        """
        self.ensure_one()
        description = html_to_inner_content(self.description)
        return textwrap.shorten(description, 1900)

    def _get_ics_file(self):
        """ Returns iCalendar file for the event invitation.
            :returns a dict of .ics file content for each event
        """
        result = {}
        if not vobject:
            return result

        for event in self:
            cal = vobject.iCalendar()
            cal_event = cal.add('vevent')

            cal_event.add('created').value = fields.Datetime.now().replace(tzinfo=pytz.timezone('UTC'))
            cal_event.add('dtstart').value = event.date_begin.astimezone(pytz.timezone(event.date_tz))
            cal_event.add('dtend').value = event.date_end.astimezone(pytz.timezone(event.date_tz))
            cal_event.add('summary').value = event.name
            cal_event.add('description').value = event._get_external_description()
            if event.address_id:
                cal_event.add('location').value = event.address_inline

            result[event.id] = cal.serialize().encode('utf-8')
        return result

    def _get_tickets_access_hash(self, registration_ids):
        """ Returns the ground truth hash for accessing the tickets in route /event/<int:event_id>/my_tickets.
        The dl links are always made event-dependant, hence the method linked to the record in self.
        """
        self.ensure_one()
        return tools.hmac(self.env(su=True), 'event-registration-ticket-report-access', (self.id, sorted(registration_ids)))

    @api.autovacuum
    def _gc_mark_events_done(self):
        """ move every ended events in the next 'ended stage' """
        ended_events = self.env['event.event'].search([
            ('date_end', '<', fields.Datetime.now()),
            ('stage_id.pipe_end', '=', False),
        ])
        if ended_events:
            ended_events.action_set_done()

    def _get_event_timeframe_string(self):
        self.ensure_one()
        start_datetime = format_datetime(self.env, self.date_begin, self.date_tz, "short")
        if self.is_one_day:
            end_datetime = format_time(self.env, self.date_end, self.date_tz, "short")
        else:
            end_datetime = format_datetime(self.env, self.date_end, self.date_tz, "short")
        return _("%(start_date)s to %(end_date)s", start_date=start_datetime, end_date=end_datetime)

    def _get_event_print_details(self):
        self.ensure_one()
        return {
            'name': self.name,
            'badge_image': self.badge_image,
            'timeframe': self._get_event_timeframe_string(),
            'address': self.address_id.name if self.address_id else None,
            'logo': self.company_id.logo,
            'sponsor_text': self._get_printing_sponsor_text()
        }

    def _get_printing_sponsor_text(self):
        sponsor_text = self.env['ir.config_parameter'].sudo().get_param('event.badge_printing_sponsor_text')
        return sponsor_text or "Powered by Odoo"
