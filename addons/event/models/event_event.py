# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz
import textwrap
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from markupsafe import escape
from urllib.parse import urlparse

from odoo import _, api, Command, fields, models, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.fields import Datetime, Domain
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


class EventEvent(models.Model):
    """Event"""
    _name = 'event.event'
    _description = 'Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_begin, id'

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if 'date_begin' in fields and 'date_begin' not in result:
            now = Datetime.now()
            # Round the datetime to the nearest half hour (e.g. 08:17 => 08:30 and 08:37 => 09:00)
            result['date_begin'] = now.replace(second=0, microsecond=0) + timedelta(minutes=-now.minute % 30)
        if 'date_end' in fields and 'date_end' not in result and result.get('date_begin'):
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
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready for Next Stage'),
        ('blocked', 'Blocked'),
        ('cancel', 'Cancelled')
    ], default='normal', copy=False, compute='_compute_kanban_state', readonly=False, store=True, tracking=True)
    stage_id = fields.Many2one(
        'event.stage', ondelete='restrict', default=_get_default_stage_id,
        group_expand='_read_group_expand_full', tracking=True, copy=False)
    # Seats and computation
    seats_max = fields.Integer(
        string='Maximum Attendees',
        compute='_compute_seats_max', readonly=False, store=True,
        help="For each event you can define a maximum registration of seats(number of attendees), above this number the registrations are not accepted. "
        "If the event has multiple slots, this maximum number is applied per slot.")
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
    is_multi_slots = fields.Boolean("Is Multi Slots", copy=True,
        help="Allow multiple time slots. "
        "The communications, the maximum number of attendees and the maximum number of tickets registrations "
        "are defined for each time slot instead of the whole event.")
    event_slot_ids = fields.One2many("event.slot", "event_id", "Slots", copy=True)
    event_slot_count = fields.Integer("Slots Count", compute="_compute_event_slot_count")
    event_ticket_ids = fields.One2many(
        'event.event.ticket', 'event_id', string='Event Ticket', copy=True,
        compute='_compute_event_ticket_ids', readonly=False, store=True, precompute=True)
    event_registrations_started = fields.Boolean(
        'Registrations started', compute='_compute_event_registrations_started',
        help="registrations have started if the current datetime is after the earliest starting date of tickets."
    )
    event_registrations_open = fields.Boolean(
        'Registration open', compute='_compute_event_registrations_open', compute_sudo=True,
        help="Registrations are open if:\n"
        "- the event is not ended or not cancelled\n"
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
        _tz_get, string='Display Timezone', required=True,
        compute='_compute_date_tz', precompute=True, readonly=False, store=True,
        help="Indicates the timezone in which the event dates/times will be displayed on the website.")
    date_begin = fields.Datetime(string='Start Date', required=True, tracking=True,
        help="When the event is scheduled to take place (expressed in your local timezone on the form view).")
    date_end = fields.Datetime(string='End Date', required=True, tracking=True)
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
    event_url = fields.Char(
        string='Online Event URL', compute='_compute_event_url', readonly=False, store=True,
        help="Link where the online event will take place.",
    )
    event_share_url = fields.Char(string='Event Share URL', compute='_compute_event_share_url')
    lang = fields.Selection(_lang_get, string='Language',
        help="All the communication emails sent to attendees will be translated in this language.")
    # ticket reports
    badge_format = fields.Selection(
        string='Badge Dimension',
        selection=[
            ('A4_french_fold', 'A4 foldable'),
            ('A6', 'A6'),
            ('four_per_sheet', '4 per sheet'),
        ], default='A6', required=True)
    badge_image = fields.Image('Badge Background', max_width=1024, max_height=1024)
    ticket_instructions = fields.Html('Ticket Instructions', translate=True,
        compute='_compute_ticket_instructions', store=True, readonly=False,
        help="This information will be printed on your tickets.")
    # questions
    question_ids = fields.One2many(
        'event.question', 'event_id', 'Questions', copy=True,
        compute='_compute_question_ids', readonly=False, store=True, precompute=True)
    general_question_ids = fields.One2many('event.question', 'event_id', 'General Questions',
                                           domain=[('once_per_order', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Specific Questions',
                                            domain=[('once_per_order', '=', False)])

    def _compute_use_barcode(self):
        use_barcode = self.env['ir.config_parameter'].sudo().get_param('event.use_event_barcode') == 'True'
        for record in self:
            record.use_barcode = use_barcode

    def _compute_event_share_url(self):
        """Get the URL to use to redirect to the event, overriden in website for fallback."""
        for event in self:
            event.event_share_url = event.event_url

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

    @api.depends('event_slot_count', 'is_multi_slots', 'seats_max', 'registration_ids.state', 'registration_ids.active')
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
            self.env.cr.execute(query, (tuple(self.ids),))
            res = self.env.cr.fetchall()
            for event_id, state, num in res:
                results[event_id][state_field[state]] = num

        # compute seats_available and expected
        for event in self:
            event.update(results.get(event._origin.id or event.id, base_vals))
            seats_max = event.seats_max * event.event_slot_count if event.is_multi_slots else event.seats_max
            if seats_max > 0:
                event.seats_available = seats_max - (event.seats_reserved + event.seats_used)

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

          * for cancelled events, registrations are not open;
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
            event.event_registrations_open = event.kanban_state != 'cancel' and \
                event.event_registrations_started and \
                (date_end_tz >= current_datetime if date_end_tz else True) and \
                (not event.seats_limited or not event.seats_max or event.seats_available) and \
                (
                    # Not multi slots: open if no tickets or at least a sale available ticket
                    (not event.is_multi_slots and
                        (not event.event_ticket_ids or any(ticket.sale_available for ticket in event.event_ticket_ids)))
                    or
                    # Multi slots: open if at least a slot and no tickets or at least an ongoing ticket with availability
                    (event.is_multi_slots and event.event_slot_count and (
                        not event.event_ticket_ids or any(
                            ticket.is_launched and not ticket.is_expired and (
                                any(availability is None or availability > 0
                                    for availability in event._get_seats_availability([
                                        (slot, ticket)
                                        for slot in event.event_slot_ids
                                    ])
                                )
                            ) for ticket in event.event_ticket_ids
                        )
                    ))
                )

    @api.depends('event_ticket_ids.start_sale_datetime')
    def _compute_start_sale_date(self):
        """ Compute the start sale date of an event. Currently lowest starting sale
        date of tickets if they are used, of False. """
        for event in self:
            start_dates = [ticket.start_sale_datetime for ticket in event.event_ticket_ids if not ticket.is_expired]
            event.start_sale_datetime = min(start_dates) if start_dates and all(start_dates) else False

    @api.depends('event_slot_ids', 'event_ticket_ids.sale_available', 'seats_available', 'seats_limited')
    def _compute_event_registrations_sold_out(self):
        """Note that max seats limits for events and sum of limits for all its tickets may not be
        equal to enable flexibility.
        E.g. max 20 seats for ticket A, 20 seats for ticket B
            * With max 20 seats for the event
            * Without limit set on the event (=40, but the customer didn't explicitly write 40)
        When the event is multi slots, instead of checking if every tickets is sold out,
        checking if every slot-ticket combination is sold out.
        """
        for event in self:
            event.event_registrations_sold_out = (
                (event.seats_limited and event.seats_max and not event.seats_available > 0)
                or (event.event_ticket_ids and (
                    not any(availability is None or availability > 0
                        for availability in event._get_seats_availability([
                            (slot, ticket)
                            for slot in event.event_slot_ids
                            for ticket in event.event_ticket_ids
                        ])
                    )
                    if event.is_multi_slots else
                    all(ticket.is_sold_out for ticket in event.event_ticket_ids)
                ))
            )

    @api.depends('date_begin', 'date_end')
    def _compute_is_ongoing(self):
        now = fields.Datetime.now()
        for event in self:
            event.is_ongoing = event.date_begin <= now < event.date_end

    def _search_is_ongoing(self, operator, value):
        if operator != 'in':
            return NotImplemented
        now = fields.Datetime.now()
        return [('date_begin', '<=', now), ('date_end', '>', now)]

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
        if operator != 'in':
            return NotImplemented
        return [('date_end', '<=', fields.Datetime.now())]

    @api.depends('event_type_id')
    def _compute_date_tz(self):
        for event in self:
            if event.event_type_id.default_timezone:
                event.date_tz = event.event_type_id.default_timezone
            if not event.date_tz:
                event.date_tz = self.env.user.tz or 'UTC'

    @api.depends("event_slot_ids")
    def _compute_event_slot_count(self):
        slot_count_per_event = dict(self.env['event.slot']._read_group(
            domain=[('event_id', 'in', self.ids)],
            groupby=['event_id'],
            aggregates=['__count']
        ))
        for event in self:
            event.event_slot_count = slot_count_per_event.get(event, 0)

    @api.depends('address_id')
    def _compute_address_search(self):
        for event in self:
            event.address_search = event.address_id

    def _search_address_search(self, operator, value):
        def make_codomain(value):
            return Domain.OR(
                Domain(field, 'ilike', value)
                for field in ('name', 'street', 'street2', 'city', 'zip', 'state_id', 'country_id')
            )
        if isinstance(value, Domain):
            domain = value.map_conditions(lambda cond: cond if cond.field_expr != 'display_name' else make_codomain(cond.value))
            return Domain('address_id', operator, domain)
        if operator == 'ilike' and isinstance(value, str):
            return Domain('address_id', 'any', make_codomain(value))
        # for the trivial "empty" case, there is no empty address
        if operator == 'in' and (not value or not any(value)):
            return Domain(False)
        return NotImplemented

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

    @api.depends('stage_id')
    def _compute_kanban_state(self):
        for task in self:
            if task.kanban_state != 'cancel':
                task.kanban_state = 'normal'

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

    @api.depends('address_id')
    def _compute_event_url(self):
        """Reset url field as it should only be used for events with no physical location."""
        self.filtered('address_id').event_url = ''

    @api.constrains("date_begin", "date_end", "event_slot_ids", "is_multi_slots")
    def _check_slots_dates(self):
        multi_slots_event_ids = self.filtered(lambda event: event.is_multi_slots).ids
        if not multi_slots_event_ids:
            return
        min_max_slot_dates_per_event = {
            event: (min_start, max_end)
            for event, min_start, max_end in self.env['event.slot']._read_group(
                domain=[('event_id', 'in', multi_slots_event_ids)],
                groupby=['event_id'],
                aggregates=['start_datetime:min', 'end_datetime:max']
            )
        }
        events_w_slots_outside_bounds = []
        for event, (min_start, max_end) in min_max_slot_dates_per_event.items():
            if (not (event.date_begin <= min_start <= event.date_end) or
                not (event.date_begin <= max_end <= event.date_end)):
                events_w_slots_outside_bounds.append(event)
        if events_w_slots_outside_bounds:
            raise ValidationError(_(
                "These events cannot have slots scheduled outside of their time range:\n%(event_names)s",
                event_names="\n".join(f"- {event.name}" for event in events_w_slots_outside_bounds)
            ))

    @api.constrains('date_begin', 'date_end')
    def _check_closing_date(self):
        for event in self:
            if event.date_end < event.date_begin:
                raise ValidationError(_('The closing date cannot be earlier than the beginning date.'))

    @api.constrains('event_url')
    def _check_event_url(self):
        for event in self.filtered('event_url'):
            url = urlparse(event.event_url)
            if not (url.scheme and url.netloc):
                raise ValidationError(_('Please enter a valid event URL.'))

    @api.onchange('event_url')
    def _onchange_event_url(self):
        """Correct the url by adding scheme if it is missing."""
        for event in self.filtered('event_url'):
            parsed_url = urlparse(event.event_url)
            if parsed_url.scheme not in ('http', 'https'):
                event.event_url = 'https://' + event.event_url

    @api.onchange('seats_max')
    def _onchange_seats_max(self):
        for event in self:
            if event.seats_limited and event.seats_max and event.seats_available <= 0 and \
                (event.event_slot_ids if event.is_multi_slots else True):
                return {
                    'warning': {
                        'title': _("Update the limit of registrations?"),
                        'message': _("There are more registrations than this limit, "
                                    "the event will be sold out and the extra registrations will remain."),
                    }
                }

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

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        if (message_operation == 'create' and self.env.user.has_group('event.group_event_registration_desk')):
            # allow the registration desk users to post messages on Event
            # can not be done with "_mail_post_access" otherwise public user will be
            # able to post on published Event (see website_event)
            return dict.fromkeys(self, 'read')
        return super()._mail_get_operation_for_mail_message_operation(message_operation)

    def _set_tz_context(self):
        self.ensure_one()
        return self.with_context(tz=self.date_tz or 'UTC')

    def _get_seats_availability(self, slot_tickets):
        """ Get availabilities for given combinations of slot / ticket. Returns
        a list following input order. None denotes no limit. """
        self.ensure_one()
        if not (all(len(item) == 2 for item in slot_tickets)):
            raise ValueError('Input should be a list of tuples containing slot, ticket')

        if any(slot for (slot, _ticket) in slot_tickets):
            slot_tickets_nb_registrations = {
                (slot.id, ticket.id): count
                for (slot, ticket, count) in self.env['event.registration'].sudo()._read_group(
                    domain=[('event_slot_id', '!=', False), ('event_id', 'in', self.ids),
                            ('state', 'in', ['open', 'done']), ('active', '=', True)],
                    groupby=['event_slot_id', 'event_ticket_id'],
                    aggregates=['__count']
                )
            }

        availabilities = []
        for slot, ticket in slot_tickets:
            available = None
            # event is constrained: max stands for either each slot, either global (no slots)
            if self.seats_limited and self.seats_max:
                if slot:
                    available = slot.seats_available
                else:
                    available = self.seats_available
            # ticket is constrained: max standard for either each slot / ticket, either global (no slots)
            if available != 0 and ticket and ticket.seats_max:
                if slot:
                    ticket_available = ticket.seats_max - slot_tickets_nb_registrations.get((slot.id, ticket.id), 0)
                else:
                    ticket_available = ticket.seats_available
                available = ticket_available if available is None else min(available, ticket_available)
            availabilities.append(available)
        return availabilities

    def _verify_seats_availability(self, slot_tickets):
        """ Check event seats availability, for combinations of slot / ticket.

        :param slot_tickets: a list of tuples(slot, ticket, count). Slot and
          ticket are optional, depending on event configuration. If count is 0
          it is a simple check current values do not overflow limit. If count
          is given, it serves as a check there are enough remaining seats.
        :raises ValidationError: if the event / slot / ticket do not have
          enough available seats
        """
        self.ensure_one()
        if not (all(len(item) == 3 for item in slot_tickets)):
            raise ValueError('Input should be a list of tuples containing slot, ticket, count')

        sold_out = []
        availabilities = self._get_seats_availability([(item[0], item[1]) for item in slot_tickets])
        for (slot, ticket, count), available in zip(slot_tickets, availabilities, strict=True):
            if available is None:  # unconstrained
                continue
            if available < count:
                if slot and ticket:
                    name = f'{ticket.name} - {slot.display_name}'
                elif slot:
                    name = slot.display_name
                elif ticket:
                    name = ticket.name
                else:
                    name = self.name
                sold_out.append((name, count - available))

        if sold_out:
            info = []  # note: somehow using list comprehension make translate.py crash in default lang
            for item in sold_out:
                info.append(_('%(slot_name)s: missing %(count)s seat(s)', slot_name=item[0], count=item[1]))
            raise ValidationError(
                _('There are not enough seats available for %(event_name)s:\n%(sold_out_info)s',
                  event_name=self.name,
                  sold_out_info='\n'.join(info),
                )
            )

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_set_done(self):
        """
        Action which will move the events
        into the first next (by sequence) stage defined as "Ended"
        (if they are not already in an ended stage)
        """
        first_ended_stage = self.env['event.stage'].search([('pipe_end', '=', True)], limit=1, order='sequence')
        if first_ended_stage:
            self.write({'stage_id': first_ended_stage.id})

    def _get_date_range_str(self, start_datetime=False, lang_code=False):
        self.ensure_one()
        datetime = start_datetime or self.date_begin
        today_tz = pytz.utc.localize(fields.Datetime.now()).astimezone(pytz.timezone(self.date_tz))
        event_date_tz = pytz.utc.localize(datetime).astimezone(pytz.timezone(self.date_tz))
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
        return _('on %(date)s', date=format_date(self.env, datetime, lang_code=lang_code, date_format='medium'))

    def _get_external_description(self):
        """
        Description of the event shortened to maximum 1900 characters to
        leave some space for addition by sub-modules.
        Meant to be used for external content (ics/icalc/Gcal).

        Reference Docs for URL limit -: https://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers
        """
        self.ensure_one()
        description = ''
        if self.event_share_url:
            description = f'<a href="{escape(self.event_share_url)}">{escape(self.name)}</a>\n'
        description += textwrap.shorten(html_to_inner_content(self.description), 1900)
        return description

    def _get_ics_file(self, slot=False):
        """ Returns iCalendar file for the event invitation.
            :param slot: If a slot is given, schedule with the given slot datetimes
            :returns a dict of .ics file content for each event
        """
        result = {}
        if not vobject:
            return result

        for event in self:
            cal = vobject.iCalendar()
            cal_event = cal.add('vevent')
            start = slot.start_datetime or event.date_begin
            end = slot.end_datetime or event.date_end

            cal_event.add('created').value = fields.Datetime.now().replace(tzinfo=pytz.timezone('UTC'))
            cal_event.add('dtstart').value = start.astimezone(pytz.timezone(event.date_tz))
            cal_event.add('dtend').value = end.astimezone(pytz.timezone(event.date_tz))
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
