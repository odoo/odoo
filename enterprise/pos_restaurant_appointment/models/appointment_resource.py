# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api

class AppointmentResource(models.Model):
    _name = 'appointment.resource'
    _inherit = ['appointment.resource', 'pos.load.mixin']

    # this should be one2one
    pos_table_ids = fields.One2many('restaurant.table', 'appointment_resource_id', string='POS Table')

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_table_ids', 'in', [table['id'] for table in data['restaurant.table']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['pos_table_ids']
