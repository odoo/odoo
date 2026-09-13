from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.barcode import is_barcode_encoding_valid

from ..const import INVENTORY_REFERENCE_PACKAGE_RELOCATED
from ..tools import debug_log as dbg


class StockPackage(models.Model):
    _name = "stock.package"
    _description = "Package"
    _order = "name, id"
    _parent_name = "parent_package_id"
    _parent_store = True
    _rec_name = "complete_name"
    _rec_names_search = ["complete_name", "dest_complete_name", "name"]

    name = fields.Char(
        string="Package Reference",
        index="trigram",
        copy=False,
        required=True,
    )
    complete_name = fields.Char(
        string="Full Package Name",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
    )
    dest_complete_name = fields.Char(
        string="Package Name At Destination",
        compute="_compute_dest_complete_name",
        recursive=True,
        store=True,
    )
    quant_ids = fields.One2many(
        comodel_name="stock.quant",
        inverse_name="package_id",
        string="Bulk Content",
        readonly=True,
        domain=["|", ("quantity", "!=", 0), ("reserved_quantity", "!=", 0)],
    )
    contained_quant_ids = fields.One2many(
        comodel_name="stock.quant",
        compute="_compute_contained_quant_ids",
        search="_search_contained_quant_ids",
    )
    content_description = fields.Char(
        string="Contents",
        compute="_compute_content_description",
    )
    package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        index=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_package_info",
        recursive=True,
        store=True,
        index=True,
        readonly=False,
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination location",
        compute="_compute_location_dest_id",
        search="_search_location_dest_id",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_package_info",
        recursive=True,
        store=True,
        index=True,
        readonly=True,
    )
    owner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_owner_id",
        search="_search_owner_id",
        compute_sudo=True,
        readonly=True,
    )
    parent_package_id = fields.Many2one(
        comodel_name="stock.package",
        string="Container",
        index="btree_not_null",
    )
    child_package_ids = fields.One2many(
        comodel_name="stock.package",
        inverse_name="parent_package_id",
        string="Contained Packages",
    )
    all_children_package_ids = fields.One2many(
        comodel_name="stock.package",
        compute="_compute_all_children_package_ids",
        search="_search_all_children_package_ids",
    )
    package_dest_id = fields.Many2one(
        comodel_name="stock.package",
        string="Destination Container",
        index="btree_not_null",
    )
    outermost_package_id = fields.Many2one(
        comodel_name="stock.package",
        string="Outermost Destination Container",
        compute="_compute_outermost_package_id",
        recursive=True,
        store=True,
        index="btree_not_null",
    )
    child_package_dest_ids = fields.One2many(
        comodel_name="stock.package",
        inverse_name="package_dest_id",
        string="Assigned Contained Packages",
    )
    result_move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="result_package_id",
        string="Move Lines Targeting This Package",
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        compute="_compute_move_line_ids",
        search="_search_move_line_ids",
        recursive=True,
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers",
        compute="_compute_picking_ids",
        search="_search_picking_ids",
        help="Transfers in which the Package is set as Destination Package",
    )
    shipping_weight = fields.Float(
        digits="Stock Weight",
        help="Total weight of the package.",
    )
    valid_sscc = fields.Boolean(
        string="Package name is valid SSCC",
        compute="_compute_valid_sscc",
    )
    pack_date = fields.Date(default=fields.Date.context_today)
    parent_path = fields.Char(index=True)
    json_popover = fields.Char(
        string="JSON data for popover widget",
        compute="_compute_json_popover",
    )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "stock.package.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        new_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("complete_name"):
                vals["name"] = vals.pop("complete_name")
            if not vals.get("name"):
                package_type = self.env["stock.package.type"].browse(
                    vals.get("package_type_id")
                )
                vals["name"] = package_type._get_next_name_by_sequence()
            new_vals_list.append(vals)

        return super().create(new_vals_list)

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.package.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if "name" in vals and not vals.get("name"):
            vals = {key: value for key, value in vals.items() if key != "name"}
            for package in self:
                package_type = self.env["stock.package.type"].browse(
                    vals.get("package_type_id", package.package_type_id.id)
                )
                package.name = package_type._get_next_name_by_sequence()
        if "location_id" in vals:
            empty_packs = self.filtered(lambda pack: not pack.contained_quant_ids)
            if not vals["location_id"] and self - empty_packs:
                raise UserError(_("Cannot remove the location of a non empty package"))
            if vals["location_id"]:
                if empty_packs:
                    raise UserError(_("Cannot move an empty package"))
                location_dest_id = self.env["stock.location"].browse(
                    vals["location_id"]
                )
                quant_to_move = self.contained_quant_ids.filtered(
                    lambda q: q.product_uom_id.compare(q.quantity, 0) > 0
                )
                dbg.pipeline.debug(
                    "package relocation %s -> location %s: moving %s",
                    dbg.rec(self),
                    vals["location_id"],
                    dbg.rec(quant_to_move),
                )
                quant_to_move.move_quants(
                    location_dest_id,
                    message=INVENTORY_REFERENCE_PACKAGE_RELOCATED,
                    up_to_parent_packages=self,
                )
                negative_quants = self.contained_quant_ids.filtered(
                    lambda q: q.product_uom_id.compare(q.quantity, 0) < 0
                )
                if negative_quants:
                    dbg.logic.debug(
                        "package relocation: negative quants %s moved by inventory moves",
                        dbg.rec(negative_quants),
                    )
                    message = INVENTORY_REFERENCE_PACKAGE_RELOCATED
                    moves = self.env["stock.move"].create(
                        [
                            quant.with_context(
                                inventory_name=message
                            )._prepare_inventory_move_vals(
                                -quant.quantity,
                                location_dest_id,
                                quant.location_id,
                                quant.package_id,
                                quant.package_id,
                            )
                            for quant in negative_quants
                        ]
                    )
                    moves._action_done()
        return super().write(vals)

    @api.constrains("package_dest_id")
    def _check_package_dest_is_not_a_descendant(self):
        for package in self:
            if not package.package_dest_id:
                continue
            if (
                package.package_dest_id.id
                in package._get_all_children_package_dest_ids()[1]
            ):
                raise ValidationError(
                    _(
                        "A package can't have one of its contained packages as destination container."
                    ),
                )

    @api.depends(
        "complete_name",
        "package_type_id.packaging_length",
        "package_type_id.width",
        "package_type_id.height",
    )
    @api.depends_context(
        "formatted_display_name", "show_dest_package", "show_src_package", "is_done"
    )
    def _compute_display_name(self):
        show_dest_package = self.env.context.get("show_dest_package")
        show_src_package = self.env.context.get("show_src_package")
        is_done = self.env.context.get("is_done")
        formatted = self.env.context.get("formatted_display_name")
        for package in self:
            if is_done:
                display_name = package.name
            elif show_dest_package:
                display_name = package.dest_complete_name
            elif show_src_package:
                display_name = package.complete_name
            else:
                display_name = package.name

            if (
                formatted
                and package.package_type_id
                and package.package_type_id.packaging_length
                and package.package_type_id.width
                and package.package_type_id.height
            ):
                package.display_name = f"{display_name}\t--{package.package_type_id.packaging_length} x {package.package_type_id.width} x {package.package_type_id.height}--"
            else:
                package.display_name = display_name

    def _update_path_name(self, parent_field, name_field):
        for package in self:
            parent = package[parent_field]
            package[name_field] = (
                f"{parent[name_field]} > {package.name}" if parent else package.name
            )

    @api.depends("name", "parent_package_id.complete_name")
    def _compute_complete_name(self):
        self._update_path_name("parent_package_id", "complete_name")

    @api.depends("name", "package_dest_id.dest_complete_name")
    def _compute_dest_complete_name(self):
        self._update_path_name("package_dest_id", "dest_complete_name")

    @api.depends("name")
    def _compute_valid_sscc(self):
        for package in self:
            package.valid_sscc = bool(package.name) and is_barcode_encoding_valid(
                package.name, "sscc"
            )

    def action_put_in_pack(
        self, *, package_id=False, package_type_id=False, package_name=False
    ):
        action = self._pre_put_in_pack_hook(
            package_id,
            package_type_id,
            package_name,
            self.env.context.get("from_package_wizard"),
        )
        if action:
            return action

        if package_id:
            package = self.env["stock.package"].browse(package_id)
        else:
            package = self.env["stock.package"].create(
                {
                    "package_type_id": package_type_id,
                    "name": package_name,
                }
            )
        previous_dest_packages = (
            self.env["stock.package"].browse(self._get_all_package_dest_ids()) - self
        )
        self.package_dest_id = package
        if packs_to_clear := previous_dest_packages.filtered(
            lambda p: not p.move_line_ids
        ):
            packs_to_clear.package_dest_id = False

        package.move_line_ids._apply_putaway_strategy()
        return package._post_put_in_pack_hook()

    def action_remove_package(self):
        all_package_dest_ids = self._get_all_package_dest_ids()
        all_move_line_ids = set(self.move_line_ids.ids)
        move_line_ids_to_unlink = set()
        related_move_ids = set()
        move_line_ids_to_update = set()
        picking_ids = self.env.context.get("picking_ids")
        for line in self.move_line_ids:
            if picking_ids and line.picking_id.id not in picking_ids:
                continue
            if line.result_package_id.id in self.ids:
                if line.is_entire_pack:
                    move_line_ids_to_unlink.add(line.id)
                    related_move_ids.add(line.move_id.id)
                else:
                    move_line_ids_to_update.add(line.id)

        dbg.logic.debug(
            "action_remove_package %s: unlink lines %s, clear result on %s",
            dbg.rec(self),
            sorted(move_line_ids_to_unlink),
            sorted(move_line_ids_to_update),
        )
        self.env["stock.move.line"].browse(move_line_ids_to_unlink).unlink()
        self.env["stock.move.line"].browse(move_line_ids_to_update).write(
            {"result_package_id": False}
        )
        self.env["stock.move"].search_fetch(
            [
                ("id", "in", related_move_ids),
                ("product_uom_qty", "=", 0),
                ("move_line_ids", "=", False),
            ],
            field_names=["id"],
        ).unlink()

        self.child_package_dest_ids.package_dest_id = False
        self.package_dest_id = False

        self.env["stock.package"].search_fetch(
            [("id", "in", all_package_dest_ids), ("move_line_ids", "=", False)],
            field_names=["id"],
        ).write({"package_dest_id": False})

        self.env["stock.move.line"].browse(
            all_move_line_ids - move_line_ids_to_unlink
        )._apply_putaway_strategy()
        return True

    def action_view_picking(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_all"
        )
        move_lines = self.env["stock.move.line"].search_fetch(
            domain=Domain("result_package_id", "in", self.ids)
            | Domain("package_id", "in", self.ids),
            field_names=["picking_id"],
        )
        action["domain"] = [("id", "in", move_lines.picking_id.ids)]
        return action

    def action_unpack(self):
        dbg.pipeline.debug(
            "action_unpack %s: children %s, quants %s",
            dbg.rec(self),
            dbg.rec(self.child_package_ids),
            dbg.rec(self.quant_ids),
        )
        self.child_package_ids.parent_package_id = False
        quants = self.quant_ids
        if quants:
            quants.move_quants(message=_("Quantities unpacked"), unpack=True)
            quants._run_maintenance_tasks()

    def _pre_put_in_pack_hook(
        self,
        package_id=False,
        package_type_id=False,
        package_name=False,
        from_package_wizard=False,
    ):
        if self.move_line_ids._is_put_in_pack_wizard_required(
            package_id, package_type_id, package_name, from_package_wizard
        ):
            action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "stock.action_put_in_pack_wizard"
            )
            action["context"] = {
                **self.env["ir.actions.actions"]._eval_action_context(
                    action.get("context")
                ),
                "default_package_ids": self.ids,
                "default_location_dest_id": self.location_dest_id[:1].id,
            }
            return action
        return False

    def _post_put_in_pack_hook(self):
        self.check_singleton()
        return self
