from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.stock.models.stock_picking_type import GroupingCriterion

_debug = DebugLog(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _default_weight_uom_name(self):
        return self.env[
            "product.template"
        ]._get_weight_uom_name_from_ir_config_parameter()

    batch_group_by_carrier = fields.Boolean(
        string="Carrier",
        help="Automatically group batches by carriers",
    )
    batch_max_weight = fields.Integer(
        string="Maximum weight",
        help="A transfer will not be automatically added to batches that will exceed this weight if the transfer is added to it.\n"
        "Leave this value as '0' if no weight limit.",
    )
    weight_uom_name = fields.Char(
        string="Weight unit of measure label",
        compute="_compute_weight_uom_name",
        default=_default_weight_uom_name,
        readonly=True,
    )

    def _compute_weight_uom_name(self):
        for picking_type in self:
            picking_type.weight_uom_name = self.env[
                "product.template"
            ]._get_weight_uom_name_from_ir_config_parameter()

    @api.model
    def _get_batch_grouping_criteria(self):
        _debug.logic("batch_grouping_criteria", picking_types=self)
        criteria = super()._get_batch_grouping_criteria()
        criteria["batch_group_by_carrier"] = GroupingCriterion(
            "picking_id.carrier_id", "name", "carrier_id", "wave_carrier_id"
        )
        return criteria

    @api.constrains("batch_max_weight")
    def _check_batch_max_weight(self):
        _debug.logic("batch_max_weight_check", picking_types=self)
        for picking_type in self:
            if picking_type.batch_max_weight < 0:
                raise ValidationError(
                    _(
                        "The maximum batch weight cannot be negative. Leave it at '0' to disable the limit."
                    )
                )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_auto_merge_amounts(self):
        _debug.logic("picking_auto_merge_amounts", pickings=self)
        amounts = super()._get_auto_merge_amounts()
        amounts["weight"] = self.weight
        return amounts

    def _is_auto_batchable(self, picking=None):
        _debug.logic("picking_auto_batchable", pickings=self)
        res = super()._is_auto_batchable(picking)
        if not picking:
            picking = self.env["stock.picking"]
        if self.picking_type_id.batch_max_weight:
            res = res and (
                self.weight + picking.weight <= self.picking_type_id.batch_max_weight
            )
        return res
