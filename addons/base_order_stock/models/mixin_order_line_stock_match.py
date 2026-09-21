from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_compare, float_is_zero

SPLITTABLE_STATES = ("waiting", "confirmed", "partially_available", "assigned")


_debug = DebugLog(__name__)


class MixinOrderLineStockMatch(models.AbstractModel):
    _name = "mixin.order.line.stock.match"
    _description = "Order Line & Stock Move Matching"

    _order_line_table = ""
    _order_table = ""
    _link_column = ""
    _move_usage = ""
    _move_usage_side = ""
    _date_expected_field = ""

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
    )

    order_line_id = fields.Many2one(
        comodel_name="mixin.order.line.fields",
        readonly=True,
    )
    order_id = fields.Many2one(
        comodel_name="mixin.order",
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name="stock.move",
        readonly=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        readonly=True,
    )

    state = fields.Char(readonly=True)
    transfer_state = fields.Char(readonly=True)
    reference = fields.Char(compute="_compute_reference")

    line_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        readonly=True,
    )
    line_qty = fields.Float(readonly=True)
    qty_transferred = fields.Float(readonly=True)
    qty_to_transfer = fields.Float(
        string="Qty to transfer",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        compute="_compute_product_uom_qty",
        inverse="_inverse_product_uom_qty",
        readonly=False,
    )

    date_expected = fields.Datetime(readonly=True)
    lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        compute="_compute_lot_ids",
    )
    transferred_qty = fields.Float(compute="_compute_side_quantities")
    ordered_qty = fields.Float(compute="_compute_side_quantities")

    @api.depends("line_qty", "move_id", "order_id")
    def _compute_side_quantities(self):
        for line in self:
            line.transferred_qty = line.line_qty if line.move_id else False
            line.ordered_qty = line.line_qty if line.order_id else False

    @api.depends(
        "order_id.display_name", "picking_id.display_name", "move_id.display_name"
    )
    def _compute_reference(self):
        for line in self:
            line.reference = (
                line.order_id.display_name
                or line.picking_id.display_name
                or line.move_id.display_name
            )

    @api.depends(
        "product_id.display_name", "move_id.description_picking", "order_line_id.name"
    )
    def _compute_display_name(self):
        for line in self:
            line.display_name = (
                line.product_id.display_name
                or line.move_id.description_picking
                or line.order_line_id.name
            )

    @api.depends("move_id.move_line_ids.lot_id")
    def _compute_lot_ids(self):
        for line in self:
            line.lot_ids = line.move_id.move_line_ids.lot_id

    @api.depends("product_id", "line_uom_id", "line_qty", "product_uom_id")
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id:
                line.product_uom_qty = line.line_uom_id._get_quantity_in_unit(
                    line.line_qty, line.product_uom_id
                )
            else:
                line.product_uom_qty = line.line_qty

    @api.onchange("product_uom_qty")
    def _inverse_product_uom_qty(self):
        for line in self:
            if line.product_id:
                qty = line.product_uom_id._get_quantity_in_unit(
                    line.product_uom_qty, line.line_uom_id
                )
            else:
                qty = line.product_uom_qty
            if line.move_id:
                if line.move_id.state == "done":
                    line.move_id.quantity = qty
                else:
                    line.move_id.product_uom_qty = qty
            else:
                line.order_line_id.product_qty = qty

    def action_view_line(self):
        self.check_singleton()
        if self.picking_id:
            record = self.picking_id
        elif self.move_id:
            record = self.move_id
        else:
            record = self.order_id
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "view_mode": "form",
            "res_id": record.id,
        }

    def _get_no_order_line_message(self):
        return _("You must select at least one order line to match or transfer.")

    def _get_no_move_message(self):
        return _("You must select at least one stock move to match.")

    def _action_create_moves_from_order_lines(self, order_lines):
        _debug.pipeline("moves_from_order_lines", lines=order_lines)
        raise NotImplementedError(
            f"{self._name} must implement _action_create_moves_from_order_lines()",
        )

    def _rank_move_for_line(self, order_line, move):
        _debug.logic("move_rank_for_line", line=order_line.id, move=move.id)
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        residual = order_line.qty_to_transfer
        move_qty = move.product_uom_id._get_quantity_in_unit(
            move.quantity if move.state == "done" else move.product_uom_qty,
            order_line.product_uom_id,
            rounding_method="HALF-UP",
        )
        expected_lots = order_line.move_ids.move_line_ids.lot_id
        move_lots = move.move_line_ids.lot_id
        expected_date = self._get_line_date_expected(order_line)
        return (
            0 if expected_lots and move_lots and (expected_lots & move_lots) else 1,
            self._get_location_rank(order_line, move),
            0
            if float_compare(move_qty, residual, precision_digits=precision) == 0
            else 1,
            abs((move.date - expected_date).total_seconds())
            if move.date and expected_date
            else float("inf"),
        )

    def _get_location_rank(self, order_line, move):
        return 1

    def _get_line_date_expected(self, order_line):
        """Return the date `_rank_move_for_line` compares against `move.date`.

        This is the ranking date, independent from `_select_order_line_date`
        below, which feeds the grid's displayed `date_expected` column. The
        two are not guaranteed to be the same value: a concrete model may
        display one field (e.g. an order-level commitment date) while ranking
        on another (e.g. a line-level planned date), when no single field
        serves both purposes.
        """
        if not self._date_expected_field:
            return False
        return order_line[self._date_expected_field]

    def _link_move_to_line(self, move, order_line, over_transferred):
        _debug.pipeline(
            "move_linked_to_line",
            move=move.id,
            line=order_line.id,
            over=over_transferred,
        )
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        residual = order_line.qty_to_transfer
        move_qty = move.product_uom_id._get_quantity_in_unit(
            move.quantity if move.state == "done" else move.product_uom_qty,
            order_line.product_uom_id,
            rounding_method="HALF-UP",
        )
        if float_is_zero(residual, precision_digits=precision):
            move[self._link_column] = order_line.id
            if not float_is_zero(move_qty, precision_digits=precision):
                over_transferred.append((order_line, move, move_qty))
            return move.browse()

        excess = float_compare(move_qty, residual, precision_digits=precision)
        if excess <= 0:
            move[self._link_column] = order_line.id
            return move.browse()

        if move.state in SPLITTABLE_STATES:
            residual_ref = order_line.product_uom_id._get_quantity_in_unit(
                residual, move.product_id.uom_id, rounding_method="HALF-UP"
            )
            split_vals = move._split(move.product_qty - residual_ref)
            move[self._link_column] = order_line.id
            if not split_vals:
                return move.browse()
            excess_move = move.create(split_vals)
            excess_move.write({"state": "confirmed", self._link_column: False})
            return excess_move

        move[self._link_column] = order_line.id
        over_transferred.append((order_line, move, move_qty - residual))
        return move.browse()

    def action_match_lines(self):
        _debug.pipeline("order_line_match_enter", records=self)
        if not self.order_line_id:
            raise UserError(self._get_no_order_line_message())
        if not self.move_id:
            return self._action_create_moves_from_order_lines(self.order_line_id)

        lines_by_product = self.order_line_id.grouped("product_id")
        moves_by_product = self.move_id.grouped("product_id")
        over_transferred = []

        for product, order_lines in lines_by_product.items():
            available = moves_by_product.get(product)
            if not available:
                continue
            remaining = list(available)
            for order_line in order_lines:
                if not remaining:
                    break
                remaining.sort(key=lambda m: self._rank_move_for_line(order_line, m))
                move = remaining.pop(0)
                leftover = self._link_move_to_line(move, order_line, over_transferred)
                if leftover:
                    remaining.append(leftover)

        if over_transferred:
            self._warn_over_transferred(over_transferred)
        return None

    def _warn_over_transferred(self, over_transferred):
        _debug.logic("over_transferred_warning", records=self)
        details = "\n".join(
            _(
                "%(product)s: %(move)s exceeds %(line)s by %(excess)s",
                product=order_line.product_id.display_name,
                move=move.display_name,
                line=order_line.order_id.display_name,
                excess=excess,
            )
            for order_line, move, excess in over_transferred
        )
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "type": "warning",
                "title": _("Over-transferred lines"),
                "message": details,
            },
        )

    @property
    def _table_query(self):
        return SQL(
            "%s UNION ALL %s",
            self._query_order_line(),
            self._query_move(),
        )

    @api.model
    def _query_order_line(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_order_line(),
            self._from_order_line(),
            self._where_order_line(),
        )

    @api.model
    def _select_order_line(self):
        return SQL(
            """
            ol.id,
            ol.id AS order_line_id,
            NULL::INTEGER AS move_id,
            NULL::INTEGER AS picking_id,
            o.company_id,
            ol.partner_id,
            ol.product_id,
            ol.product_qty AS line_qty,
            ol.product_uom_id AS line_uom_id,
            ol.qty_transferred,
            ol.qty_to_transfer,
            ol.transfer_state,
            o.id AS order_id,
            %(date_expected)s AS date_expected,
            o.state
            """,
            date_expected=self._select_order_line_date(),
        )

    @api.model
    def _select_order_line_date(self):
        """Return the SQL expression for the grid's displayed `date_expected`.

        This is the display date, independent from `_date_expected_field`/
        `_get_line_date_expected` above, which feeds `_rank_move_for_line`'s
        ranking. See that method's docstring for why the two may differ.
        """
        return SQL("NULL::TIMESTAMP")

    @api.model
    def _from_order_line(self):
        return SQL(
            """
            %(order_line)s ol
            JOIN %(order)s o ON ol.order_id = o.id
            JOIN product_product pp ON ol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            """,
            order_line=SQL.identifier(self._order_line_table),
            order=SQL.identifier(self._order_table),
        )

    @api.model
    def _where_order_line(self):
        return SQL(
            """
            o.state = 'done'
            AND COALESCE(ol.display_type, '') = ''
            AND NOT COALESCE(ol.is_downpayment, FALSE)
            AND pt.type = 'consu'
            AND ol.qty_to_transfer > 0
            """,
        )

    @api.model
    def _query_move(self):
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_move(),
            self._from_move(),
            self._where_move(),
        )

    @api.model
    def _select_move(self):
        return SQL(
            """
            -sm.id AS id,
            NULL::INTEGER AS order_line_id,
            sm.id AS move_id,
            sm.picking_id,
            sm.company_id,
            COALESCE(sm.partner_id, sp.partner_id) AS partner_id,
            sm.product_id,
            CASE WHEN sm.state = 'done' THEN sm.quantity ELSE sm.product_uom_qty END
                AS line_qty,
            sm.product_uom_id AS line_uom_id,
            NULL::NUMERIC AS qty_transferred,
            NULL::NUMERIC AS qty_to_transfer,
            NULL::VARCHAR AS transfer_state,
            NULL::INTEGER AS order_id,
            sm.date AS date_expected,
            sm.state
            """,
        )

    @api.model
    def _from_move(self):
        return SQL(
            """
            stock_move sm
            JOIN stock_location sl ON sm.%(column)s = sl.id
            LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
            """,
            column=SQL.identifier(
                "location_id"
                if self._move_usage_side == "source"
                else "location_dest_id"
            ),
        )

    @api.model
    def _where_move(self):
        return SQL(
            """
            sm.%(link)s IS NULL
            AND sl.usage = %(usage)s
            AND sm.state NOT IN ('draft', 'cancel')
            AND sm.scrap_id IS NULL
            AND NOT COALESCE(sm.is_inventory, FALSE)
            """,
            link=SQL.identifier(self._link_column),
            usage=self._move_usage,
        )
