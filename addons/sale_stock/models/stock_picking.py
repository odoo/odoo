from odoo import Command, _, api, fields, models
from odoo.db.schema import column_exists, create_column


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        compute="_compute_sale_id",
        inverse="_inverse_sale_id",
        store=True,
        index="btree_not_null",
    )

    def _get_fields_linking_orders(self):
        return ["sale_id", *super()._get_fields_linking_orders()]

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_picking", "sale_id"):
            create_column(self.env.cr, "stock_picking", "sale_id", "int4")
        return super()._auto_init()

    @api.depends(
        "reference_ids.sale_ids",
        "move_ids.sale_line_id.order_id",
        "move_ids.location_id.usage",
        "move_ids.location_dest_id.usage",
        "move_ids.move_orig_ids",
    )
    def _compute_sale_id(self):
        for picking in self:
            sale_order = picking.move_ids.sale_line_id.order_id[:1]
            if (
                not sale_order
                and picking.reference_ids.sale_ids
                and not picking._is_on_manufacturing_route()
                and not picking._is_replenishment_receipt_step()
            ):
                sale_order = picking.reference_ids.sale_ids[:1]
            picking.sale_id = sale_order

    @api.depends("move_ids.sale_line_id.order_id.picking_policy")
    def _compute_move_type(self):
        super()._compute_move_type()
        for picking in self:
            sale_orders = picking.move_ids.sale_line_id.order_id
            if sale_orders:
                if any(so.picking_policy == "direct" for so in sale_orders):
                    picking.move_type = "direct"
                else:
                    picking.move_type = "one"

    def _is_on_manufacturing_route(self):
        self.check_singleton()
        return False

    def _is_replenishment_receipt_step(self):
        # What an MTO sale triggers upstream -- a vendor purchase, an inter-company or
        # inter-warehouse resupply -- shares the sale's reference. Its receipt, and any
        # internal step fed by it, belongs to that replenishment, not to the sale.
        self.check_singleton()
        moves = self.move_ids
        visited = self.env["stock.move"]
        while moves:
            if any(
                move.location_id.usage in ("supplier", "transit")
                and move.location_dest_id.usage != "customer"
                for move in moves
            ):
                return True
            visited |= moves
            moves = moves.move_orig_ids - visited
        return False

    def _inverse_sale_id(self):
        if self.reference_ids:
            if self.sale_id:
                self.reference_ids.sudo().sale_ids = [Command.link(self.sale_id.id)]
            else:
                sale_order = self.move_ids.sale_line_id.order_id
                if len(sale_order) == 1:
                    self.reference_ids.sudo().sale_ids = [Command.unlink(sale_order.id)]
        elif self.sale_id:
            reference = (
                self.env["stock.reference"]
                .sudo()
                .create(
                    {
                        "sale_ids": [Command.link(self.sale_id.id)],
                        "name": self.sale_id.name,
                    },
                )
            )
            self._add_reference(reference)
        self.move_ids._update_sale_lines_for_order(self.sale_id)

    def _log_less_quantities_than_expected(self, moves):
        def _get_groupby_keys(sale_line):
            return (sale_line.order_id, sale_line.order_id.user_id)

        def _render_note_exception_quantity(moves_information):
            origin_moves = self.env["stock.move"].browse(
                [
                    move.id
                    for move_orig in moves_information.values()
                    for move in move_orig[0]
                ],
            )
            origin_picking = origin_moves.mapped("picking_id")
            values = {
                "origin_moves": origin_moves,
                "origin_picking": origin_picking,
                "moves_information": moves_information.values(),
            }
            return self.env["ir.qweb"]._render(
                "sale_stock.exception_on_picking", values
            )

        documents = self.sudo()._get_log_activity_documents(
            moves, "sale_line_id", "DOWN", _get_groupby_keys
        )
        self._log_activity(_render_note_exception_quantity, documents)

        return super()._log_less_quantities_than_expected(moves)

    def action_sale_matching(self):
        return self._get_action_transfer_matching(
            _("Sales Matching"),
            "sale.delivery.line.match",
            "sale_stock.sale_delivery_line_match_list",
        )
