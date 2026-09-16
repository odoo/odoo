import contextlib
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_is_zero
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "mixin.order.line.stock"]

    def _get_merge_date_field(self):
        return "date_planned"

    is_storable = fields.Boolean(
        related="product_id.is_storable",
        depends=["product_id"],
    )
    transfer_state = fields.Selection(
        selection=[
            ("no", "Nothing to deliver"),
            ("to do", "To deliver"),
            ("partial", "Partially delivered"),
            ("done", "Fully delivered"),
            ("over done", "Over delivered"),
        ],
        string="Delivery Status",
    )
    customer_lead = fields.Float(
        compute="_compute_customer_lead",
        inverse="_inverse_customer_lead",
        precompute=True,
        store=True,
        readonly=False,
    )
    route_ids = fields.Many2many(
        comodel_name="stock.route",
        string="Routes",
        domain=[("sale_selectable", "=", True)],
        ondelete="restrict",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_id",
        store=True,
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="sale_line_id",
        string="Stock Moves",
    )
    date_planned = fields.Datetime(compute="_compute_qty_at_date")
    date_planned_forecast = fields.Datetime(compute="_compute_qty_at_date")
    qty_available_today = fields.Float(
        digits="Product Unit",
        compute="_compute_qty_at_date",
    )
    qty_available_virtual_at_date = fields.Float(
        digits="Product Unit",
        compute="_compute_qty_at_date",
    )
    qty_free_today = fields.Float(
        digits="Product Unit",
        compute="_compute_qty_at_date",
    )
    display_qty_widget = fields.Boolean(
        compute="_compute_display_qty_widget",
        compute_sudo=False,
    )
    is_mto = fields.Boolean(compute="_compute_is_mto")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        _debug.lifecycle("create", lines=lines, rows=len(vals_list))
        lines.filtered(lambda line: line.state == "done")._action_launch_stock_rule()
        return lines

    def write(self, vals):
        lines = self.env["sale.order.line"]

        if "product_qty" in vals:
            lines = self.filtered(lambda r: r.state == "done" and not r.is_expense)

        previous_product_qty = {line.id: line.product_qty for line in lines}
        res = super().write(vals)

        if lines:
            _debug.pipeline("relaunch_stock_rules", lines=lines)
            lines._action_launch_stock_rule(
                previous_product_qty=previous_product_qty,
            )

        return res

    def _compute_invoice_state(self):
        def is_moves_done(moves):
            at_least_one_done = False
            for move in moves:
                if move.state not in ["done", "cancel"]:
                    return False
                at_least_one_done = at_least_one_done or move.state == "done"
            return at_least_one_done

        super()._compute_invoice_state()

        for line in self:
            if (
                line.state == "done"
                and line.invoice_state == "no"
                and line.product_id.type == "consu"
                and line.product_id.invoice_policy == "transferred"
                and line.move_ids
                and is_moves_done(line.move_ids)
                and not float_is_zero(
                    line.qty_transferred,
                    precision_rounding=line.product_uom_id.rounding,
                )
            ):
                _debug.logic(
                    "invoice_state_forced_done", line=line, by="moves_all_done"
                )
                line.invoice_state = "done"

    @api.depends("product_id")
    def _compute_customer_lead(self):
        super()._compute_customer_lead()
        for line in self.filtered(lambda x: not x.display_type):
            line.customer_lead = line.product_id.sale_delay

    @api.depends("route_ids", "order_id.warehouse_id", "product_id")
    def _compute_warehouse_id(self):
        for line in self:
            line.warehouse_id = line.order_id.warehouse_id

        routed = self.filtered("route_ids")
        by_key = defaultdict(self.browse)
        for line in routed:
            by_key[
                (
                    tuple(sorted(line.route_ids.ids)),
                    line.order_id.partner_shipping_id.property_stock_customer.id,
                )
            ] |= line

        for (route_ids, destination_id), lines in by_key.items():
            rules = self.env["stock.rule"].search(  # noqa: E8507 - one query per distinct (routes, destination); lines sharing one were merged above
                domain=Domain.AND(
                    [
                        [("route_id", "in", list(route_ids))],
                        [
                            (
                                "location_dest_id",
                                "in",
                                [destination_id] if destination_id else [],
                            ),
                            ("action", "!=", "push"),
                        ],
                    ],
                ),
                order="route_sequence, sequence",
            )
            if not rules:
                continue
            for line in lines:
                best = sorted(
                    rules,
                    key=lambda rule, line=line: (
                        0
                        if rule.location_src_id.warehouse_id
                        in (False, line.order_id.warehouse_id)
                        else 1
                    ),
                )
                line.warehouse_id = best[0].location_src_id.warehouse_id
                _debug.logic(
                    "line_warehouse_from_rule",
                    line=line,
                    rule=best[0],
                    warehouse=line.warehouse_id,
                )

    @api.depends("move_ids")
    def _compute_product_readonly(self):
        super()._compute_product_readonly()
        for line in self:
            if line.move_ids.filtered(lambda m: m.state != "cancel"):
                line.product_readonly = True

    @api.depends(
        "product_qty",
        "move_ids.state",
        "move_ids.location_dest_usage",
        "move_ids.product_uom_id",
        "move_ids.quantity",
    )
    def _compute_qty_transferred(self):
        lines_by_stock_move = self.filtered(
            lambda line: line.qty_transferred_method == "stock_move",
        )
        super(SaleOrderLine, self - lines_by_stock_move)._compute_qty_transferred()

        for line in lines_by_stock_move:
            line.qty_transferred = line._get_transferred_qty_from_moves()

    @api.depends(
        "state",
        "product_id.is_storable",
        "move_ids",
        "move_ids.state",
        "qty_to_transfer",
    )
    def _compute_display_qty_widget(self):
        self.display_qty_widget = False

        for line in self.filtered(lambda x: x.product_id and x.product_id.is_storable):
            if line.state == "draft" or (
                line.state == "done"
                and line.qty_to_transfer > 0
                and any(m.state not in ["done", "cancel"] for m in line.move_ids)
            ):
                line.display_qty_widget = True

    @api.depends(
        "route_ids",
        "warehouse_id",
        "product_id",
        "product_id.route_ids",
        "display_qty_widget",
    )
    def _compute_is_mto(self):
        self.is_mto = False
        for line in self.filtered(lambda x: x.display_qty_widget):
            product_routes = line.route_ids or (
                line.product_id.route_ids + line.product_id.categ_id.total_route_ids
            )
            mto_route = line.warehouse_id.mto_pull_id.route_id
            if not mto_route:
                with contextlib.suppress(UserError):
                    mto_route = self.env["stock.warehouse"]._get_or_create_global_route(
                        "stock.route_warehouse0_mto",
                        _("Replenish on Order (MTO)"),
                        create=False,
                    )

            if mto_route and mto_route in product_routes:
                line.is_mto = True
                _debug.logic("line_is_mto", line=line, route=mto_route)

    @api.depends(
        "order_id.date_commitment",
        "warehouse_id",
        "product_id",
        "product_uom_id",
        "product_qty",
        "customer_lead",
        "display_qty_widget",
        "move_ids.date_planned_forecast",
        "move_ids.forecast_availability",
    )
    def _compute_qty_at_date(self):
        self.qty_available_virtual_at_date = False
        self.date_planned = False
        self.date_planned_forecast = False
        self.qty_free_today = False
        self.qty_available_today = False

        lines_display_qty_widget = self.filtered(lambda x: x.display_qty_widget)

        if not lines_display_qty_widget:
            _debug.logic("qty_at_date_skipped", lines=self, reason="no_qty_widget")
            return

        _debug.perf.count(
            "qty_at_date", lines=len(self), with_widget=len(lines_display_qty_widget)
        )
        all_moves = self.env["stock.move"]
        line_all_moves_cached = {}

        for line in lines_display_qty_widget.filtered(lambda l: l.state == "done"):
            combined_moves = (
                line.move_ids
                | self.env["stock.move"].browse(line.move_ids._rollup_move_orig_ids())
            ).filtered(lambda m, line=line: m.product_id == line.product_id)
            all_moves |= combined_moves
            line_all_moves_cached[line.id] = combined_moves

        date_planned_forecast_per_move = {
            m.id: m.date_planned_forecast for m in all_moves
        }

        for line in lines_display_qty_widget.filtered(lambda l: l.state == "done"):
            combined_moves = line_all_moves_cached.get(line.id, ())
            moves = combined_moves.filtered(
                lambda m: m.state not in ("cancel", "done"),
            )
            qty_available_today = 0
            qty_free_today = 0

            for move in moves:
                qty_available_today += move.product_uom_id._get_quantity_estimate(
                    move.quantity,
                    line.product_uom_id,
                )
                qty_free_today += move.product_id.uom_id._get_quantity_estimate(
                    move.forecast_availability,
                    line.product_uom_id,
                )

            line.qty_available_virtual_at_date = False
            line.qty_available_today = qty_available_today
            line.qty_free_today = qty_free_today
            line.date_planned = (
                line.order_id.date_commitment or line._get_date_planned()
            )
            line.date_planned_forecast = max(
                (
                    date_planned_forecast_per_move[move.id]
                    for move in moves
                    if date_planned_forecast_per_move[move.id]
                ),
                default=False,
            )

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env["sale.order.line"])

        for line in lines_display_qty_widget.filtered(lambda l: l.state == "draft"):
            grouped_lines[
                (
                    line.warehouse_id.id,
                    line.order_id.date_commitment or line._get_date_planned(),
                )
            ] |= line

        for (warehouse, date_planned), lines in grouped_lines.items():
            product_qties = lines._read_qties(date_planned, warehouse)
            qties_per_product = {
                product["id"]: (
                    product["qty_available"],
                    product["qty_free"],
                    product["qty_available_virtual"],
                )
                for product in product_qties
            }

            for line in lines:
                line.date_planned = date_planned
                qty_available_today, qty_free_today, qty_available_virtual_at_date = (
                    qties_per_product[line.product_id.id]
                )
                line.qty_available_today = (
                    qty_available_today - qty_processed_per_product[line.product_id.id]
                )
                line.qty_free_today = (
                    qty_free_today - qty_processed_per_product[line.product_id.id]
                )
                line.qty_available_virtual_at_date = (
                    qty_available_virtual_at_date
                    - qty_processed_per_product[line.product_id.id]
                )
                line.date_planned_forecast = False
                product_qty = line.product_qty

                if line.product_uom_id != line.product_id.uom_id:
                    line.qty_available_today = (
                        line.product_id.uom_id._get_quantity_estimate(
                            line.qty_available_today,
                            line.product_uom_id,
                        )
                    )
                    line.qty_free_today = (
                        line.product_id.uom_id._get_quantity_estimate(
                            line.qty_free_today,
                            line.product_uom_id,
                        )
                    )
                    line.qty_available_virtual_at_date = (
                        line.product_id.uom_id._get_quantity_estimate(
                            line.qty_available_virtual_at_date,
                            line.product_uom_id,
                        )
                    )
                    product_qty = line.product_uom_id._get_quantity_estimate(
                        product_qty,
                        line.product_id.uom_id,
                    )

                qty_processed_per_product[line.product_id.id] += product_qty

    def _inverse_customer_lead(self):
        for line in self:
            if line.state == "done" and not line.order_id.date_commitment:
                _debug.lifecycle(
                    "move_deadline_from_lead", line=line, moves=line.move_ids
                )
                line.move_ids.date_deadline = line.order_id.date_order + timedelta(
                    days=line.customer_lead or 0.0,
                )

    def _action_launch_stock_rule(self, *, previous_product_qty=False):
        if self.env.context.get("skip_procurement"):
            _debug.logic("stock_rules_skipped", lines=self, reason="skip_procurement")
            return True

        precision = self.env["decimal.precision"].get_precision("Product Unit")
        procuring = []
        for line in self:
            line = line.with_company(line.company_id)
            if (
                line.state != "done"
                or line.order_id.locked
                or line.product_id.type != "consu"
            ):
                continue

            qty = line._get_procurement_qty(previous_product_qty)

            if float_compare(qty, line.product_qty, precision_digits=precision) == 0:
                _debug.logic("line_not_procured", line=line, reason="already_covered")
                continue
            procuring.append((line, qty))

        # one reference per order that has none yet, created together
        first_line_by_order = {}
        for line, _qty in procuring:
            if not line.order_id.reference_ids:
                first_line_by_order.setdefault(line.order_id.id, line)
        if first_line_by_order:
            _debug.lifecycle(
                "stock_references_created", orders=len(first_line_by_order)
            )
            self.env["stock.reference"].sudo().create(
                [
                    line._prepare_reference_vals()
                    for line in first_line_by_order.values()
                ]
            )

        procurements = []
        for line, qty in procuring:
            values = line._prepare_procurement_vals()
            procurement_qty = line.product_qty - qty

            line_uom = line.product_uom_id
            quant_uom = line.product_id.uom_id
            procurement_qty, procurement_uom = line_uom._get_procurement_qty_and_uom(
                procurement_qty,
                quant_uom,
            )
            procurements += line._create_procurements(
                procurement_qty,
                procurement_uom,
                values,
            )
        if procurements:
            _debug.pipeline(
                "procurements_run", lines=self, procurements=len(procurements)
            )
            self.env["stock.rule"].run(procurements)

        pickings_to_confirm = self.order_id.picking_ids.filtered(
            lambda p: p.state not in ["cancel", "done"],
        )
        if pickings_to_confirm:
            _debug.lifecycle("pickings_confirmed", pickings=pickings_to_confirm)
            pickings_to_confirm.action_confirm()
        return True

    def _get_product_catalog_lines_data(self, **kwargs):
        res = super()._get_product_catalog_lines_data(**kwargs)
        res["deliveredQty"] = sum(
            self.mapped(
                lambda line: line.product_uom_id._get_quantity_report(
                    qty=line.qty_transferred,
                    to_unit=line.product_id.uom_id,
                ),
            ),
        )
        return res

    def _create_procurements(self, product_qty, procurement_uom, values):
        self.check_singleton()
        return [
            self.env["stock.rule"].Procurement(
                self.product_id,
                product_qty,
                procurement_uom,
                self._get_location_final(),
                self.product_id.display_name,
                self.order_id.name,
                self.order_id.company_id,
                values,
            ),
        ]

    def _get_location_final(self):
        self.check_singleton()
        return self.order_id.partner_shipping_id.property_stock_customer

    def _get_procurement_moves(self):
        return self._get_stock_moves_outgoing_incoming()

    def _get_procurement_qty(self, previous_product_qty=False):
        self.check_singleton()
        moves = self._get_transferable_moves()
        delivered, returned = self._get_stock_moves_outgoing_incoming()
        _debug.perf.count(
            "procurement_qty",
            line=self,
            moves=moves,
            delivered=delivered,
            returned=returned,
        )
        return (
            self._get_moves_qty_sum(delivered)
            - self._get_moves_qty_sum(returned)
            + self._get_pipeline_qty(moves - returned)
        )

    def _get_pipeline_qty(self, moves):
        self.check_singleton()
        balance = defaultdict(float)
        for move in moves:
            quantity = move.product_uom_id._get_quantity_in_unit(
                move.quantity if move.state == "done" else move.product_uom_qty,
                self.product_uom_id,
                rounding_method="HALF-UP",
            )
            balance[move.location_dest_id] += quantity
            balance[move.location_id] -= quantity

        rounding = self.product_uom_id.rounding
        return sum(
            quantity
            for location, quantity in balance.items()
            if quantity > 0
            and not float_is_zero(quantity, precision_rounding=rounding)
            and location.usage in ("internal", "transit")
            and not location._is_outgoing()
        )

    def _get_transferred_qty_from_moves(self):
        self.check_singleton()
        outgoing_moves, incoming_moves = self._get_stock_moves_outgoing_incoming()

        def total(moves):
            return sum(
                move.product_uom_id._get_quantity_reconcile(
                    move.quantity,
                    self.product_uom_id,
                    rounding_method="HALF-UP",
                )
                for move in moves
                if move.state == "done"
            )

        return total(outgoing_moves) - total(incoming_moves)

    def _get_stock_moves_outgoing_incoming(self):
        outgoing_moves = self.env["stock.move"]
        incoming_moves = self.env["stock.move"]
        moves = self._get_transferable_moves()

        if not moves:
            return outgoing_moves, incoming_moves

        if self.env.context.get("accrual_entry_date"):
            accrual_date = fields.Date.from_string(
                self.env.context["accrual_entry_date"],
            )
            moves = moves.filtered(
                lambda r: fields.Date.context_today(r, r.date) <= accrual_date,
            )

        for move in moves:
            if (
                not move._is_dropshipped_returned()
                and move.location_dest_id._is_outgoing()
            ):
                if not move.origin_returned_move_id or move.to_refund:
                    outgoing_moves |= move
            elif move.to_refund and (
                move._is_incoming() or move.location_id._is_outgoing()
            ):
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _prepare_procurement_vals(self):
        values = super()._prepare_procurement_vals()
        self.check_singleton()
        date_deadline = self.order_id.date_commitment or self._get_date_planned()
        date_planned = date_deadline - timedelta(
            days=self.order_id.company_id.security_lead,
        )
        values.update(
            {
                "origin": self.order_id.name,
                "reference_ids": self.order_id.reference_ids,
                "sale_line_id": self.id,
                "date_planned": date_planned,
                "date_deadline": date_deadline,
                "route_ids": self.route_ids,
                "warehouse_id": self.warehouse_id,
                "partner_id": self.order_id.partner_shipping_id.id,
                "location_final_id": self._get_location_final(),
                "product_description_variants": self.with_context(
                    lang=self.order_id.partner_id.lang,
                )
                ._get_line_multiline_description_variants()
                .strip(),
                "company_id": self.order_id.company_id,
                "sequence": self.sequence,
                "never_product_template_attribute_value_ids": self.product_no_variant_attribute_value_ids,
                "packaging_uom_id": self.product_uom_id,
            },
        )
        return values

    def _prepare_qty_transferred(self):
        delivered_qties = super()._prepare_qty_transferred()
        for line in self:
            if line.qty_transferred_method == "stock_move":
                delivered_qties[line] = line._get_transferred_qty_from_moves()
        return delivered_qties

    def _prepare_reference_vals(self):
        return {
            "name": self.order_id.name,
            "sale_ids": [Command.link(self.order_id.id)],
        }

    def _read_qties(self, date, wh):
        return (
            self.mapped("product_id")
            .with_context(to_date=date, warehouse_id=wh)
            .read(
                [
                    "qty_available",
                    "qty_free",
                    "qty_available_virtual",
                ],
            )
        )

    def _update_line_quantity(self, values):
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        line_products = self.filtered(lambda l: l.product_id.type == "consu")
        if (
            line_products.mapped("qty_transferred")
            and float_compare(
                values["product_qty"],
                max(line_products.mapped("qty_transferred")),
                precision_digits=precision,
            )
            == -1
        ):
            _debug.logic(
                "quantity_decrease_refused",
                lines=line_products,
                requested=values["product_qty"],
            )
            raise UserError(
                _(
                    "The ordered quantity of a sale order line cannot be decreased below the amount already delivered. Instead, create a return in your inventory.",
                ),
            )
        super()._update_line_quantity(values)

    def has_valued_move_ids(self):
        return (
            any(move.state not in ("cancel", "draft") for move in self.move_ids)
            or super().has_valued_move_ids()
        )
