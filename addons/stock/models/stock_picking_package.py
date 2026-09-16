from collections import defaultdict

from odoo import api, models
from odoo.tools.misc import clean_context

from ..tools import debug_log as dbg
from .stock_picking import DONE_CANCEL_STATES


class StockPickingPackage(models.Model):
    _inherit = "stock.picking"

    @api.depends("state", "move_line_ids.result_package_id", "package_history_ids")
    def _compute_count_packages(self):
        done_pickings = self.filtered(lambda picking: picking.state == "done")
        other_pickings = self - done_pickings

        packages_by_pick = defaultdict(int)
        packages = self.env["stock.package"].search(
            [("picking_ids", "in", other_pickings.ids)],
        )
        for pack in packages:
            for picking in pack.picking_ids:
                packages_by_pick[picking] += 1

        histories_by_pick = self.env["stock.package.history"]._read_group(
            [("picking_ids", "in", done_pickings.ids)],
            ["picking_ids"],
            ["__count"],
        )
        histories_by_pick = dict(histories_by_pick)

        for picking in done_pickings:
            picking.count_packages = histories_by_pick.get(picking, 0)
        for picking in other_pickings:
            picking.count_packages = packages_by_pick.get(picking, 0)

    @api.depends(
        "move_line_ids",
        "move_line_ids.result_package_id",
        "move_line_ids.product_uom_id",
        "move_line_ids.quantity",
        "move_line_ids.product_id.weight",
    )
    def _compute_weight_bulk(self):
        weights = self._get_total_by_picking(
            [("result_package_id", "=", False)],
            "weight",
            "move_line_ids",
        )
        for picking in self:
            picking.weight_bulk = weights[picking.id]

    @api.depends(
        "move_line_ids.result_package_id",
        "move_line_ids.result_package_id.package_type_id",
        "move_line_ids.result_package_id.shipping_weight",
        "move_line_ids.result_package_id.outermost_package_id",
        "move_line_ids.result_package_id.outermost_package_id.package_type_id",
        "move_line_ids.result_package_id.outermost_package_id.shipping_weight",
        "weight_bulk",
    )
    def _compute_shipping_weight(self):
        packages_by_picking = {
            picking: picking.move_line_ids.result_package_id.outermost_package_id
            for picking in self
        }
        all_packages = self.env["stock.package"].union(*packages_by_picking.values())
        packages_weight = (
            all_packages.sudo()._get_weight_by_picking(self.ids) if all_packages else {}
        )
        for picking in self:
            shipping_weight = picking.weight_bulk
            for package in packages_by_picking[picking]:
                if package.shipping_weight:
                    shipping_weight += package.shipping_weight
                else:
                    shipping_weight += packages_weight.get((package, picking.id), 0)
            picking.shipping_weight = shipping_weight

    @api.depends(
        "move_ids.quantity",
        "move_ids.product_uom_id",
        "move_ids.product_id.volume",
    )
    def _compute_shipping_volume(self):
        volumes = self._get_total_by_picking(
            [],
            "volume",
            "move_ids",
        )
        for picking in self:
            picking.shipping_volume = volumes[picking.id]

    def _get_total_by_picking(self, extra_domain, product_attr, lines_field):
        totals = defaultdict(float)
        saved = self.filtered("id")
        if saved:
            lines_model = self.env[self._fields[lines_field].comodel_name]
            res_groups = lines_model._read_group(
                [
                    ("picking_id", "in", saved.ids),
                    ("product_id", "!=", False),
                    *extra_domain,
                ],
                ["picking_id", "product_id", "product_uom_id"],
                ["quantity:sum"],
            )
            for picking, product, product_uom_id, quantity in res_groups:
                totals[picking.id] += product_uom_id._get_quantity_in_unit(
                    quantity, product.uom_id
                ) * getattr(product, product_attr)
        for picking in self - saved:
            quantity_by_group = defaultdict(float)
            for line in picking[lines_field].filtered_domain(
                [("product_id", "!=", False), *extra_domain],
            ):
                quantity_by_group[line.product_id, line.product_uom_id] += line.quantity
            for (product, product_uom_id), quantity in quantity_by_group.items():
                totals[picking.id] += product_uom_id._get_quantity_in_unit(
                    quantity, product.uom_id
                ) * getattr(product, product_attr)
        return totals

    def action_put_in_pack(
        self,
        *,
        package_id=False,
        package_type_id=False,
        package_name=False,
    ):
        self.check_singleton()
        if self.env.context.get("sml_specific_default"):
            self = self.with_context(clean_context(self.env.context))
        if self.state in DONE_CANCEL_STATES:
            dbg.logic.debug(
                "[picking:%s] action_put_in_pack on closed picking", self.id
            )
            return None
        if self.env.context.get("all_move_line_ids"):
            self = self.with_context(
                all_move_line_ids=(
                    self.move_line_ids
                    & self.env["stock.move.line"].browse(
                        self.env.context["all_move_line_ids"],
                    )
                ).ids,
            )
        return self.move_line_ids.action_put_in_pack(
            package_id=package_id,
            package_type_id=package_type_id,
            package_name=package_name,
        )

    def action_add_entire_packs(self, package_ids):
        self.check_singleton()
        if self.state not in DONE_CANCEL_STATES:
            all_packages = self.env["stock.package"].search(
                [("id", "child_of", package_ids)],
            )
            all_package_ids = set(all_packages.ids)
            self.move_line_ids.filtered(
                lambda ml: ml.package_id.id in all_package_ids,
            ).unlink()
            move_line_vals = self._prepare_entire_pack_move_line_vals(all_packages)
            dbg.pipeline.debug(
                "[picking:%s] action_add_entire_packs %s -> %d lines",
                self.id,
                dbg.rec(all_packages),
                len(move_line_vals),
            )
            pack_move_lines = self.env["stock.move.line"].create(move_line_vals)
            pack_move_lines._apply_putaway_strategy()
            self.move_line_ids.result_package_id._update_package_dest_for_entire_packs(
                allowed_package_ids=all_package_ids,
            )
            return True
        return False

    def _prepare_entire_pack_move_line_vals(self, packages):
        self.check_singleton()
        return [
            {
                "product_id": package_quant.product_id.id,
                "quantity": package_quant.quantity,
                "product_uom_id": package_quant.product_uom_id.id,
                "location_id": package_quant.location_id.id,
                "location_dest_id": self.location_dest_id.id,
                "picking_id": self.id,
                "company_id": self.company_id.id,
                "package_id": package_quant.package_id.id,
                "result_package_id": package_quant.package_id.id,
                "lot_id": package_quant.lot_id.id,
                "owner_id": package_quant.owner_id.id,
                "is_entire_pack": True,
            }
            for package_quant in packages.quant_ids
        ]

    @dbg.timed
    def _check_entire_pack(self):
        for package, package_move_lines in self.move_line_ids.grouped(
            "package_id"
        ).items():
            if not package:
                continue
            pickings = package_move_lines.picking_id
            if pickings._is_single_transfer() and pickings._is_package_entirely_moved(
                package
            ):
                move_lines_to_pack = package_move_lines.filtered(
                    lambda ml: (
                        not ml.result_package_id and ml.state not in DONE_CANCEL_STATES
                    ),
                )
                dbg.logic.debug(
                    "_check_entire_pack: package %s entirely moved, %s keep it (%s)",
                    package.id,
                    dbg.rec(move_lines_to_pack),
                    package.package_type_id.package_use,
                )
                if package.package_type_id.package_use != "reusable":
                    move_lines_to_pack.write(
                        {
                            "result_package_id": package.id,
                            "is_entire_pack": True,
                        },
                    )
        self.move_line_ids.result_package_id._update_package_dest_for_entire_packs()

    def _is_package_entirely_moved(self, package):
        return package._is_entirely_moved_by_move_lines(
            self.move_line_ids.filtered(
                lambda ml: (
                    ml.product_id.is_storable
                    and (
                        ml.package_id == package
                        or ml.package_id in package.all_children_package_ids
                    )
                ),
            ),
        )

    def _is_single_transfer(self):
        return len(self) == 1
