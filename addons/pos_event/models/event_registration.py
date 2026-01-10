# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class EventRegistration(models.Model):
    _name = 'event.registration'
    _inherit = ['event.registration', 'pos.load.mixin']

    pos_order_id = fields.Many2one(related='pos_order_line_id.order_id', string='PoS Order')
    pos_order_line_id = fields.Many2one('pos.order.line', string='PoS Order Line', ondelete='cascade', copy=False)

    @api.model
    def _load_pos_data_domain(self, data):
        return False

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'event_id', 'event_ticket_id', 'pos_order_line_id', 'pos_order_id', 'phone', 'email', 'name',
                'company_name', 'registration_answer_ids', 'registration_answer_choice_ids', 'write_date']

    @api.model_create_multi
    def create(self, vals_list):
        self._populate_creation_vals(vals_list)
        result = super().create(vals_list)
        result._update_available_seat()
        return result

    def write(self, vals):
        result = super().write(vals)
        self._update_available_seat()
        return result

    def _populate_creation_vals(self, vals_list):
        for vals in vals_list:
            if 'pos_order_line_id' in vals:
                if 'partner_id' not in vals:
                    pol = self.env['pos.order.line'].browse(vals['pos_order_line_id']).exists()
                    if pol and pol.order_id.partner_id:
                        vals['partner_id'] = pol.order_id.partner_id.id
                for field in ["name", "email", "phone", "company_name"]:
                    if field in vals and not vals[field]:
                        vals.pop(field)

    def _update_available_seat(self):
        # Here sudo is used in order for pos_event to update the available seats to all open pos session when a ticket is sold in website for example
        session_ids = self.env['pos.session'].sudo().search([("state", "!=", "closed")])
        if len(session_ids) > 0:
            session_ids.config_id._update_events_seats(self.event_id)
