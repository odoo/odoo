# Copyright (C) 2011 Julius Network Solutions SARL <contact@julius.fr>
# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockMoveLocationWizardLine(models.TransientModel):
    _name = "wiz.stock.move.location.line"
    _description = "Wizard move location line"

    move_location_wizard_id = fields.Many2one(
        string="Move location Wizard",
        comodel_name="wiz.stock.move.location",
    )
    product_id = fields.Many2one(
        string="Product", comodel_name="product.product", required=True
    )
    origin_location_id = fields.Many2one(
        string="Origin Location", comodel_name="stock.location"
    )
    destination_location_id = fields.Many2one(
        string="Destination Location", comodel_name="stock.location"
    )
    product_uom_id = fields.Many2one(
        string="Product Unit of Measure", comodel_name="uom.uom"
    )
    lot_id = fields.Many2one(
        string="Lot/Serial Number",
        comodel_name="stock.lot",
        domain="[('product_id','=',product_id)]",
    )
    package_id = fields.Many2one(
        string="Package Number",
        comodel_name="stock.quant.package",
        domain="[('location_id', '=', origin_location_id)]",
    )
    owner_id = fields.Many2one(comodel_name="res.partner", string="From Owner")
    move_quantity = fields.Float(
        string="Quantity to move", digits="Product Unit of Measure"
    )
    max_quantity = fields.Float(
        string="Maximum available quantity", digits="Product Unit of Measure"
    )
    reserved_quantity = fields.Float(digits="Product Unit of Measure")
    custom = fields.Boolean(string="Custom line", default=True)

    @staticmethod
    def _compare(qty1, qty2, precision_rounding):
        return float_compare(qty1, qty2, precision_rounding=precision_rounding)

    @api.constrains("max_quantity", "move_quantity")
    def _constraint_max_move_quantity(self):
        for record in self:
            rounding = record.product_uom_id.rounding
            move_qty_gt_max_qty = (
                self._compare(record.move_quantity, record.max_quantity, rounding) == 1
            )
            move_qty_lt_0 = self._compare(record.move_quantity, 0.0, rounding) == -1
            if move_qty_gt_max_qty or move_qty_lt_0:
                raise ValidationError(
                    _("Move quantity can not exceed max quantity or be negative")
                )

    def get_max_quantity(self):
        self.product_uom_id = self.product_id.uom_id
        search_args = [
            ("location_id", "=", self.origin_location_id.id),
            ("product_id", "=", self.product_id.id),
        ]
        if self.lot_id:
            search_args.append(("lot_id", "=", self.lot_id.id))
        else:
            search_args.append(("lot_id", "=", False))
        if self.package_id:
            search_args.append(("package_id", "=", self.package_id.id))
        else:
            search_args.append(("package_id", "=", False))
        if self.owner_id:
            search_args.append(("owner_id", "=", self.owner_id.id))
        else:
            search_args.append(("owner_id", "=", False))
        res = self.env["stock.quant"].read_group(search_args, ["quantity"], [])
        max_quantity = res[0]["quantity"]
        return max_quantity

    def create_move_lines(self, picking, move):
        for line in self:
            values = line._get_move_line_values(picking, move)
            if not self.env.context.get("planned") and values.get("qty_done") <= 0:
                continue
            self.env["stock.move.line"].create(values)
        return True

    def _get_move_line_values(self, picking, move):
        self.ensure_one()
        location_dest_id = (
            self.move_location_wizard_id.apply_putaway_strategy
            and self.destination_location_id._get_putaway_strategy(self.product_id).id
            or self.destination_location_id.id
        )
        qty_todo, qty_done = self._get_available_quantity()
        return {
            "product_id": self.product_id.id,
            "lot_id": self.lot_id.id,
            "package_id": self.package_id.id,
            "result_package_id": self.package_id.id,
            "owner_id": self.owner_id.id,
            "location_id": self.origin_location_id.id,
            "location_dest_id": location_dest_id,
            "qty_done": qty_done,
            "product_uom_id": self.product_uom_id.id,
            "picking_id": picking.id,
            "move_id": move.id,
        }

    def _get_available_quantity(self):
        """We check here if the actual amount changed in the stock.

        We don't care about the reservations but we do care about not moving
        more than exists."""
        self.ensure_one()
        if not self.product_id:
            return 0
        if self.env.context.get("planned"):
            # for planned transfer we don't care about the amounts at all
            return self.move_quantity, 0
        search_args = [
            ("location_id", "=", self.origin_location_id.id),
            ("product_id", "=", self.product_id.id),
        ]
        if self.lot_id:
            search_args.append(("lot_id", "=", self.lot_id.id))
        else:
            search_args.append(("lot_id", "=", False))
        if self.package_id:
            search_args.append(("package_id", "=", self.package_id.id))
        else:
            search_args.append(("package_id", "=", False))
        if self.owner_id:
            search_args.append(("owner_id", "=", self.owner_id.id))
        else:
            search_args.append(("owner_id", "=", False))
        res = self.env["stock.quant"].read_group(search_args, ["quantity"], [])
        available_qty = res[0]["quantity"]
        if not available_qty:
            # if it is immediate transfer and product doesn't exist in that
            # location -> make the transfer of 0.
            return 0
        rounding = self.product_uom_id.rounding
        available_qty_lt_move_qty = (
            self._compare(available_qty, self.move_quantity, rounding) == -1
        )
        if available_qty_lt_move_qty:
            return available_qty
        return 0, self.move_quantity
