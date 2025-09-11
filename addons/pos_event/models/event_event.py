from odoo import api, fields, models


class EventEvent(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'pos.load.mixin']

    image_1024 = fields.Image("PoS Image", max_width=1024, max_height=1024)
    pos_price_total = fields.Monetary('PoS Total (Tax Included)', compute='_compute_pos_price_total', groups='point_of_sale.group_pos_user')

    @api.depends('company_id.currency_id', 'registration_ids.pos_order_line_id.price_subtotal_incl',
                 'registration_ids.pos_order_line_id.currency_id', 'registration_ids.pos_order_line_id.order_id.state')
    def _compute_pos_price_total(self):
        """ Compute the total amount (tax included) of paid/posted PoS orders linked to the event. """
        totals = {event.id: 0.0 for event in self}
        event_subtotals = self.env['pos.order.line']._read_group(
            [('event_ticket_id.event_id', 'in', self.ids), ('order_id.state', 'in', ['paid', 'done'])],
            ['event_ticket_id.event_id', 'currency_id'],
            ['price_subtotal_incl:sum'],
        )

        for event, currency_id, sum_subtotal in event_subtotals:
            company = event.company_id or self.env.company
            totals[event.id] += event.currency_id._convert(sum_subtotal, currency_id, company)

        for event in self:
            event.pos_price_total = totals.get(event.id, 0.0)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('event_ticket_ids', 'in', [ticket['id'] for ticket in data['event.event.ticket']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'seats_available', 'event_ticket_ids', 'registration_ids', 'seats_limited', 'write_date',
                'question_ids', 'general_question_ids', 'specific_question_ids', 'seats_max',
                'is_multi_slots', 'event_slot_ids']

    def get_slot_tickets_availability_pos(self, slot_ticket_ids):
        self.ensure_one()
        slot_tickets = [
            (
                self.event_slot_ids.filtered(lambda slot: slot.id == slot_id) if slot_id else self.env['event.slot'],
                self.event_ticket_ids.filtered(lambda ticket: ticket.id == ticket_id) if ticket_id else self.env['event.event.ticket']
            )
            for slot_id, ticket_id in slot_ticket_ids
        ]
        return self._get_seats_availability(slot_tickets)

    def action_view_linked_pos_orders(self):
        """ Redirects to the Paid/Posted PoS Orders linked to the current event records. """
        pos_order_action = self.env["ir.actions.actions"]._for_xml_id("point_of_sale.action_pos_pos_form")
        pos_order_action['domain'] = [('state', 'in', ['paid', 'done']), ('lines.event_ticket_id.event_id', 'in', self.ids)]
        return pos_order_action
