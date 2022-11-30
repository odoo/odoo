from odoo import models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # event_id = fields.Many2one(
    #     'event.event', string='Event',
    #     compute="_compute_event_id", store=True, readonly=False, precompute=True,
    #     help="Choose an event and it will automatically create a registration for this event.")
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket')
