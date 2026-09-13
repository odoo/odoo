from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class StockReturnPickingLine(models.TransientModel):
    _name = "stock.return.picking.line"
    _rec_name = "product_id"
    _description = "Return Picking Line"

    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    move_quantity = fields.Float(
        related="move_id.quantity",
        string="Move Quantity",
    )
    quantity = fields.Float(
        digits="Product Unit",
        default=1,
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_uom_id",
    )
    wizard_id = fields.Many2one(comodel_name="stock.return.picking")
    move_id = fields.Many2one(comodel_name="stock.move")

    @api.depends("move_id.product_uom_id", "product_id.uom_id")
    def _compute_uom_id(self):
        for line in self:
            line.uom_id = line.move_id.product_uom_id or line.product_id.uom_id

    def _prepare_move_default_values(self, new_picking):
        picking = new_picking or self.wizard_id.picking_id
        vals = {
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
            "product_uom_id": self.uom_id.id,
            "picking_id": picking.id,
            "state": "draft",
            "date": fields.Datetime.now(),
            "location_id": picking.location_id.id or self.move_id.location_dest_id.id,
            "location_dest_id": picking.location_dest_id.id
            or self.move_id.location_id.id,
            "location_final_id": False,
            "picking_type_id": picking.picking_type_id.id,
            "warehouse_id": picking.picking_type_id.warehouse_id.id,
            "origin_returned_move_id": self.move_id.id,
            "procure_method": "make_to_stock",
            "reference_ids": self.wizard_id.picking_id.reference_ids.ids,
        }
        if picking.picking_type_id.code == "outgoing":
            vals["partner_id"] = picking.partner_id.id
        return vals

    def _process_line(self, new_picking):
        self.check_singleton()
        if not self.uom_id.is_zero(self.quantity):
            vals = self._prepare_move_default_values(new_picking)

            if self.move_id:
                new_return_move = self.move_id.copy(vals)
                vals = {}
                move_orig_to_link = self.move_id.move_dest_ids.returned_move_ids
                move_orig_to_link |= self.move_id
                move_orig_to_link |= self.move_id.move_dest_ids.filtered(
                    lambda m: m.state != "cancel"
                ).move_orig_ids.filtered(lambda m: m.state != "cancel")
                move_dest_to_link = self.move_id.move_orig_ids.returned_move_ids
                move_dest_to_link |= (
                    self.move_id.move_orig_ids.returned_move_ids.move_orig_ids.filtered(
                        lambda m: m.state != "cancel"
                    ).move_dest_ids.filtered(lambda m: m.state != "cancel")
                )
                vals["move_orig_ids"] = [Command.link(m.id) for m in move_orig_to_link]
                vals["move_dest_ids"] = [Command.link(m.id) for m in move_dest_to_link]
                dbg.pipeline.debug(
                    "return line: move %s -> return move %s qty %s, orig %s dest %s",
                    self.move_id.id,
                    new_return_move.id,
                    self.quantity,
                    dbg.rec(move_orig_to_link),
                    dbg.rec(move_dest_to_link),
                )
                new_return_move.write(vals)
            else:
                dbg.pipeline.debug(
                    "return line without move: new move for product %s qty %s",
                    self.product_id.id,
                    self.quantity,
                )
                self.env["stock.move"].create(vals)
            return True
        return False


