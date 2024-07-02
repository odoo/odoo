# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicleModelCategory(models.Model):
    _inherit = 'fleet.vehicle.model.category'

    max_weight = fields.Float(string="Max Weight (Kg)")
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    max_volume = fields.Float(string="Max Volume (m³)")
    volume_uom_name = fields.Char(string='Volume unit of measure label', compute='_compute_volume_uom_name')

    def _compute_display_name(self):
        for record in self:
            max_weight = record.max_weight
            max_volume = record.max_volume
            max_weight_str = f"{max_weight}{record.weight_uom_name}, " if max_weight else 'f"0 {record.weight_uom_name}", '
            max_volume_str = f"{max_volume}{record.volume_uom_name}" if max_volume else 'f"0 {record.volume_uom_name}"'
            record.display_name = f"{record.name} ({max_weight_str}{max_volume_str})" if max_weight or max_volume else record.name

    def _compute_weight_uom_name(self):
        for category in self:
            category.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_volume_uom_name(self):
        for category in self:
            category.volume_uom_name = self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()
