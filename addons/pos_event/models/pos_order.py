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

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        event_registration_ids = self.lines.filtered('event_registration_ids').event_registration_ids
        event_registration_ids.action_confirm()

        return res


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    event_id = fields.Many2one('event.event', string='Event', compute="_compute_event_id", store=True, precompute=True)
    event_ticket_id = fields.Many2one('event.event.ticket', string='Event Ticket')
    event_registration_ids = fields.One2many('event.registration', 'pos_order_line_id', string='Event Registrations')

    @api.depends('event_registration_ids')
    def _compute_event_id(self):
        for line in self:
            line.event_id = line.event_registration_ids.event_id
