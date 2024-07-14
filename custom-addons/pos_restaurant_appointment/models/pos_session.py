# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_restaurant_floor(self, params):
        floors = super()._get_pos_ui_restaurant_floor(params)

        # optimize get_appointments to work in batch
        tables = [table for floor in floors for table in floor.get('tables', []) if table.get('id')]
        tables_ids = [table.get('id') for table in tables]

        table_prefetch = self.env['restaurant.table'].with_prefetch(tables_ids)
        tables_appointments = table_prefetch.browse(tables_ids)._get_appointments()
        for table in tables:
            table['appointment_ids'] = tables_appointments.get(table['id']) or {}

        return floors
