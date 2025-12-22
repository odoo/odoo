# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.tools import format_list


class FleetVehicleModelCategory(models.Model):
    _inherit = 'fleet.vehicle.model.category'

    weight_capacity = fields.Float(string="Max Weight")
    weight_capacity_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_capacity_uom_name')
    volume_capacity = fields.Float(string="Max Volume")
    volume_capacity_uom_name = fields.Char(string='Volume unit of measure label', compute='_compute_volume_capacity_uom_name')

    def _compute_display_name(self):
        super()._compute_display_name()
        for record in self:
            additional_info = []
            if record.weight_capacity:
                additional_info.append(_("%(weight_capacity)s %(weight_uom)s", weight_capacity=record.weight_capacity, weight_uom=record.weight_capacity_uom_name))
            if record.volume_capacity:
                additional_info.append(_("%(volume_capacity)s %(volume_uom)s", volume_capacity=record.volume_capacity, volume_uom=record.volume_capacity_uom_name))
            if additional_info:
                additional_info = format_list(self.env, additional_info, "unit-short")
                record.display_name = _("%(display_name)s (%(load_capacity)s)", display_name=record.display_name, load_capacity=additional_info)

    def _compute_weight_capacity_uom_name(self):
        self.weight_capacity_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_volume_capacity_uom_name(self):
        self.volume_capacity_uom_name = self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()
