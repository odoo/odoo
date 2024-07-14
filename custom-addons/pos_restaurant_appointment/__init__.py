# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def _pos_restaurant_appointment_after_init(env):
    table_ids = env['restaurant.table'].search([('appointment_resource_id', '=', False)])
    for table_id in table_ids:
        table_id.appointment_resource_id = table_id.env['appointment.resource'].sudo().create({
            'name': f'{table_id.floor_id.name} - {table_id.name}',
            'capacity': table_id.seats,
            'pos_table_ids': table_id,
        })
