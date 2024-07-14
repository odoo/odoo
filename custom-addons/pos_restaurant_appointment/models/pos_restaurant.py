# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import api, fields, models
from datetime import timedelta

class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    appointment_resource_id = fields.Many2one('appointment.resource', string='Appointment resource')

    def _get_appointments(self):
        appointments_by_table_id = defaultdict(dict)
        now = fields.Datetime.now()
        today = fields.Date.today()
        appointments = self.env['calendar.event'].search([
            ('booking_line_ids.appointment_resource_id', 'in', self.appointment_resource_id.ids),
            ('appointment_type_id', 'in', self.floor_id.pos_config_ids.appointment_type_ids.ids),
            ('start', '>=', now), ('stop', '<=', today),
        ])

        fields_to_read = self.env['calendar.event']._fields_for_restaurant_table()
        for appointment in appointments:
            appointment_dict = appointment.read(fields_to_read)[0]
            for table in appointment.booking_line_ids.appointment_resource_id.sudo().pos_table_ids:
                appointments_by_table_id[table.id][appointment.id] = appointment_dict

        return dict(appointments_by_table_id)


    @api.model_create_multi
    def create(self, vals_list):
        tables = super().create(vals_list)

        for table in tables:
            if not table.appointment_resource_id:
                table.appointment_resource_id = table.env['appointment.resource'].sudo().create({
                    'name': f'{table.floor_id.name} - {table.name}',
                    'capacity': table.seats,
                    'pos_table_ids': table,
                })

        return tables

    def write(self, vals):
        table = super().write(vals)

        if not self.active:
            self.appointment_resource_id.sudo().active = False
        else:
            if self.appointment_resource_id:
                self.appointment_resource_id.sudo().write({
                    'name': f'{self.floor_id.name} - {self.name}',
                    'capacity': self.seats,
                })

        return table

    def unlink(self):
        for table in self:
            table.appointment_resource_id.sudo().unlink()

        return super().unlink()

    @api.ondelete(at_uninstall=True)
    def _delete_linked_resources(self):
        for table in self:
            table.appointment_resource_id.unlink()
