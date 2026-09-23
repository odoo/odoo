from odoo import api, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import groupby

from ..tools import debug_log as dbg
from odoo.addons.web.controllers.utils import clean_action


class StockMoveLinePackage(models.Model):
    _inherit = "stock.move.line"

    @api.onchange("result_package_id", "product_id", "product_uom_id", "quantity")
    def _onchange_putaway_location(self):
        default_dest_location = self._get_default_dest_location()
        if (
            not self.id
            and self.env.user.has_group("stock.group_stock_multi_locations")
            and self.product_id
            and self.quantity_product_uom
            and self.location_dest_id == default_dest_location
        ):
            quantity = self.quantity_product_uom
            self.location_dest_id = default_dest_location.with_context(
                exclude_sml_ids=self.ids
            )._get_putaway_strategy(
                self.product_id, quantity=quantity, package=self.result_package_id
            )

    @dbg.timed
    def _apply_putaway_strategy(self):
        if self.env.context.get("avoid_putaway_rules"):
            dbg.logic.debug("_apply_putaway_strategy skipped (avoid_putaway_rules)")
            return
        for package, smls in groupby(
            self,
            lambda sml: sml.result_package_id.outermost_package_id,
        ):
            smls = self.env["stock.move.line"].concat(*smls)
            locations = smls.move_id.location_dest_id.child_internal_location_ids
            excluded_smls = set(smls.ids)
            dbg.logic.debug(
                "_apply_putaway_strategy: %s package=%s type=%s over %d candidate locations",
                dbg.rec(smls),
                package.id,
                package.package_type_id.id,
                len(locations),
            )
            if package.package_type_id:
                smls._apply_putaway_by_package_type(package, locations, excluded_smls)
            elif package:
                smls._apply_putaway_keeping_package_together(locations, excluded_smls)
            else:
                smls._apply_putaway_per_line(excluded_smls)

    def _apply_putaway_by_package_type(self, package, locations, excluded_smls):
        for location_dest, dest_smls in self.grouped(
            lambda sml: sml.move_id.location_dest_id
        ).items():
            if not location_dest:
                continue
            dest_smls.location_dest_id = location_dest.with_context(
                exclude_sml_ids=excluded_smls,
                products=dest_smls.product_id,
                locations=locations,
            )._get_putaway_strategy(self.env["product.product"], package=package)

    def _apply_putaway_keeping_package_together(self, locations, excluded_smls):
        used_locations = set()
        for sml in self:
            if len(used_locations) > 1:
                break
            putaway_location = sml.move_id.location_dest_id.with_context(
                exclude_sml_ids=excluded_smls,
                locations=locations,
            )._get_putaway_strategy(sml.product_id, quantity=sml.quantity_product_uom)
            if putaway_location != sml.location_dest_id:
                sml.location_dest_id = putaway_location
            excluded_smls.discard(sml.id)
            used_locations.add(sml.location_dest_id)
        if len(used_locations) > 1:
            dbg.logic.debug(
                "_apply_putaway_keeping_package_together: %d locations, falling back "
                "to move destinations",
                len(used_locations),
            )
            for move, grouped_smls in self.grouped("move_id").items():
                grouped_smls.location_dest_id = move.location_dest_id

    def _apply_putaway_per_line(self, excluded_smls):
        for sml in self:
            putaway_location = sml.move_id.location_dest_id.with_context(
                exclude_sml_ids=excluded_smls,
            )._get_putaway_strategy(
                sml.product_id,
                quantity=sml.quantity_product_uom,
                packaging=sml.move_id.packaging_uom_id,
            )
            if putaway_location != sml.location_dest_id:
                dbg.logic.debug(
                    "[line:%s] putaway %s -> %s",
                    sml.id,
                    sml.location_dest_id.id,
                    putaway_location.id,
                )
                sml.location_dest_id = putaway_location
            excluded_smls.discard(sml.id)

    def _get_lines_in_pack_scope(self):
        scope_ids = self.env.context.get("all_move_line_ids")
        if not scope_ids:
            return self
        widened = self.browse(scope_ids).exists()
        if not self.picking_id:
            return self
        return self | widened.filtered(lambda ml: ml.picking_id in self.picking_id)

    def action_put_in_pack(
        self, *, package_id=False, package_type_id=False, package_name=False
    ):
        move_lines = self._get_lines_in_pack_scope()
        force_move_lines = bool(self.env.context.get("force_move_lines"))

        move_lines_to_pack, packages_to_pack = (
            move_lines._get_lines_and_packages_to_pack(
                picked_first=not force_move_lines
            )
        )
        dbg.pipeline.debug(
            "action_put_in_pack on %s: lines %s, packages %s, package_id=%s type=%s",
            dbg.rec(self),
            dbg.rec(move_lines_to_pack),
            dbg.rec(packages_to_pack),
            package_id,
            package_type_id,
        )
        done_pack = False
        package = self.env["stock.package"]
        if move_lines_to_pack:
            action = move_lines_to_pack._pre_put_in_pack_hook(
                move_lines if force_move_lines else False,
                package_id,
                package_type_id,
                package_name,
                self.env.context.get("from_package_wizard"),
            )
            if action:
                dbg.pipeline.debug("action_put_in_pack: pre hook returned an action")
                return action

            package = move_lines_to_pack._put_in_pack(
                package_id, package_type_id, package_name
            )
            done_pack = move_lines_to_pack._post_put_in_pack_hook(package)
        if done_pack and not force_move_lines:
            return done_pack
        if packages_to_pack:
            if package:
                packages_to_pack -= package
                package_id = package.id
            if packages_to_pack:
                return packages_to_pack.action_put_in_pack(
                    package_id=package_id,
                    package_type_id=package_type_id,
                    package_name=package_name,
                )
        return None

    def _pre_put_in_pack_hook(
        self,
        all_lines=False,
        package_id=False,
        package_type_id=False,
        package_name=False,
        from_package_wizard=False,
    ):
        move_lines = all_lines or self
        action = move_lines._action_open_choose_destination()
        if action:
            return action
        if self._is_put_in_pack_wizard_required(
            package_id, package_type_id, package_name, from_package_wizard
        ):
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "stock.action_put_in_pack_wizard"
            )
            action["context"] = {
                **self.env["ir.actions.actions"]._eval_action_context(
                    action.get("context")
                ),
                "all_move_line_ids": move_lines.ids,
                "default_move_line_ids": self.ids,
                "default_location_dest_id": self.location_dest_id.id,
                "picking_ids": move_lines.picking_id.ids,
            }
            return action
        return None

    def _put_in_pack(self, package_id=False, package_type_id=False, package_name=False):
        if package_id:
            package = self.env["stock.package"].browse(package_id)
        elif package_type_id:
            package = self.env["stock.package"].create(
                {
                    "name": package_name,
                    "package_type_id": package_type_id,
                }
            )
        else:
            package_vals = {"name": package_name}
            package_type = self.move_id.packaging_uom_id.package_type_id
            if len(package_type) == 1:
                package_vals["package_type_id"] = package_type.id
            package = self.env["stock.package"].create(package_vals)
        if len(self) == 1:
            default_dest_location = self._get_default_dest_location()
            self.location_dest_id = default_dest_location._get_putaway_strategy(
                product=self.product_id,
                quantity=self.quantity_product_uom,
                package=package,
            )
        dbg.lifecycle.debug(
            "_put_in_pack: %s -> package %s (%s)",
            dbg.rec(self),
            package.id,
            "existing" if package_id else "new",
        )
        self.write({"result_package_id": package.id})
        return package

    def _post_put_in_pack_hook(self, package):
        if package and self.picking_type_id.auto_print_package_label:
            action = None
            if self.picking_type_id.package_label_to_print == "pdf":
                action = self.env.ref(
                    "stock.action_report_package_barcode_small"
                ).report_action(package.id, config=False)
            elif self.picking_type_id.package_label_to_print == "zpl":
                action = self.env.ref("stock.label_package_template").report_action(
                    package.id, config=False
                )
            if action:
                action.update({"close_on_report_download": True})
                clean_action(action, self.env)
                return action
        return package

    def _get_lines_and_packages_to_pack(self, picked_first=True):
        if len(self.picking_type_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot pack products into the same package when they are from different transfers with different operation types"
                ),
            )

        quantity_move_lines = self.filtered(
            lambda ml: (
                ml.state not in ("done", "cancel")
                and ml.product_uom_id.compare(ml.quantity, 0.0) > 0
            )
        )
        if picked_first:
            picked_move_lines = quantity_move_lines.filtered(lambda ml: ml.picked)
            if picked_move_lines:
                quantity_move_lines = picked_move_lines

        move_lines_to_pack = quantity_move_lines.filtered(
            lambda ml: not ml.result_package_id
        )
        packages_to_pack = (
            quantity_move_lines - move_lines_to_pack
        ).result_package_id.outermost_package_id

        return move_lines_to_pack, packages_to_pack

    def _get_lines_not_entire_pack(self):
        relevant_move_lines = self.filtered(lambda ml: ml.is_entire_pack)
        if not relevant_move_lines:
            return self.browse()

        ids_to_update = set(
            relevant_move_lines.filtered(
                lambda ml: ml.package_id != ml.result_package_id
            ).ids
        )
        for package, move_lines in relevant_move_lines.grouped("package_id").items():
            pickings = move_lines.picking_id
            if (
                not pickings._is_single_transfer()
                or not pickings._is_package_entirely_moved(package)
            ):
                ids_to_update.update(
                    pickings.move_line_ids.filtered(
                        lambda ml, package=package: ml.package_id == package
                    ).ids
                )

        if ids_to_update:
            dbg.logic.debug("_get_lines_not_entire_pack: %s", sorted(ids_to_update))
        return self.env["stock.move.line"].browse(ids_to_update)

    def _is_put_in_pack_wizard_required(
        self, package_id, package_type_id, package_name, from_package_wizard
    ):
        return (
            self._is_package_set_required()
            and not from_package_wizard
            and not (package_id or package_type_id or package_name)
        )

    def _is_package_set_required(self):
        picking_type = self.picking_type_id
        return len(picking_type) == 1 and picking_type.set_package_type

    def _action_open_choose_destination(self):
        if len(self.location_dest_id) > 1:
            view_id = self.env.ref("stock.stock_package_destination_form_view").id
            wiz = self.env["stock.package.destination"].create(
                {
                    "move_line_ids": self.ids,
                    "location_dest_id": self[0].location_dest_id.id,
                }
            )
            return {
                "name": self.env._("Choose destination location"),
                "view_mode": "form",
                "res_model": "stock.package.destination",
                "view_id": view_id,
                "views": [(view_id, "form")],
                "type": "ir.actions.act_window",
                "res_id": wiz.id,
                "target": "new",
            }
        return None

    def _get_package_dests(self):
        return self.env["stock.package"].browse(
            self.result_package_id._get_all_package_dest_ids()
        )

    def _get_default_dest_location(self):
        if not self.env.user.has_group("stock.group_stock_multi_locations"):
            return self.location_dest_id[:1]
        if self.env.context.get("default_location_dest_id"):
            return self.env["stock.location"].browse(
                [self.env.context.get("default_location_dest_id")],
            )
        return (
            self.move_id.location_dest_id
            or self.picking_id.location_dest_id
            or self.location_dest_id
        )[:1]

    def _prepare_package_history_vals(self):
        packages = self._get_package_dests()
        return [
            {
                "location_id": package.location_id.id,
                "location_dest_id": package.location_dest_id.id,
                "move_line_ids": [
                    Command.set(
                        package.move_line_ids.filtered(
                            lambda ml, package=package: ml.result_package_id == package
                        ).ids
                    )
                ],
                "picking_ids": [Command.set(package.picking_ids.ids)],
                "package_id": package.id,
                "package_name": package.dest_complete_name,
                "parent_orig_id": package.parent_package_id.id,
                "parent_orig_name": package.parent_package_id.complete_name,
                "parent_dest_id": package.package_dest_id.id,
                "parent_dest_name": package.package_dest_id.dest_complete_name,
                "outermost_dest_id": package.outermost_package_id.id,
            }
            for package in packages
        ]
