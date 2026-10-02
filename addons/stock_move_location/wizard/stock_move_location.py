# Copyright (C) 2011 Julius Network Solutions SARL <contact@julius.fr>
# Copyright 2018 Camptocamp SA
# Copyright 2019 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from itertools import groupby

from odoo import api, fields, models
from odoo.fields import first
from odoo.osv import expression


class StockMoveLocationWizard(models.TransientModel):
    _name = "wiz.stock.move.location"
    _description = "Wizard move location"

    origin_location_disable = fields.Boolean(
        compute="_compute_readonly_locations",
        help="technical field to disable the edition of origin location.",
    )
    origin_location_id = fields.Many2one(
        string="Origin Location",
        comodel_name="stock.location",
        required=True,
        domain=lambda self: self._get_locations_domain(),
    )
    destination_location_disable = fields.Boolean(
        compute="_compute_readonly_locations",
        help="technical field to disable the edition of destination location.",
    )
    destination_location_id = fields.Many2one(
        string="Destination Location",
        comodel_name="stock.location",
        required=True,
        domain=lambda self: self._get_locations_domain(),
    )
    stock_move_location_line_ids = fields.One2many(
        "wiz.stock.move.location.line",
        "move_location_wizard_id",
        string="Move Location lines",
    )
    picking_type_id = fields.Many2one(
        compute="_compute_picking_type_id",
        comodel_name="stock.picking.type",
        readonly=False,
        store=True,
    )
    picking_id = fields.Many2one(
        string="Connected Picking", comodel_name="stock.picking"
    )
    edit_locations = fields.Boolean(default=True)
    apply_putaway_strategy = fields.Boolean()

    @api.depends("edit_locations")
    def _compute_readonly_locations(self):
        for rec in self:
            rec.origin_location_disable = self.env.context.get(
                "origin_location_disable", False
            )
            rec.destination_location_disable = self.env.context.get(
                "destination_location_disable", False
            )
            if not rec.edit_locations:
                rec.origin_location_disable = True
                rec.destination_location_disable = True

    @api.depends_context("company")
    @api.depends("origin_location_id")
    def _compute_picking_type_id(self):
        company_id = self.env.context.get("company_id") or self.env.company.id
        for rec in self:
            picking_type = self.env["stock.picking.type"]
            base_domain = [
                ("code", "in", ("internal", "outgoing")),
                ("warehouse_id.company_id", "=", company_id),
            ]
            if rec.origin_location_id:
                location_id = rec.origin_location_id
                while location_id and not picking_type:
                    domain = [("default_location_src_id", "=", location_id.id)]
                    domain = expression.AND([base_domain, domain])
                    picking_type = picking_type.search(domain, limit=1)
                    # Move up to the parent location if no picking type found
                    location_id = not picking_type and location_id.location_id or False
            if not picking_type:
                picking_type = picking_type.search(base_domain, limit=1)
            rec.picking_type_id = picking_type.id

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get("active_model", False) != "stock.quant":
            return res
        # Load data directly from quants
        quants = self.env["stock.quant"].browse(
            self.env.context.get("active_ids", False)
        )
        res["stock_move_location_line_ids"] = self._prepare_wizard_move_lines(quants)
        res["origin_location_id"] = first(quants).location_id.id
        return res

    @api.model
    def _prepare_wizard_move_lines(self, quants):
        res = []
        exclude_reserved_qty = self.env.context.get("only_reserved_qty", False)
        if not exclude_reserved_qty:
            res = [
                (
                    0,
                    0,
                    {
                        "product_id": quant.product_id.id,
                        "move_quantity": quant.quantity,
                        "max_quantity": quant.quantity,
                        "reserved_quantity": quant.reserved_quantity,
                        "origin_location_id": quant.location_id.id,
                        "lot_id": quant.lot_id.id,
                        "package_id": quant.package_id.id,
                        "owner_id": quant.owner_id.id,
                        "product_uom_id": quant.product_uom_id.id,
                        "custom": False,
                    },
                )
                for quant in quants
            ]
        else:
            # if need move only available qty per product on location
            for _product, quant in groupby(quants, lambda r: r.product_id):
                # we need only one quant per product
                quant = list(quant)[0]
                qty = quant._get_available_quantity(
                    quant.product_id,
                    quant.location_id,
                )
                if qty:
                    res.append(
                        (
                            0,
                            0,
                            {
                                "product_id": quant.product_id.id,
                                "move_quantity": qty,
                                "max_quantity": qty,
                                "reserved_quantity": quant.reserved_quantity,
                                "origin_location_id": quant.location_id.id,
                                "lot_id": quant.lot_id.id,
                                "package_id": quant.package_id.id,
                                "owner_id": quant.owner_id.id,
                                "product_uom_id": quant.product_uom_id.id,
                                "custom": False,
                            },
                        )
                    )
        return res

    @api.onchange("origin_location_id")
    def _onchange_origin_location_id(self):
        if not self.env.context.get("origin_location_disable", False):
            self._clear_lines()

    @api.onchange("destination_location_id")
    def _onchange_destination_location_id(self):
        for line in self.stock_move_location_line_ids:
            line.destination_location_id = self.destination_location_id

    def _clear_lines(self):
        self.stock_move_location_line_ids = False

    def _get_locations_domain(self):
        return [
            "|",
            ("company_id", "=", self.env.company.id),
            ("company_id", "=", False),
        ]

    def _create_picking(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_id.id,
                "location_id": self.origin_location_id.id,
                "location_dest_id": self.destination_location_id.id,
            }
        )

    def group_lines(self):
        lines_grouped = {}
        for line in self.stock_move_location_line_ids:
            lines_grouped.setdefault(
                line.product_id.id, self.env["wiz.stock.move.location.line"].browse()
            )
            lines_grouped[line.product_id.id] |= line
        return lines_grouped

    def _create_moves(self, picking):
        self.ensure_one()
        groups = self.group_lines()
        moves = self.env["stock.move"]
        for lines in groups.values():
            move = self._create_move(picking, lines)
            moves |= move
        return moves

    def _get_move_values(self, picking, lines):
        # locations are same for the products
        location_from_id = lines[0].origin_location_id.id
        location_to_id = lines[0].destination_location_id.id
        product = lines[0].product_id
        product_uom_id = lines[0].product_uom_id.id
        qty = sum(x.move_quantity for x in lines)
        return {
            "name": product.display_name,
            "location_id": location_from_id,
            "location_dest_id": location_to_id,
            "product_id": product.id,
            "product_uom": product_uom_id,
            "product_uom_qty": qty,
            "picking_id": picking.id,
            "location_move": True,
        }

    def _create_move(self, picking, lines):
        self.ensure_one()
        move = self.env["stock.move"].create(self._get_move_values(picking, lines))
        lines.create_move_lines(picking, move)
        if self.env.context.get("planned"):
            for line in lines:
                available_quantity = self.env["stock.quant"]._get_available_quantity(
                    line.product_id,
                    line.origin_location_id,
                    lot_id=line.lot_id,
                    package_id=line.package_id,
                    owner_id=line.owner_id,
                    strict=True,
                )
                move._update_reserved_quantity(
                    line.move_quantity,
                    available_quantity,
                    line.origin_location_id,
                    lot_id=line.lot_id,
                    package_id=line.package_id,
                    owner_id=line.owner_id,
                    strict=True,
                )
            # Force the state to be assigned, instead of _action_assign,
            # to avoid discarding the selected move_location_line.
            move.state = "assigned"
            move.move_line_ids.write({"state": "assigned"})
        return move

    def _unreserve_moves(self):
        """
        Try to unreserve moves that they has reserved quantity before user
        moves products from a location to other one and change move origin
        location to the new location to assign later.
        :return moves unreserved
        """
        moves_to_reassign = self.env["stock.move"]
        lines_to_ckeck_reverve = self.stock_move_location_line_ids.filtered(
            lambda l: (
                l.move_quantity > l.max_quantity - l.reserved_quantity
                and not l.origin_location_id.should_bypass_reservation()
            )
        )
        for line in lines_to_ckeck_reverve:
            move_lines = self.env["stock.move.line"].search(
                [
                    ("state", "=", "assigned"),
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "=", line.origin_location_id.id),
                    ("lot_id", "=", line.lot_id.id),
                    ("package_id", "=", line.package_id.id),
                    ("owner_id", "=", line.owner_id.id),
                    ("qty_done", ">", 0.0),
                ]
            )
            moves_to_unreserve = move_lines.mapped("move_id")
            # Unreserve in old location
            moves_to_unreserve._do_unreserve()
            moves_to_reassign |= moves_to_unreserve
        return moves_to_reassign

    def action_move_location(self):
        self.ensure_one()
        if not self.picking_id:
            picking = self._create_picking()
        else:
            picking = self.picking_id
        self._create_moves(picking)
        if not self.env.context.get("planned"):
            moves_to_reassign = self._unreserve_moves()
            picking.button_validate()
            moves_to_reassign._action_assign()
        self.picking_id = picking
        return self._get_picking_action(picking.id)

    def _get_picking_action(self, picking_id):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        form_view = self.env.ref("stock.view_picking_form").id
        action.update(
            {"view_mode": "form", "views": [(form_view, "form")], "res_id": picking_id}
        )
        return action

    def _get_quants_domain(self):
        return [("location_id", "=", self.origin_location_id.id)]

    def _get_group_quants(self):
        domain = self._get_quants_domain()
        result = self.env["stock.quant"].read_group(
            domain=domain,
            fields=[
                "product_id",
                "lot_id",
                "package_id",
                "owner_id",
                "quantity:sum",
                "reserved_quantity:sum",
            ],
            groupby=["product_id", "lot_id", "package_id", "owner_id"],
            orderby="id",
            lazy=False,
        )
        return result

    def _get_stock_move_location_lines_values(self):
        product_obj = self.env["product.product"]
        product_data = []
        for group in self._get_group_quants():
            product = product_obj.browse(group["product_id"][0]).exists()
            # Apply the putaway strategy
            location_dest_id = (
                self.apply_putaway_strategy
                and self.destination_location_id._get_putaway_strategy(product).id
                or self.destination_location_id.id
            )
            product_data.append(
                {
                    "product_id": product.id,
                    "move_quantity": group.get("quantity") or 0,
                    "max_quantity": group.get("quantity") or 0,
                    "reserved_quantity": group.get("reserved_quantity"),
                    "origin_location_id": self.origin_location_id.id,
                    "destination_location_id": location_dest_id,
                    # cursor returns None instead of False
                    "lot_id": group["lot_id"][0] if group.get("lot_id") else False,
                    "package_id": group["package_id"][0]
                    if group.get("package_id")
                    else False,
                    "owner_id": group["owner_id"][0]
                    if group.get("owner_id")
                    else False,
                    "product_uom_id": product.uom_id.id,
                    "custom": False,
                }
            )
        return product_data

    def _reset_stock_move_location_lines(self):
        lines = []
        line_model = self.env["wiz.stock.move.location.line"]
        for line_val in self._get_stock_move_location_lines_values():
            if line_val.get("max_quantity") <= 0:
                continue
            line = line_model.create(line_val)
            line.max_quantity = line.get_max_quantity()
            line.reserved_quantity = line.reserved_quantity
            lines.append(line)
        self.update(
            {"stock_move_location_line_ids": [(6, 0, [line.id for line in lines])]}
        )

    @api.onchange("origin_location_id")
    def onchange_origin_location(self):
        # Get origin_location_disable context key to prevent load all origin
        # location products when user opens the wizard from stock quants to
        # move it to other location.
        if (
            not self.env.context.get("origin_location_disable")
            and self.origin_location_id
        ):
            self._reset_stock_move_location_lines()

    def clear_lines(self):
        self._clear_lines()
        return {"type": "ir.action.do_nothing"}
