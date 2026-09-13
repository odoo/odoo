from odoo import api, fields, models

from odoo.addons.base.models.res_partner import _selection_timezones


class EventType(models.Model):
    _name = "event.type"
    _description = "Event Template"
    _order = "sequence, id"

    def _default_event_type_mail_ids(self):
        return [
            (
                0,
                0,
                {
                    "interval_nbr": 0,
                    "interval_unit": "now",
                    "interval_type": "after_sub",
                    "template_ref": "mail.template, %i"
                    % self.env.ref("event.event_subscription").id,
                },
            ),
            (
                0,
                0,
                {
                    "interval_nbr": 1,
                    "interval_unit": "hour",
                    "interval_type": "before_event",
                    "template_ref": "mail.template, %i"
                    % self.env.ref("event.event_reminder").id,
                },
            ),
            (
                0,
                0,
                {
                    "interval_nbr": 3,
                    "interval_unit": "day",
                    "interval_type": "before_event",
                    "template_ref": "mail.template, %i"
                    % self.env.ref("event.event_reminder").id,
                },
            ),
        ]

    def _default_question_ids(self):
        return (
            self.env["event.question"]
            .search([("is_default", "=", True), ("active", "=", True)])
            .ids
        )

    name = fields.Char(
        string="Event Template",
        translate=True,
        required=True,
    )
    note = fields.Html()
    sequence = fields.Integer(default=10)
    # tickets
    event_type_ticket_ids = fields.One2many(
        comodel_name="event.type.ticket",
        inverse_name="event_type_id",
        string="Tickets",
    )
    tag_ids = fields.Many2many(
        comodel_name="event.tag",
        string="Tags",
    )
    # registration
    has_seats_limitation = fields.Boolean(string="Limited Seats")
    seats_max = fields.Integer(
        string="Maximum Registrations",
        compute="_compute_seats_max",
        store=True,
        readonly=False,
        help="It will select this default maximum value when you choose this event",
    )
    default_timezone = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        default=lambda self: self.env.user.tz or "UTC",
    )
    # communication
    event_type_mail_ids = fields.One2many(
        comodel_name="event.type.mail",
        inverse_name="event_type_id",
        string="Mail Schedule",
        default=_default_event_type_mail_ids,
    )
    # ticket reports
    ticket_instructions = fields.Html(
        translate=True,
        help="This information will be printed on your tickets.",
    )
    question_ids = fields.Many2many(
        comodel_name="event.question",
        string="Questions",
        default=_default_question_ids,
        copy=True,
    )

    @api.depends("has_seats_limitation")
    def _compute_seats_max(self):
        for template in self:
            if not template.has_seats_limitation:
                template.seats_max = 0
