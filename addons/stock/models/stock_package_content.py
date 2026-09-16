import json
from collections import defaultdict
from collections.abc import Iterable

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.numbers import float_is_zero, float_round
from odoo.tools import format_list

from ..tools import debug_log as dbg


class StockPackageContent(models.Model):
    _inherit = "stock.package"

    @api.depends("child_package_ids", "child_package_ids.parent_path")
    def _compute_all_children_package_ids(self):
        def get_all_children(parent_id, children_by_pack):
            children_ids = children_by_pack.get(parent_id, [])
            sub_children_ids = [
                cid
                for child_id in children_ids
                for cid in get_all_children(child_id, children_by_pack)
            ]
            return children_ids + sub_children_ids

        groups = self.env["stock.package"]._read_group(
            [("id", "child_of", self.ids)], ["parent_package_id"], ["id:array_agg"]
        )
        children_by_pack = {
            package.id: children_ids for package, children_ids in groups
        }
        for package in self:
            package.all_children_package_ids = [
                Command.set(get_all_children(package.id, children_by_pack))
            ]

    @api.depends("quant_ids", "all_children_package_ids.quant_ids")
    def _compute_contained_quant_ids(self):
        for package in self:
            package.contained_quant_ids = (
                package.quant_ids | package.all_children_package_ids.quant_ids
            )

    @api.depends("contained_quant_ids.quantity", "contained_quant_ids.product_id")
    @api.depends_context("lang", "uid")
    def _compute_content_description(self):
        precision = self.env["decimal.precision"].get_precision("Product Unit")

        def format_content(product, qty):
            qty = float_round(qty, precision_digits=precision)
            quantity = str(int(qty) if qty == int(qty) else qty)
            if display_uom:
                return f"{quantity} {product.uom_id.name} {product.display_name}"
            return f"{quantity} {product.display_name}"

        display_uom = self.env.user.has_group("uom.group_uom")
        for package in self:
            package.content_description = format_list(
                self.env,
                [
                    format_content(product, sum(quants.mapped("quantity")))
                    for product, quants in package.contained_quant_ids.grouped(
                        "product_id"
                    ).items()
                ],
            )

    @api.depends("move_line_ids", "move_line_ids.location_dest_id")
    def _compute_json_popover(self):
        for package in self:
            if not package._has_issues():
                package.json_popover = False
                continue
            location_names = package.move_line_ids.location_dest_id.mapped(
                "display_name"
            )
            package.json_popover = json.dumps(
                {
                    "title": _("Multiple destinations"),
                    "msg": _(
                        "This package is currently set to be sent in %(location_names_list)s.",
                        location_names_list=location_names,
                    ),
                    "color": "text-warning",
                    "icon": "fa-exclamation-triangle",
                },
            )

    @api.depends("move_line_ids.location_dest_id")
    def _compute_location_dest_id(self):
        for package in self:
            locations = package.move_line_ids.location_dest_id
            package.location_dest_id = locations if len(locations) == 1 else False

    @api.depends(
        "result_move_line_ids",
        "result_move_line_ids.state",
        "child_package_dest_ids",
        "child_package_dest_ids.move_line_ids",
    )
    @dbg.timed
    def _compute_move_line_ids(self):
        children_by_dest_pack, all_pack_ids = self._get_all_children_package_dest_ids()
        groups = self.env["stock.move.line"]._read_group(
            domain=[
                ("state", "not in", ["done", "cancel"]),
                ("result_package_id", "in", all_pack_ids),
            ],
            groupby=["result_package_id"],
            aggregates=["id:array_agg"],
        )
        move_lines_by_package = {
            package.id: move_line_ids for package, move_line_ids in groups
        }

        for package in self:
            move_line_ids = {
                line_id
                for child_id in children_by_dest_pack[package]
                for line_id in move_lines_by_package.get(child_id, [])
            }
            move_line_ids.update(move_lines_by_package.get(package.id, []))
            package.move_line_ids = [Command.set(list(move_line_ids))]

    @api.depends(
        "child_package_ids",
        "child_package_ids.location_id",
        "quant_ids",
        "quant_ids.quantity",
        "quant_ids.location_id",
        "quant_ids.company_id",
    )
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.quant_ids.filtered(
                lambda q: q.product_uom_id.compare(q.quantity, 0) > 0
            )
            if quants:
                locations = quants.location_id
                if len(locations) == 1:
                    package.location_id = locations
                companies = quants.company_id
                if len(companies) == 1 and all(q.company_id for q in quants):
                    package.company_id = companies
            elif package.child_package_ids:
                locations = package.child_package_ids.location_id
                if len(locations) == 1:
                    package.location_id = locations
                companies = package.child_package_ids.company_id
                if len(companies) == 1 and all(
                    p.company_id for p in package.child_package_ids
                ):
                    package.company_id = companies

    @api.depends("move_line_ids")
    def _compute_picking_ids(self):
        for package in self:
            package.picking_ids = package.move_line_ids.picking_id

    @api.depends("contained_quant_ids.owner_id")
    def _compute_owner_id(self):
        for package in self:
            package.owner_id = False
            quants = package.contained_quant_ids
            if quants and all(q.owner_id == quants[0].owner_id for q in quants):
                package.owner_id = quants[0].owner_id

    @api.depends("package_dest_id", "package_dest_id.outermost_package_id")
    def _compute_outermost_package_id(self):
        for package in self:
            if package.package_dest_id:
                package.outermost_package_id = (
                    package.package_dest_id.outermost_package_id
                )
            else:
                package.outermost_package_id = package

    def _search_all_children_package_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        packages = self.search_fetch(
            domain=[("id", operator, value)], field_names=["id"]
        )
        return Domain("id", "parent_of", packages.ids) & Domain(
            "id", "not in", packages.ids
        )

    def _search_contained_quant_ids(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        packages = self.search([("quant_ids", operator, value)])
        if packages:
            return [("id", "parent_of", packages.ids)]
        else:
            return [("id", "=", False)]

    def _get_packages_of_move_lines(self, domain):
        move_lines = self.env["stock.move.line"].search_fetch(
            domain=Domain("state", "not in", ["done", "cancel"]) & Domain(domain),
            field_names=["result_package_id"],
        )
        return move_lines.result_package_id._get_all_package_dest_ids()

    def _search_location_dest_id(self, operator, value):
        if operator != "in":
            return NotImplemented
        here = self._get_packages_of_move_lines(Domain("location_dest_id", "in", value))
        elsewhere = self._get_packages_of_move_lines(
            Domain("location_dest_id", "not in", value)
        )
        return [("id", "in", list(set(here) - set(elsewhere)))]

    def _search_move_line_ids(self, operator, value):
        if operator not in ("in", "any"):
            return NotImplemented
        if operator == "any":
            operator = "in"
            if isinstance(value, Domain):
                value = self.env["stock.move.line"]._search(value)

        if isinstance(value, Iterable) and not isinstance(value, str):
            value = list(value)
        if isinstance(value, list) and value == [False]:
            return [("id", "not in", self._get_packages_of_move_lines(Domain.TRUE))]
        return [
            (
                "id",
                "in",
                self._get_packages_of_move_lines(Domain("id", operator, value)),
            )
        ]

    def _search_owner_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain("contained_quant_ids.owner_id", operator, value)

    def _search_picking_ids(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [
            (
                "id",
                "in",
                self._get_packages_of_move_lines(Domain("picking_id", "in", value)),
            )
        ]

    def _get_weight(self, picking_id=False):
        if picking_id:
            return {
                package: weight
                for (package, __), weight in self._get_weight_by_picking(
                    [picking_id]
                ).items()
            }
        res = {}
        for package in self:
            weight = sum(
                contained.package_type_id.base_weight
                for contained in package | package.all_children_package_ids
            )
            weight += sum(
                quant.quantity * quant.product_id.weight
                for quant in package.contained_quant_ids
            )
            res[package] = weight
        return res

    @dbg.timed
    def _get_weight_by_picking(self, picking_ids):
        picking_ids = list(picking_ids)
        package_weights = defaultdict(float)
        children_by_dest_pack, all_pack_ids = self._get_all_children_package_dest_ids()
        base_weight_per_package_group = self.env["stock.package"]._read_group(
            domain=[("id", "in", all_pack_ids)],
            groupby=["id", "package_type_id.base_weight"],
        )
        base_weight_per_package = {
            pack.id: weight for pack, weight in base_weight_per_package_group
        }

        res_groups = self.env["stock.move.line"]._read_group(
            [
                ("result_package_id", "in", all_pack_ids),
                ("product_id", "!=", False),
                ("picking_id", "in", picking_ids),
            ],
            ["picking_id", "result_package_id", "product_id", "product_uom_id"],
            ["quantity:sum"],
        )
        for picking, result_package, product, product_uom_id, quantity in res_groups:
            package_weights[(picking.id, result_package.id)] += (
                product_uom_id._get_quantity_in_unit(quantity, product.uom_id)
                * product.weight
            )

        res = {}
        for package in self:
            base_weight = package.package_type_id.base_weight or 0.0
            for picking_id in picking_ids:
                weight = base_weight + package_weights[(picking_id, package.id)]
                for child_id in children_by_dest_pack.get(package, []):
                    weight += (
                        base_weight_per_package.get(child_id, 0)
                        + package_weights[(picking_id, child_id)]
                    )
                res[(package, picking_id)] = weight
        return res

    def _get_all_children_package_dest_ids(self):
        all_children_by_pack = defaultdict(list)
        all_children_ids = set(self.ids)
        for package in self:
            descendants = self._walk_dest_tree(
                package.child_package_dest_ids, "child_package_dest_ids"
            )
            if descendants:
                all_children_by_pack[package] = list(descendants)
                all_children_ids.update(descendants)

        dbg.performance.debug(
            "_get_all_children_package_dest_ids: %d packages -> %d with descendants, %d total",
            len(self),
            len(all_children_by_pack),
            len(all_children_ids),
        )
        return all_children_by_pack, all_children_ids

    @staticmethod
    def _walk_dest_tree(start, link_field):
        seen = set()
        frontier = start
        while frontier:
            frontier = frontier.browse(set(frontier.ids) - seen)
            seen.update(frontier.ids)
            frontier = frontier[link_field]
        return seen

    def _update_orphaned_package_dests(self):
        orphaned = self.filtered(
            lambda package: package.package_dest_id and not package.picking_ids
        )
        if orphaned:
            dbg.lifecycle.debug("_update_orphaned_package_dests: %s", dbg.rec(orphaned))
        orphaned.package_dest_id = False

    def _get_all_package_dest_ids(self):
        return list(self._walk_dest_tree(self, "package_dest_id"))

    def _update_parent_packages_from_dest(self, processed_package_ids=None):
        if processed_package_ids is None:
            processed_package_ids = set()
        packages_todo = self.filtered(lambda p: p.id not in processed_package_ids)
        packs_by_container = packages_todo.grouped("package_dest_id")
        for container_package, packages in packs_by_container.items():
            dbg.lifecycle.debug(
                "_update_parent_packages_from_dest: %s -> container %s",
                dbg.rec(packages),
                container_package.id,
            )
            if not container_package:
                packages.write({"parent_package_id": False})
                processed_package_ids.update(packages.ids)
                continue
            new_location = packages.location_id
            if len(new_location) > 1:
                raise UserError(
                    _(
                        "Packages %(duplicate_names)s are moved to different locations while being in the same container %(container_name)s.",
                        duplicate_names=packages.mapped("name"),
                        container_name=container_package.name,
                    )
                )
            contained_quants = container_package.contained_quant_ids.filtered(
                lambda q: (
                    not float_is_zero(
                        q.quantity, precision_rounding=q.product_uom_id.rounding
                    )
                )
            )
            if contained_quants and contained_quants.location_id != new_location:
                old_location = contained_quants.location_id - new_location
                raise UserError(
                    _(
                        "Can't move a container having packages in another location (%(old_location)s) to a different location (%(new_location)s).",
                        old_location=old_location.display_name,
                        new_location=new_location.display_name,
                    )
                )
            packages.write(
                {
                    "parent_package_id": container_package.id,
                    "package_dest_id": False,
                }
            )
            processed_package_ids.update(packages.ids)
        if (
            packages_todo.parent_package_id.package_dest_id
            or packages_todo.parent_package_id.parent_package_id
        ):
            packages_todo.parent_package_id._update_parent_packages_from_dest(
                processed_package_ids
            )

    def _update_package_dest_for_entire_packs(self, allowed_package_ids=None):
        for container, packages in self.grouped("parent_package_id").items():
            if (
                container.child_package_ids == packages
                and container.package_type_id.package_use != "reusable"
            ):
                if allowed_package_ids and container.id not in allowed_package_ids:
                    continue
                dbg.logic.debug(
                    "_update_package_dest_for_entire_packs: %s travel with container %s",
                    dbg.rec(packages),
                    container.id,
                )
                packages.package_dest_id = container
        if self.package_dest_id:
            self.package_dest_id._update_package_dest_for_entire_packs(
                allowed_package_ids
            )

    def _is_entirely_moved_by_move_lines(self, move_lines):
        if not move_lines:
            return True
        precision_digits = self.env["decimal.precision"].get_precision("Product Unit")

        def get_quantity_by_product_and_lot(records, quantity_field):
            return {
                key: sum(group.mapped(quantity_field))
                for key, group in records.grouped(
                    lambda record: (record.product_id, record.lot_id)
                ).items()
            }

        quantities = get_quantity_by_product_and_lot(
            self.contained_quant_ids, "quantity"
        )
        operations = get_quantity_by_product_and_lot(move_lines, "quantity_product_uom")

        return all(
            float_is_zero(
                quantities.get(key, 0) - operations.get(key, 0),
                precision_digits=precision_digits,
            )
            for key in quantities.keys() | operations.keys()
        )

    def _has_issues(self):
        self.check_singleton()
        return len(self.move_line_ids.location_dest_id) > 1
