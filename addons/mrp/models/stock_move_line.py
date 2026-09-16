from odoo import api, fields, models
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    workorder_id = fields.Many2one(
        comodel_name="mrp.workorder",
        string="Work Order",
        index="btree_not_null",
        check_company=True,
    )
    production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Production Order",
        check_company=True,
    )

    @api.depends("production_id.picking_type_id")
    def _compute_picking_type_id(self):
        own_production = self.filtered("production_id")
        for line in own_production:
            line.picking_type_id = line.production_id.picking_type_id
        return super(StockMoveLine, self - own_production)._compute_picking_type_id()

    def _search_picking_type_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        domain = super()._search_picking_type_id(operator, value)
        return (Domain("production_id", "=", False) & domain) | Domain(
            "production_id.picking_type_id", operator, value
        )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if self.env.context.get("force_manual_consumption"):
            for move in res.move_id:
                move.picked = True
                lines = res.filtered(lambda line, move=move: line.move_id == move)
                if not any(lines.mapped("quantity")):
                    continue
                if move._is_quantity_edited(
                    move.product_uom_qty, move.quantity, move.product_uom_id
                ):
                    move.manual_consumption = True
        _debug.lifecycle(
            "create",
            lines=res,
            forced=bool(self.env.context.get("force_manual_consumption")),
        )
        for line in res:
            if line.move_id.raw_material_production_id and line.state == "done":
                mo = line.move_id.raw_material_production_id
                finished_lots = mo.lot_producing_ids
                finished_lots |= mo.move_finished_ids.filtered(
                    lambda m, mo=mo: m.product_id != mo.product_id
                ).move_line_ids.lot_id
                _debug.logic(
                    "consume_line_traced",
                    line=line.id,
                    production=mo.id,
                    by="finished_lots" if finished_lots else "all_finished_lines",
                )
                produced_move_lines = mo.move_finished_ids.move_line_ids
                if finished_lots:
                    produced_move_lines = produced_move_lines.filtered(
                        lambda sml, finished_lots=finished_lots: (
                            sml.lot_id in finished_lots
                        )
                    )
                line.produce_line_ids = [Command.set(produced_move_lines.ids)]
        return res

    def _get_similar_move_lines(self):
        lines = super()._get_similar_move_lines()
        if self.move_id.production_id:
            finished_moves = self.move_id.production_id.move_finished_ids
            finished_move_lines = finished_moves.mapped("move_line_ids")
            lines |= finished_move_lines.filtered(
                lambda ml: (
                    ml.product_id == self.product_id and (ml.lot_id or ml.lot_name)
                )
            )
        if self.move_id.raw_material_production_id:
            raw_moves = self.move_id.raw_material_production_id.move_raw_ids
            raw_moves_lines = raw_moves.mapped("move_line_ids")
            lines |= raw_moves_lines.filtered(
                lambda ml: (
                    ml.product_id == self.product_id and (ml.lot_id or ml.lot_name)
                )
            )
        return lines

    def write(self, vals):
        for move_line in self:
            production = (
                move_line.move_id.production_id
                or move_line.move_id.raw_material_production_id
            )
            if (
                production
                and move_line.state == "done"
                and any(
                    field in vals for field in ("lot_id", "location_id", "quantity")
                )
            ):
                move_line._log_message(
                    production, move_line, "mrp.track_production_move_template", vals
                )
        return super().write(vals)

    def _get_aggregated_properties(self, move_line=False, move=False):
        aggregated_properties = super()._get_aggregated_properties(move_line, move)
        bom = aggregated_properties["move"].bom_line_id.bom_id
        aggregated_properties["bom"] = bom or False
        aggregated_properties["line_key"] += f"_{bom.id if bom else ''}"
        return aggregated_properties

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        kit_name = kwargs.get("kit_name")

        to_be_removed = []
        for aggregated_move_line in aggregated_move_lines:
            bom = aggregated_move_lines[aggregated_move_line]["bom"]
            is_phantom = bom.type == "phantom" if bom else False
            if kit_name:
                product = bom.product_id or bom.product_tmpl_id if bom else False
                display_name = product.display_name if product else False
                description = aggregated_move_lines[aggregated_move_line]["description"]
                if not is_phantom or display_name != kit_name:
                    to_be_removed.append(aggregated_move_line)
                elif description == kit_name:
                    aggregated_move_lines[aggregated_move_line]["description"] = ""
            elif not kwargs and is_phantom:
                to_be_removed.append(aggregated_move_line)

        for move_line in to_be_removed:
            del aggregated_move_lines[move_line]

        return aggregated_move_lines

    def _prepare_stock_move_vals(self):
        move_vals = super()._prepare_stock_move_vals()
        if self.env["product.product"].browse(move_vals["product_id"]).is_kit:
            move_vals["location_id"] = self.location_id.id
            move_vals["location_dest_id"] = self.location_dest_id.id
        return move_vals

    def _get_linkable_moves(self):
        self.check_singleton()
        if self.product_id and self.product_id.is_kit:
            moves = self.picking_id.move_ids.filtered(
                lambda move: (
                    move.product_id == self.product_id
                    and move.location_id == self.location_id
                    and move.location_dest_id == self.location_dest_id
                )
            )
            return sorted(moves, key=lambda m: m.quantity < m.product_qty, reverse=True)
        else:
            return super()._get_linkable_moves()

    def _has_lot_context(self):
        return (
            self.move_id.unbuild_id
            and not self.move_id.origin_returned_move_id.move_line_ids.lot_id
        ) or super()._has_lot_context()
