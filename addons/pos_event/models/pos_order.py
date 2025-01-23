# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    attendee_count = fields.Integer('Attendee Count', compute='_compute_attendee_count')

    @api.depends('lines.event_registration_ids')
    def _compute_attendee_count(self):
        for order in self:
            order.attendee_count = len(order.lines.mapped('event_registration_ids'))

    def action_view_attendee_list(self):
        action = self.env["ir.actions.actions"]._for_xml_id("event.event_registration_action_tree")
        action['domain'] = [('pos_order_id', 'in', self.ids)]
        return action

    def read_for_pos(self, config_id, new_session = False, ui_orders=None):
        result = super().read_for_pos(config_id, new_session, ui_orders)
        paid_orders = self.filtered(lambda order: order.state in ['paid', 'invoiced'])

        if not paid_orders:
            return result

        lines_with_event = paid_orders.mapped('lines').filtered(lambda line: line.event_ticket_id)
        event_event_fields = self.env['event.event']._load_pos_data_fields(paid_orders[0].config_id.id)
        event_ticket_fields = self.env['event.event.ticket']._load_pos_data_fields(paid_orders[0].config_id.id)
        event_registrations_fields = self.env['event.registration']._load_pos_data_fields(paid_orders[0].config_id.id)
        event_registrations_answer_fields = self.env['event.registration.answer']._load_pos_data_fields(paid_orders[0].config_id.id)
        result['event.registration'] = lines_with_event.event_registration_ids.read(event_registrations_fields, load=False)
        result['event.event'] = lines_with_event.event_registration_ids.mapped('event_id').read(event_event_fields, load=False)
        result['event.event.ticket'] = lines_with_event.event_registration_ids.mapped('event_ticket_id').read(event_ticket_fields, load=False)
        result['event.registration.answer'] = lines_with_event.event_registration_ids.mapped('registration_answer_ids').read(event_registrations_answer_fields, load=False)

        for registration in lines_with_event.event_registration_ids:
            if registration.email:
                registration.action_send_badge_email()

        return result

    @api.model
    def _process_order(self, order, existing_order):
        res = super()._process_order(order, existing_order)
        refunded_line_ids = [line[2].get('refunded_orderline_id') for line in order.get('lines') if line[0] in [0, 1] and line[2].get('refunded_orderline_id')]
        refunded_orderlines = self.env['pos.order.line'].browse(refunded_line_ids)
        event_to_cancel = []

        for refunded_orderline in refunded_orderlines:
            if refunded_orderline.event_registration_ids:
                refund_qty = abs(sum(refunded_orderline.refund_orderline_ids.mapped('qty')))
                already_cancelled_qty = len(refunded_orderline.event_registration_ids.filtered(lambda r: r.state == 'cancel'))
                to_cancel_qty = refund_qty - already_cancelled_qty
                if to_cancel_qty > 0:
                    event_to_cancel += refunded_orderline.event_registration_ids.filtered(lambda registration: registration.state != 'cancel').ids[:int(to_cancel_qty)]

        if event_to_cancel:
            self.env['event.registration'].browse(event_to_cancel).write({'state': 'cancel'})

        return res
