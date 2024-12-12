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
    def print_event_tickets(self):
        return self.env.ref('event.action_report_event_registration_full_page_ticket').report_action(self.lines.event_registration_ids)

    def print_event_badges(self):
        return self.env.ref('event.action_report_event_registration_badge').report_action(self.lines.event_registration_ids)
