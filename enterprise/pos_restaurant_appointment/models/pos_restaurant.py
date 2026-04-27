# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    appointment_resource_id = fields.Many2one('appointment.resource', string='Appointment resource')

    @api.model
    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        data += ['appointment_resource_id']
        return data

    @api.model_create_multi
    def create(self, vals_list):
        tables = super().create(vals_list)

        for table in tables:
            if not table.appointment_resource_id:
                table.appointment_resource_id = table.env['appointment.resource'].sudo().create({
                    'name': f'{table.floor_id.name} - {table.table_number}',
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
                    'name': f'{self.floor_id.name} - {self.table_number}',
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
