# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _name = 'event.registration'
    _inherit = ['event.registration', 'pos.load.mixin']

    pos_order_id = fields.Many2one(related='pos_order_line_id.order_id', string='PoS Order')
    pos_order_line_id = fields.Many2one('pos.order.line', string='PoS Order Line', ondelete='cascade', copy=False, index='btree_not_null')

    def _has_order(self):
        return super()._has_order() or self.pos_order_id

    @api.depends('pos_order_id.state', 'pos_order_id.currency_id', 'pos_order_id.amount_total')
    def _compute_registration_status(self):
        if self.pos_order_id:
            for registration in self:
                if registration.pos_order_id.state == 'cancel':
                    registration.state = 'cancel'
                elif float_is_zero(registration.pos_order_id.amount_total, precision_rounding=registration.pos_order_id.currency_id.rounding):
                    registration.sale_status = 'free'
                    registration.state = 'open'
                else:
                    registration.sale_status = 'sold'
                    registration.state = 'open'

        super()._compute_registration_status()

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'event_id', 'event_ticket_id', 'event_slot_id', 'pos_order_line_id', 'pos_order_id', 'phone',
                'company_name', 'email', 'name', 'registration_answer_ids', 'registration_answer_choice_ids', 'write_date']

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        result._update_available_seat()
        return result

    def write(self, vals):
        result = super().write(vals)
        self._update_available_seat()
        return result

    def _update_available_seat(self):
        # Here sudo is used in order for pos_event to update the available seats to all open pos session when a ticket is sold in website for example
        session_ids = self.env['pos.session'].sudo().search([("state", "!=", "closed")])
        if len(session_ids) > 0:
            session_ids.config_id._update_events_seats(self.event_id)

    def action_view_pos_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("point_of_sale.action_pos_pos_form")
        action['views'] = [(False, 'form')]
        action['res_id'] = self.pos_order_id.id
        return action
