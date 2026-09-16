from odoo import _, api, fields, models
from odoo.tools import format_list


class ProductTemplate(models.Model):
    _inherit = "product.template"

    weight_capacity = fields.Float(string="Max Weight")
    weight_capacity_uom_name = fields.Char(
        string="Weight unit of measure label",
        compute="_compute_weight_capacity_uom_name",
    )
    volume_capacity = fields.Float(string="Max Volume")
    volume_capacity_uom_name = fields.Char(
        string="Volume unit of measure label",
        compute="_compute_volume_capacity_uom_name",
    )

    def _compute_weight_capacity_uom_name(self):
        self.weight_capacity_uom_name = (
            self._get_weight_uom_name_from_ir_config_parameter()
        )

    def _compute_volume_capacity_uom_name(self):
        self.volume_capacity_uom_name = (
            self._get_volume_uom_name_from_ir_config_parameter()
        )


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.depends_context("show_load_capacity")
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("show_load_capacity"):
            return
        for product in self:
            capacities = []
            if product.weight_capacity:
                capacities.append(
                    _(
                        "%(weight_capacity)s %(weight_uom)s",
                        weight_capacity=product.weight_capacity,
                        weight_uom=product.weight_capacity_uom_name,
                    )
                )
            if product.volume_capacity:
                capacities.append(
                    _(
                        "%(volume_capacity)s %(volume_uom)s",
                        volume_capacity=product.volume_capacity,
                        volume_uom=product.volume_capacity_uom_name,
                    )
                )
            if capacities:
                product.display_name = _(
                    "%(display_name)s (%(load_capacity)s)",
                    display_name=product.display_name,
                    load_capacity=format_list(self.env, capacities, "unit-short"),
                )
