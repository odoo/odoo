# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicleModelCategory(models.Model):
    _inherit = 'fleet.vehicle.model.category'

    max_weight = fields.Float(string="Max Weight (Kg)")
    max_volume = fields.Float(string="Max Volume (m³)")

    def _compute_display_name(self):
        for record in self:
            max_weight = record.max_weight
            max_volume = record.max_volume
            max_weight_str = f"{max_weight}kg, " if max_weight else "0kg, "
            max_volume_str = f"{max_volume}m³" if max_volume else "0m³"
            record.display_name = f"{record.name} ({max_weight_str}{max_volume_str})" if max_weight or max_volume else record.name
