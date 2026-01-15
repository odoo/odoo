from odoo import api, fields, models, _


class EventTypeTicket(models.Model):
    _name = 'event.type.ticket'
    _description = 'Event Template Ticket'
    _order = 'sequence, name, id'

    sequence = fields.Integer('Sequence', default=10)
    # description
    name = fields.Char(
        string='Name', default=lambda self: _('Registration'),
        required=True, translate=True)
    description = fields.Text(
        'Description', translate=True,
        help="A description of the ticket that you want to communicate to your customers.")
    event_type_id = fields.Many2one(
        'event.type', string='Event Category', ondelete='cascade', required=True)
    # seats
    seats_limited = fields.Boolean(string='Limit Attendees', readonly=True, store=True,
                                   compute='_compute_seats_limited')
    seats_max = fields.Integer(
        string='Maximum Attendees',
        help="Define the number of available tickets. If you have too many registrations you will "
             "not be able to sell tickets anymore. Set 0 to ignore this rule set as unlimited.")

    @api.depends('seats_max')
    def _compute_seats_limited(self):
        for ticket in self:
            ticket.seats_limited = ticket.seats_max

    @api.model
    def _get_event_ticket_fields_whitelist(self):
        """ Whitelist of fields that are copied from event_type_ticket_ids to event_ticket_ids when
        changing the event_type_id field of event.event """
        return ['sequence', 'name', 'description', 'seats_max']
