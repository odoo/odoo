# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from datetime import timedelta


class CalendarEvent(models.Model):
    _name = 'calendar.event'
    _inherit = ["calendar.event", "pos.load.mixin"]

    answers = fields.Char('Q&A answers', compute='_get_answers')

    def _get_answers(self):
        for record in self:
            record.answers = (', ').join([answer.value_text_box or answer.value_answer_id.name for answer in record.appointment_answer_input_ids.sorted('id')])

    @api.model
    def _load_pos_data_domain(self, data):
        now = fields.Datetime.now()
        dayAfter = fields.Date.today() + timedelta(days=1)
        appointment_type_id = [config['appointment_type_id'] for config in data['pos.config']['data']]
        return [
            ('booking_line_ids.appointment_resource_id', 'in', [table['appointment_resource_id'] for table in data['restaurant.table']['data']]),
            ('appointment_type_id', 'in', appointment_type_id),
            '|', '&', ('start', '>=', now), ('start', '<=', dayAfter), '&', ('stop', '>=', now), ('stop', '<=', dayAfter),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return self.env['calendar.event']._fields_for_restaurant_table()

    @api.model
    def _fields_for_restaurant_table(self):
        return ['id', 'start', 'duration', 'stop', 'name', 'appointment_type_id', 'appointment_status', 'appointment_resource_ids', 'resource_total_capacity_reserved']

    @api.model
    def _send_table_notifications(self, events, command):
        today = fields.Date.today()
        fields_to_read = self._fields_for_restaurant_table()

        for event in events:
            # Don't include the event if it's not for today
            if event.start.date() != today:
                continue

            event_dict = event.read(fields_to_read, load=False)[0]
            event_appointment_type_id = event_dict.get('appointment_type_id')
            # tables that are booked for this event
            event_table_ids = event.booking_line_ids.appointment_resource_id.sudo().pos_table_ids
            for table in event_table_ids:
                for config in table.floor_id.pos_config_ids:
                    session = config.current_session_id

                    if (
                        session
                        and config.appointment_type_id
                        and config.appointment_type_id.id == event_appointment_type_id
                    ):
                        config._notify(("TABLE_BOOKING", {
                            "command": command,
                            "event": event_dict,
                        }))

    def action_open_booking_gantt_view(self):
        return {
            'name': 'Manage Bookings',
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            "views": [(self.env.ref("pos_restaurant_appointment.calendar_event_view_gantt_booking_resource_inherited").id, "gantt")],
            'target': 'current',
            'context': {
                'appointment_booking_gantt_show_all_resources': True,
                'active_model': 'appointment.type',
                'default_partner_ids': [],
                "search_default_appointment_type_id": self._context.get("appointment_type_id"),
            }
        }

    def action_open_booking_form_view(self):
        return {
            'name': 'Edit Booking',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'views': [(self.env.ref('pos_restaurant_appointment.calendar_event_view_form_gantt_booking_inherit').id, 'form')],
            'res_id': self.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        new_events = super().create(vals_list)
        self._send_table_notifications(new_events, "ADDED")
        return new_events

    def write(self, vals):
        self._send_table_notifications(self, "REMOVED")
        result = super().write(vals)
        self._send_table_notifications(self, "ADDED")
        return result

    def unlink(self):
        self._send_table_notifications(self, "REMOVED")
        return super().unlink()