class StockReturnPicking(models.TransientModel):
    _name = "stock.return.picking"
    _description = "Return Picking"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if (
            self.env.context.get("active_id")
            and self.env.context.get("active_model") == "stock.picking"
        ):
            if len(self.env.context.get("active_ids", [])) > 1:
                raise UserError(_("You may only return one picking at a time."))
            picking = self.env["stock.picking"].browse(
                self.env.context.get("active_id")
            )
            if picking.exists():
                res.update({"picking_id": picking.id})
        return res

    picking_id = fields.Many2one(comodel_name="stock.picking")
    picking_type_code = fields.Selection(
        related="picking_id.picking_type_code",
        readonly=True,
    )
    product_return_moves = fields.One2many(
        comodel_name="stock.return.picking.line",
        inverse_name="wizard_id",
        string="Moves",
        compute="_compute_product_return_moves",
        precompute=True,
        store=True,
        readonly=False,
    )
    company_id = fields.Many2one(related="picking_id.company_id")

    @api.depends("picking_id")
    def _compute_product_return_moves(self):
        for wizard in self:
            if not wizard.picking_id:
                wizard.product_return_moves = [Command.clear()]
                continue
            product_return_moves = [Command.clear()]
            if not wizard.picking_id._can_return():
                raise UserError(_("You may only return Done pickings."))
            line_fields = list(self.env["stock.return.picking.line"]._fields)
            product_return_moves_data_tmpl = self.env[
                "stock.return.picking.line"
            ].default_get(line_fields)
            for move in wizard.picking_id.move_ids:
                if move.state == "cancel":
                    continue
                if move.location_dest_usage == "inventory":
                    continue
                product_return_moves_data = dict(product_return_moves_data_tmpl)
                product_return_moves_data.update(
                    wizard._prepare_stock_return_picking_line_vals_from_move(move)
                )
                product_return_moves.append(Command.create(product_return_moves_data))
            if len(product_return_moves) == 1:
                raise UserError(
                    _(
                        "No products to return (only lines in Done state and not fully returned yet can be returned)."
                    )
                )
            wizard.product_return_moves = product_return_moves

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        return {
            "product_id": stock_move.product_id.id,
            "quantity": 0,
            "move_id": stock_move.id,
        }

    def _prepare_picking_default_values(self):
        return self._prepare_picking_default_values_based_on(self.picking_id)

    def _prepare_picking_default_values_based_on(self, picking):
        location = picking.location_dest_id
        return_type = picking.picking_type_id.return_picking_type_id
        if return_type and return_type.code == "incoming":
            location_dest = return_type.default_location_dest_id
        else:
            location_dest = picking.location_id

        return {
            "move_ids": [],
            "picking_type_id": return_type.id or picking.picking_type_id.id,
            "state": "draft",
            "return_id": picking.id,
            "origin": _("Return of %(picking_name)s", picking_name=picking.name),
            "location_id": location.id,
            "location_dest_id": location_dest.id,
        }

    @dbg.timed
    def _create_return(self):
        dbg.pipeline.debug(
            "_create_return from picking %s: %d lines",
            self.picking_id.id,
            len(self.product_return_moves),
        )
        if self.picking_id:
            for return_move in self.product_return_moves.move_id:
                return_move.move_dest_ids.filtered(
                    lambda m: m.state not in ("done", "cancel")
                )._unreserve()

            new_picking = self.picking_id.copy(self._prepare_picking_default_values())
            new_picking.user_id = False
            new_picking.message_post_with_source(
                "mail.message_origin_link",
                render_values={"self": new_picking, "origin": self.picking_id},
                subtype_xmlid="mail.mt_note",
            )
        else:
            new_picking = self.env["stock.picking"].create(
                self._prepare_picking_default_values()
            )

        returned_lines = False
        for return_line in self.product_return_moves:
            if return_line._process_line(new_picking):
                returned_lines = True
        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        dbg.pipeline.debug(
            "_create_return -> confirm + assign picking %s", new_picking.id
        )
        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking

    @dbg.timed
    def _create_exchange(self, return_picking):
        exchange_picking = return_picking.copy(
            self._prepare_picking_default_values_based_on(return_picking)
        )
        dbg.pipeline.debug(
            "_create_exchange: return %s -> exchange %s",
            return_picking.id,
            exchange_picking.id,
        )
        exchange_picking.user_id = False
        exchange_picking.message_post_with_source(
            "mail.message_origin_link",
            render_values={"self": exchange_picking, "origin": return_picking},
            subtype_xmlid="mail.mt_note",
        )
        for return_line in self.product_return_moves:
            return_line._process_line(exchange_picking)

        exchange_picking.move_ids.write(
            {
                "origin_returned_move_id": False,
                "move_orig_ids": False,
            }
        )
        exchange_picking.action_confirm()
        exchange_picking.action_assign()
        return exchange_picking

    def action_create_returns(self):
        self.check_singleton()
        new_picking = self._create_return()
        return {
            "name": _("Returned Picking"),
            "view_mode": "form",
            "res_model": "stock.picking",
            "res_id": new_picking.id,
            "type": "ir.actions.act_window",
            "context": self.env.context,
        }

    def action_create_returns_all(self):
        self.check_singleton()
        for return_move in self.product_return_moves:
            stock_move = return_move.move_id
            if (
                not stock_move
                or stock_move.state == "cancel"
                or stock_move.location_dest_usage == "inventory"
            ):
                continue
            quantity = stock_move.quantity
            for move in stock_move.move_dest_ids:
                if (
                    not move.origin_returned_move_id
                    or move.origin_returned_move_id != stock_move
                ):
                    continue
                quantity -= move.quantity
            quantity = max(stock_move.product_uom_id.round(quantity), 0)
            dbg.logic.debug(
                "action_create_returns_all: move %s returnable %s",
                stock_move.id,
                quantity,
            )
            return_move.quantity = quantity
        return self.action_create_returns()

    def action_create_exchanges(self):
        action = self.action_create_returns()
        if self.picking_id.picking_type_id.code == "incoming":
            return_picking = self.env["stock.picking"].browse([action["res_id"]])
            self._create_exchange(return_picking)
            return action

        proc_list = []
        for line in self.product_return_moves:
            if not line.move_id:
                continue
            proc_values = self._prepare_procurement_vals(line)
            proc_list.append(
                self.env["stock.rule"].Procurement(
                    line.product_id,
                    line.quantity,
                    line.uom_id,
                    line.move_id.location_dest_id or self.picking_id.location_dest_id,
                    line.product_id.display_name,
                    self.picking_id.origin,
                    self.picking_id.company_id,
                    proc_values,
                )
            )
        if proc_list:
            dbg.pipeline.debug(
                "action_create_exchanges -> stock.rule.run %d procurements",
                len(proc_list),
            )
            self.env["stock.rule"].run(proc_list)
        return action

    def _prepare_procurement_vals(self, line):
        self.check_singleton()
        return {
            "reference_ids": self.picking_id.reference_ids,
            "date_planned": line.move_id.date or fields.Datetime.now(),
            "warehouse_id": self.picking_id.picking_type_id.warehouse_id,
            "partner_id": self.picking_id.partner_id.id,
            "location_final_id": line.move_id.location_final_id
            or self.picking_id.location_dest_id,
            "company_id": self.picking_id.company_id,
        }
