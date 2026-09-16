from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpConsumptionWarning(models.TransientModel):
    _name = "mrp.consumption.warning"
    _description = "Wizard in case of consumption in warning/strict and more component has been used for a MO (related to the bom)"

    mrp_production_ids = fields.Many2many(comodel_name="mrp.production")
    mrp_production_count = fields.Count(count_of="mrp_production_ids")

    consumption = fields.Selection(
        selection=[
            ("flexible", "Allowed"),
            ("warning", "Allowed with warning"),
            ("strict", "Blocked"),
        ],
        compute="_compute_consumption",
    )
    mrp_consumption_warning_line_ids = fields.One2many(
        comodel_name="mrp.consumption.warning.line",
        inverse_name="mrp_consumption_warning_id",
    )

    @api.depends("mrp_consumption_warning_line_ids.consumption")
    def _compute_consumption(self):
        for wizard in self:
            consumption_map = set(
                wizard.mrp_consumption_warning_line_ids.mapped("consumption")
            )
            wizard.consumption = (
                ("strict" in consumption_map and "strict")
                or ("warning" in consumption_map and "warning")
                or "flexible"
            )

    def action_confirm(self):
        ctx = dict(self.env.context)
        ctx.pop("default_mrp_production_ids", None)
        _debug.logic(
            "consumption_warning_confirmed",
            productions=self.mrp_production_ids,
            consumption=self.consumption,
            lines=len(self.mrp_consumption_warning_line_ids),
        )
        return self.mrp_production_ids.with_context(
            ctx, skip_consumption=True
        ).button_mark_done()

    def action_set_qty(self):
        missing_move_vals = []
        lines_by_production = self.mrp_consumption_warning_line_ids.grouped(
            "mrp_production_id"
        )
        for production in self.mrp_production_ids:
            moves_by_product = production.move_raw_ids.grouped("product_id")
            for line in lines_by_production.get(production, self.browse()):
                matching = moves_by_product.get(line.product_id)
                if not matching:
                    missing_move_vals.append(
                        {
                            "product_id": line.product_id.id,
                            "product_uom_id": line.product_uom_id.id,
                            "product_uom_qty": line.product_expected_qty_uom,
                            "quantity": line.product_expected_qty_uom,
                            "raw_material_production_id": line.mrp_production_id.id,
                            "additional": True,
                            "picked": True,
                        }
                    )
                    continue
                first, rest = matching[0], matching[1:]
                qty_expected = line.product_uom_id._get_quantity_in_unit(
                    line.product_expected_qty_uom, first.product_uom_id
                )
                if first.product_uom_id.compare(qty_expected, first.quantity) != 0:
                    first.quantity = qty_expected
                for other in rest:
                    if not other.product_uom_id.is_zero(other.quantity):
                        other.quantity = 0
                matching.picked = True
                line.product_expected_qty_uom = 0
        _debug.pipeline(
            "consumption_warning_qty_set",
            productions=self.mrp_production_ids,
            created=len(missing_move_vals),
        )
        if missing_move_vals:
            self.env["stock.move"].create(missing_move_vals)
        return self.action_confirm()

    def action_cancel(self):
        if self.env.context.get("from_workorder") and len(self.mrp_production_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "mrp.production",
                "views": [[self.env.ref("mrp.mrp_production_form_view").id, "form"]],
                "res_id": self.mrp_production_ids.id,
                "target": "main",
            }
        return None


class MrpConsumptionWarningLine(models.TransientModel):
    _name = "mrp.consumption.warning.line"
    _description = "Line of issue consumption"

    mrp_consumption_warning_id = fields.Many2one(
        comodel_name="mrp.consumption.warning",
        string="Parent Wizard",
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    mrp_production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Manufacturing Order",
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    consumption = fields.Selection(related="mrp_production_id.consumption")

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
        required=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        string="Unit",
        readonly=True,
    )
    product_consumed_qty_uom = fields.Float(
        string="Consumed",
        readonly=True,
    )
    product_expected_qty_uom = fields.Float(
        string="To Consume",
        readonly=True,
    )
