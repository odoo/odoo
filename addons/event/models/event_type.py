from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get


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
        return self.env['event.question'].search([('is_default', '=', True), ('active', '=', True)]).ids

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
    question_ids = fields.Many2many(
        'event.question', default=_default_question_ids,
        string='Questions', copy=True)

    @api.depends('has_seats_limitation')
    def _compute_seats_max(self):
        for template in self:
            if not template.has_seats_limitation:
                template.seats_max = 0
