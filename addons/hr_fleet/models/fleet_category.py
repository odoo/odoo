# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class FleetCategory(models.Model):
    _inherit = 'fleet.category'

    internal = fields.Boolean(default=True)

    def action_view_vehicles(self):
        res = super().action_view_vehicles()
        res['context']['internal'] = self.internal
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'internal' in vals and not vals['internal']:
            self.vehicle_ids.write({
                'driver_employee_id': False,
                'future_driver_employee_id': False,
            })
        return res
