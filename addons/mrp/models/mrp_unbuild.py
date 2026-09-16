from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare
from odoo.tools.misc import clean_context

_debug = DebugLog(__name__)


class MrpUnbuild(models.Model):
    _name = "mrp.unbuild"
    _description = "Unbuild Order"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        default=lambda s: s.env._("New"),
        copy=False,
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        compute="_compute_product_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('type', '=', 'consu')]",
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda s: s.env.company,
        index=True,
        required=True,
    )
    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        compute="_compute_product_qty",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Material",
        compute="_compute_bom_id",
        store=True,
        domain="""[
        '|',
            ('product_id', '=', product_id),
            '&',
                ('product_tmpl_id.product_variant_ids', '=', product_id),
                ('product_id','=',False),
        ('type', '=', 'normal'),
        '|',
            ('company_id', '=', company_id),
            ('company_id', '=', False)
        ]""",
        check_company=True,
    )
    mo_id = fields.Many2one(
        comodel_name="mrp.production",
        string="Manufacturing Order",
        index="btree_not_null",
        domain="[('state', '=', 'done'), ('product_id', '=?', product_id), ('bom_id', '=?', bom_id)]",
        check_company=True,
    )
    mo_bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        related="mo_id.bom_id",
        string="Bill of Material used on the Production Order",
    )
    lot_producing_ids = fields.Many2many(
        comodel_name="stock.lot",
        related="mo_id.lot_producing_ids",
        string="Lot/Serial Numbers",
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Lot/Serial Number",
        domain="[('product_id', '=', product_id),('id', 'in', lot_producing_ids)]",
        check_company=True,
    )
    has_tracking = fields.Selection(
        related="product_id.tracking",
        readonly=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_locations",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage','=','internal')]",
        check_company=True,
        help="Location where the product you want to unbuild is.",
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        compute="_compute_locations",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('usage','=','internal')]",
        check_company=True,
        help="Location where you want to send the components resulting from the unbuild order.",
    )
    consume_line_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="consume_unbuild_id",
        string="Consumed Disassembly Lines",
        readonly=True,
    )
    produce_line_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="unbuild_id",
        string="Processed Disassembly Lines",
        readonly=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        string="Status",
        default="draft",
    )

    _qty_positive = models.Constraint(
        "check (product_qty > 0)",
        "The quantity to unbuild must be positive!",
    )

    @api.depends("mo_id", "product_id")
    def _compute_product_uom_id(self):
        for record in self:
            if record.mo_id.product_id and record.mo_id.product_id == record.product_id:
                record.product_uom_id = record.mo_id.product_uom_id.id
            else:
                record.product_uom_id = record.product_id.uom_id.id

    @api.depends("company_id")
    def _compute_locations(self):
        warehouse_by_company = {}
        for warehouse in self.env["stock.warehouse"].search(
            [("company_id", "in", self.company_id.ids)]
        ):
            warehouse_by_company.setdefault(warehouse.company_id.id, warehouse)
        for order in self:
            if not order.company_id:
                continue
            stock_location = warehouse_by_company.get(
                order.company_id.id, self.env["stock.warehouse"]
            ).lot_stock_id
            if order.location_id.company_id != order.company_id:
                order.location_id = stock_location
            if order.location_dest_id.company_id != order.company_id:
                order.location_dest_id = stock_location

    @api.depends("mo_id", "product_id", "company_id")
    def _compute_bom_id(self):
        orders_without_mo = self.filtered(lambda order: not order.mo_id)
        boms_by_company = {
            company.id: self.env["mrp.bom"]._get_bom_by_product(
                orders.product_id, company_id=company.id
            )
            for company, orders in orders_without_mo.grouped("company_id").items()
        }
        for order in self:
            if order.mo_id:
                order.bom_id = order.mo_id.bom_id
            else:
                order.bom_id = boms_by_company[order.company_id.id][order.product_id]

    @api.depends("mo_id")
    def _compute_product_id(self):
        for order in self:
            if order.mo_id and order.mo_id.product_id:
                order.product_id = order.mo_id.product_id

    @api.depends("mo_id", "mo_id.qty_produced", "has_tracking")
    def _compute_product_qty(self):
        for order in self:
            if not order.mo_id or order.has_tracking == "serial":
                order.product_qty = 1.0
            else:
                order.product_qty = order.mo_id.qty_produced

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("mrp.unbuild") or _(
                    "New"
                )
        _debug.lifecycle("create", count=len(vals_list))
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if "done" in self.mapped("state"):
            _debug.logic("unbuild_refused", reason="delete_done", unbuilds=self)
            raise UserError(
                _("You cannot delete an unbuild order if the state is 'Done'.")
            )

    def _prepare_finished_move_line_vals(self, finished_move):
        return {
            "move_id": finished_move.id,
            "lot_id": self.lot_id.id,
            "quantity": finished_move.product_uom_qty - finished_move.quantity,
            "product_id": finished_move.product_id.id,
            "product_uom_id": finished_move.product_uom_id.id,
            "location_id": finished_move.location_id.id,
            "location_dest_id": finished_move.location_dest_id.id,
        }

    def _prepare_move_line_vals(self, move, origin_move_line, taken_quantity):
        return {
            "move_id": move.id,
            "lot_id": origin_move_line.lot_id.id,
            "quantity": taken_quantity,
            "product_id": move.product_id.id,
            "product_uom_id": origin_move_line.product_uom_id.id,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
        }

    def action_unbuild(self):
        self.check_singleton()
        self._check_company()
        self = self.with_env(self.env(context=clean_context(self.env.context)))
        if self.product_id.tracking != "none" and not self.lot_id.id:
            _debug.logic("unbuild_refused", reason="no_lot", unbuild=self.id)
            raise UserError(_("You should provide a lot number for the final product."))

        if self.mo_id and self.mo_id.state != "done":
            _debug.logic("unbuild_refused", reason="mo_not_done", unbuild=self.id)
            raise UserError(_("You cannot unbuild a undone manufacturing order."))

        if self.mo_id and self.mo_id.product_uom_id.is_zero(self.mo_id.qty_produced):
            _debug.logic("unbuild_refused", reason="nothing_produced", unbuild=self)
            raise UserError(
                _("You cannot unbuild a manufacturing order that produced nothing.")
            )

        if not self.mo_id and not self.bom_id:
            _debug.logic("unbuild_refused", reason="no_bom_no_mo", unbuild=self.id)
            raise UserError(
                _(
                    "%(product)s has no bill of materials, so there is nothing to"
                    " unbuild it into. Set one on this order, or select the"
                    " manufacturing order that produced it.",
                    product=self.product_id.display_name,
                )
            )

        consume_moves = self._create_consume_moves()
        consume_moves._action_confirm()
        produce_moves = self._create_produce_moves()
        produce_moves._action_confirm()
        produce_moves.quantity = 0
        _debug.pipeline("unbuild", consume=consume_moves, produce=produce_moves)

        previously_unbuilt_lots = (
            (self.mo_id.unbuild_ids - self)
            .produce_line_ids.filtered(
                lambda ml: (
                    ml.product_id != self.product_id
                    and ml.product_id.tracking == "serial"
                )
            )
            .lot_ids
        )

        finished_moves = consume_moves.filtered(
            lambda m: m.product_id == self.product_id
        )
        consume_moves -= finished_moves
        error_message = _(
            "Please specify a manufacturing order.\n"
            "It will allow us to retrieve the lots/serial numbers of the correct components and/or byproducts."
        )

        if any(
            produce_move.has_tracking != "none" and not self.mo_id
            for produce_move in produce_moves
        ):
            raise UserError(error_message)

        if any(
            consume_move.has_tracking != "none" and not self.mo_id
            for consume_move in consume_moves
        ):
            raise UserError(error_message)

        finished_line_vals = [
            self._prepare_finished_move_line_vals(finished_move)
            for finished_move in finished_moves
            if float_compare(
                finished_move.product_uom_qty,
                finished_move.quantity,
                precision_rounding=finished_move.product_uom_id.rounding,
            )
            > 0
        ]
        if finished_line_vals:
            self.env["stock.move.line"].create(finished_line_vals)

        qty_already_used = defaultdict(float)
        unbuild_lines = self.env["stock.move.line"]
        for move in produce_moves | consume_moves:
            if (
                float_compare(
                    move.product_uom_qty,
                    move.quantity,
                    precision_rounding=move.product_uom_id.rounding,
                )
                < 1
            ):
                continue
            if move in produce_moves:
                original_move = self.mo_id.move_raw_ids
            else:
                original_move = self.mo_id.move_finished_ids
            original_move = original_move.filtered(
                lambda m, move=move: m.product_id == move.product_id
            )
            if not original_move:
                move.quantity = move.product_uom_id.round(move.product_uom_qty)
                continue
            needed_quantity = move.product_uom_qty
            move_line_vals_list = []
            moves_lines = original_move.mapped("move_line_ids")
            if move in produce_moves and self.lot_id:
                moves_lines = moves_lines.filtered(
                    lambda ml: (
                        self.lot_id in ml.produce_line_ids.lot_id
                        and ml.lot_id not in previously_unbuilt_lots
                    )
                )
            for move_line in moves_lines:
                taken_quantity = min(
                    needed_quantity, move_line.quantity - qty_already_used[move_line]
                )
                taken_quantity = move.product_uom_id.round(taken_quantity)
                if taken_quantity:
                    move_line_vals = self._prepare_move_line_vals(
                        move, move_line, taken_quantity
                    )
                    if move_line.owner_id:
                        move_line_vals["owner_id"] = move_line.owner_id.id
                    move_line_vals_list.append(move_line_vals)
                    needed_quantity -= taken_quantity
                    qty_already_used[move_line] += taken_quantity
            if move_line_vals_list:
                unbuild_lines |= self.env["stock.move.line"].create(move_line_vals_list)
            if (
                move in produce_moves
                and float_compare(
                    needed_quantity, 0, precision_rounding=move.product_uom_id.rounding
                )
                > 0
            ):
                move.quantity += needed_quantity

        unbuild_lines._apply_putaway_strategy()
        _debug.pipeline("unbuild_lines_built", unbuild=self.id, lines=unbuild_lines)

        (finished_moves | consume_moves | produce_moves).picked = True
        finished_moves._action_done()
        consume_moves._action_done()
        produce_moves._action_done()
        produced_move_line_ids = produce_moves.mapped("move_line_ids").filtered(
            lambda ml: ml.quantity > 0
        )
        consume_moves.mapped("move_line_ids").write(
            {"produce_line_ids": [(6, 0, produced_move_line_ids.ids)]}
        )
        _debug.lifecycle("unbuild_done", unbuild=self.id, mo=self.mo_id)
        if self.mo_id:
            unbuild_msg = _(
                "%(qty)s %(measure)s unbuilt in %(order)s",
                qty=self.product_qty,
                measure=self.product_uom_id.name,
                order=self._get_html_link(),
            )
            self.mo_id.message_post(
                body=unbuild_msg,
                subtype_xmlid="mail.mt_note",
            )
        return self.write({"state": "done"})

    def _get_unbuild_factor(self):
        self.check_singleton()
        if self.mo_id:
            return self.product_qty / self.mo_id.product_uom_id._get_quantity_in_unit(
                self.mo_id.qty_produced, self.product_uom_id
            )
        return (
            self.product_uom_id._get_quantity_in_unit(
                self.product_qty, self.bom_id.product_uom_id
            )
            / self.bom_id.product_qty
        )

    def _create_consume_moves(self):
        moves = self.env["stock.move"]
        for unbuild in self:
            factor = unbuild._get_unbuild_factor()
            if unbuild.mo_id:
                finished_moves = unbuild.mo_id.move_finished_ids.filtered(
                    lambda move: move.state == "done"
                )
                for finished_move in finished_moves:
                    moves += unbuild._create_move_from_existing_move(
                        finished_move,
                        factor,
                        unbuild.location_id,
                        finished_move.location_id,
                    )
            else:
                moves += unbuild._create_move_from_bom_line(
                    unbuild.product_id, unbuild.product_uom_id, unbuild.product_qty
                )
                for byproduct in unbuild.bom_id.byproduct_ids:
                    if byproduct._is_bom_line_skipped(unbuild.product_id):
                        continue
                    quantity = byproduct.product_qty * factor
                    moves += unbuild._create_move_from_bom_line(
                        byproduct.product_id,
                        byproduct.product_uom_id,
                        quantity,
                        byproduct_id=byproduct.id,
                    )
        _debug.pipeline("unbuild_consume_moves", unbuilds=self, moves=moves)
        return moves

    def _create_produce_moves(self):
        moves = self.env["stock.move"]
        for unbuild in self:
            factor = unbuild._get_unbuild_factor()
            if unbuild.mo_id:
                raw_moves = unbuild.mo_id.move_raw_ids.filtered(
                    lambda move: move.state == "done"
                )
                for raw_move in raw_moves:
                    moves += unbuild._create_move_from_existing_move(
                        raw_move,
                        factor,
                        raw_move.location_dest_id,
                        unbuild.location_dest_id,
                    )
            else:
                _boms, lines = unbuild.bom_id._explode(
                    unbuild.product_id,
                    factor,
                    picking_type=unbuild.bom_id.picking_type_id,
                )
                for line, line_data in lines:
                    moves += unbuild._create_move_from_bom_line(
                        line.product_id,
                        line.product_uom_id,
                        line_data["qty"],
                        bom_line_id=line.id,
                    )
        _debug.pipeline("unbuild_produce_moves", unbuilds=self, moves=moves)
        return moves

    def _create_move_from_existing_move(
        self, move, factor, location_id, location_dest_id
    ):
        return self.env["stock.move"].create(
            {
                "date": self.create_date,
                "product_id": move.product_id.id,
                "product_uom_qty": move.quantity * factor,
                "product_uom_id": move.product_uom_id.id,
                "procure_method": "make_to_stock",
                "location_dest_id": location_dest_id.id,
                "location_id": location_id.id,
                "warehouse_id": location_dest_id.warehouse_id.id,
                "unbuild_id": self.id,
                "company_id": move.company_id.id,
                "origin_returned_move_id": move.id,
            }
        )

    def _create_move_from_bom_line(
        self, product, product_uom_id, quantity, bom_line_id=False, byproduct_id=False
    ):
        product_prod_location = product.with_company(
            self.company_id
        ).property_stock_production
        location_id = (bom_line_id and product_prod_location) or self.location_id
        location_dest_id = (
            bom_line_id and self.location_dest_id
        ) or product_prod_location
        warehouse = location_dest_id.warehouse_id
        return self.env["stock.move"].create(
            {
                "date": self.create_date,
                "bom_line_id": bom_line_id,
                "byproduct_id": byproduct_id,
                "product_id": product.id,
                "product_uom_qty": quantity,
                "product_uom_id": product_uom_id.id,
                "procure_method": "make_to_stock",
                "location_dest_id": location_dest_id.id,
                "location_id": location_id.id,
                "warehouse_id": warehouse.id,
                "unbuild_id": self.id,
                "company_id": self.company_id.id,
            }
        )

    def action_validate(self):
        self.check_singleton()
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        available_qty = self.env["stock.quant"]._get_available_quantity(
            self.product_id, self.location_id, self.lot_id, strict=True
        )
        unbuild_qty = self.product_uom_id._get_quantity_in_unit(
            self.product_qty, self.product_id.uom_id
        )
        _debug.logic(
            "unbuild_availability",
            unbuild=self.id,
            available=available_qty,
            wanted=unbuild_qty,
        )
        if float_compare(available_qty, unbuild_qty, precision_digits=precision) >= 0:
            return self.action_unbuild()
        else:
            return {
                "name": _(
                    "%(product)s: Insufficient Quantity To Unbuild",
                    product=self.product_id.display_name,
                ),
                "view_mode": "form",
                "res_model": "stock.warn.insufficient.qty.unbuild",
                "view_id": self.env.ref(
                    "mrp.stock_warn_insufficient_qty_unbuild_form_view"
                ).id,
                "type": "ir.actions.act_window",
                "context": {
                    "default_product_id": self.product_id.id,
                    "default_location_id": self.location_id.id,
                    "default_unbuild_id": self.id,
                    "default_quantity": unbuild_qty,
                    "default_product_uom_name": self.product_id.uom_name,
                },
                "target": "new",
            }
