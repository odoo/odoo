from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import float_compare
from odoo.tools.translate import _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    is_storable = fields.Boolean(
        related="product_id.is_storable",
        depends=["product_id"],
    )
    customer_lead = fields.Float(
        compute="_compute_customer_lead",
        store=True,
        precompute=True,
        readonly=False,
        inverse="_inverse_customer_lead",
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
    date_planned = fields.Datetime(
        compute="_compute_qty_at_date",
    )
    date_planned_forecast = fields.Datetime(
        compute="_compute_qty_at_date",
    )
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
    qty_to_transfer = fields.Float(
        digits="Product Unit",
        compute="_compute_qty_transferred",
        store=True,
    )
    display_qty_widget = fields.Boolean(
        compute="_compute_display_qty_widget",
        compute_sudo=False,
    )
    is_mto = fields.Boolean(
        compute="_compute_is_mto",
    )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.filtered(lambda line: line.state == "done")._action_launch_stock_rule()
        return lines

    def write(self, vals):
        lines = self.env["sale.order.line"]

        if "product_uom_qty" in vals:
            lines = self.filtered(lambda r: r.state == "done" and not r.is_expense)

        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        res = super().write(vals)

        if lines:
            lines._action_launch_stock_rule(
                previous_product_uom_qty=previous_product_uom_qty,
            )

        return res

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    #    def _compute_invoice_state(self):
    #        def check_moves_state(moves):
    #            # All moves states are either 'done' or 'cancel', and there is at least one 'done'
    #            at_least_one_done = False
    #            for move in moves:
    #                if move.state not in ["done", "cancel"]:
    #                    return False
    #                at_least_one_done = at_least_one_done or move.state == "done"
    #            return at_least_one_done
    #
    #        super()._compute_invoice_state()
    #        for line in self:
    #            # We handle the following specific situation: a physical product is partially delivered,
    #            # but we would like to set its invoice status to 'Fully Invoiced'. The use case is for
    #            # products sold by weight, where the delivered quantity rarely matches exactly the
    #            # quantity ordered.
    #            if (
    #                line.state == "done"
    #                and line.invoice_state == "no"
    #                and line.product_id.type in ["consu", "product"]
    #                and line.product_id.invoice_policy == "transferred"
    #                and line.move_ids
    #                and check_moves_state(line.move_ids)
    #            ):
    #                line.invoice_state = "done"

    @api.depends("product_id")
    def _compute_customer_lead(self):
        super()._compute_customer_lead()  # Reset customer_lead when the product is modified
        for line in self:
            line.customer_lead = line.product_id.sale_delay

    @api.depends("route_ids", "order_id.warehouse_id", "product_id")
    def _compute_warehouse_id(self):
        for line in self:
            line.warehouse_id = line.order_id.warehouse_id
            if line.route_ids:
                domain = [
                    (
                        "location_dest_id",
                        "in",
                        line.order_id.partner_shipping_id.property_stock_customer.ids,
                    ),
                    ("action", "!=", "push"),
                ]
                # prefer rules on the route itself even if they pull from a different warehouse than the SO's
                rules = sorted(
                    self.env["stock.rule"].search(
                        domain=Domain.AND(
                            [[("route_id", "in", line.route_ids.ids)], domain],
                        ),
                        order="route_sequence, sequence",
                    ),
                    # if there are multiple rules on the route, prefer those that pull from the SO's warehouse
                    # or those that are not warehouse specific
                    key=lambda rule: (
                        0
                        if rule.location_src_id.warehouse_id
                        in (False, line.order_id.warehouse_id)
                        else 1
                    ),
                )
                if rules:
                    line.warehouse_id = rules[0].location_src_id.warehouse_id

    @api.depends("move_ids")
    def _compute_product_readonly(self):
        """Extend product_readonly to consider stock moves.

        In addition to the base conditions (cancelled, downpayment, invoiced, delivered, locked),
        product becomes readonly if there are confirmed stock moves.
        """
        super()._compute_product_readonly()
        for line in self:
            if line.move_ids.filtered(lambda m: m.state != "cancel"):
                line.product_readonly = True

    @api.depends(
        "product_uom_qty",
        "move_ids.state",
        "move_ids.location_dest_usage",
        "move_ids.product_uom",
        "move_ids.quantity",
    )
    def _compute_qty_transferred(self):
        lines_by_stock_move = self.filtered(
            lambda line: line.qty_transferred_method == "stock_move",
        )
        super(SaleOrderLine, self - lines_by_stock_move)._compute_qty_transferred()

        for line in lines_by_stock_move:
            qty_transferred = 0.0
            outgoing_moves, incoming_moves = line._get_stock_moves_outgoing_incoming()

            for move in incoming_moves.filtered(lambda x: x.state == "done"):
                qty_transferred -= move.product_uom._compute_quantity(
                    move.quantity,
                    line.product_uom_id,
                    rounding_method="HALF-UP",
                )

            for move in outgoing_moves.filtered(lambda x: x.state == "done"):
                qty_transferred += move.product_uom._compute_quantity(
                    move.quantity,
                    line.product_uom_id,
                    rounding_method="HALF-UP",
                )

            line.qty_transferred = qty_transferred
            line.qty_to_transfer = max(0.0, line.product_uom_qty - qty_transferred)

    @api.depends(
        "state",
        "product_id.is_storable",
        "move_ids",
        "move_ids.state",
        "qty_to_transfer",
    )
    def _compute_display_qty_widget(self):
        """Compute the visibility of the inventory widget."""
        self.display_qty_widget = False

        for line in self.filtered(lambda x: x.product_id and x.product_id.is_storable):
            if (
                line.state == "draft"
                or line.state == "done"
                and line.qty_to_transfer > 0
                and any(m.state not in ["done", "cancel"] for m in line.move_ids)
            ):
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends(
        "route_ids",
        "warehouse_id",
        "product_id",
        "product_id.route_ids",
        "display_qty_widget",
    )
    def _compute_is_mto(self):
        """Verify the route of the product based on the warehouse
        set 'is_available' at True if the product availability in stock does
        not need to be verified, which is the case in MTO, Drop-Shipping
        """
        self.is_mto = False
        for line in self.filtered(lambda x: x.display_qty_widget):
            product_routes = line.route_ids or (
                line.product_id.route_ids + line.product_id.categ_id.total_route_ids
            )
            # Check MTO
            mto_route = line.warehouse_id.mto_pull_id.route_id
            if not mto_route:
                try:
                    mto_route = self.env[
                        "stock.warehouse"
                    ]._find_or_create_global_route(
                        "stock.route_warehouse0_mto",
                        _("Replenish on Order (MTO)"),
                        create=False,
                    )
                except UserError:
                    # if route MTO not found in ir_model_data, we treat the product as in MTS
                    pass

            if mto_route and mto_route in product_routes:
                line.is_mto = True
            else:
                line.is_mto = False

    @api.depends(
        "order_id.date_commitment",
        "warehouse_id",
        "product_id",
        "product_uom_id",
        "product_uom_qty",
        "customer_lead",
        "display_qty_widget",
        "move_ids.date_planned_forecast",
        "move_ids.forecast_availability",
    )
    def _compute_qty_at_date(self):
        """Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a date_commitment, we take it as delivery date
         2. The quotation hasn't date_commitment, we compute the estimated delivery
            date based on lead time"""
        self.qty_available_virtual_at_date = False
        self.date_planned = False
        self.date_planned_forecast = False
        self.qty_free_today = False
        self.qty_available_today = False

        lines_display_qty_widget = self.filtered(lambda x: x.display_qty_widget)

        if not lines_display_qty_widget:
            return

        treated = self.browse()
        all_moves = self.env["stock.move"]
        line_all_moves_cached = {}

        for line in lines_display_qty_widget.filtered(lambda l: l.state == "done"):
            combined_moves = line.move_ids | self.env["stock.move"].browse(
                line.move_ids._rollup_move_origs(),
            )
            all_moves |= combined_moves.filtered(
                lambda m: m.product_id == line.product_id,
            )
            line_all_moves_cached[line.id] = all_moves

        date_planned_forecast_per_move = {
            m.id: m.date_planned_forecast for m in all_moves
        }

        # If the state is already in sale the picking is created and a simple forecasted quantity isn't enough
        # Then used the forecasted data of the related stock.move
        for line in lines_display_qty_widget.filtered(lambda l: l.state == "done"):
            combined_moves = line_all_moves_cached.get(line.id, ())
            moves = combined_moves.filtered(
                lambda m: m.state not in ("cancel", "done"),
            )
            qty_available_today = 0
            qty_free_today = 0

            for move in moves:
                qty_available_today += move.product_uom._compute_quantity(
                    move.quantity,
                    line.product_uom_id,
                )
                qty_free_today += move.product_id.uom_id._compute_quantity(
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
            treated |= line

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env["sale.order.line"])

        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
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
                    product["free_qty"],
                    product["virtual_available"],
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
                product_qty = line.product_uom_qty

                if line.product_uom_id != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(
                        line.qty_available_today,
                        line.product_uom_id,
                    )
                    line.qty_free_today = line.product_id.uom_id._compute_quantity(
                        line.qty_free_today,
                        line.product_uom_id,
                    )
                    line.qty_available_virtual_at_date = (
                        line.product_id.uom_id._compute_quantity(
                            line.qty_available_virtual_at_date,
                            line.product_uom_id,
                        )
                    )
                    product_qty = line.product_uom_id._compute_quantity(
                        product_qty,
                        line.product_id.uom_id,
                    )

            treated |= lines

    # ------------------------------------------------------------
    # INVERSE METHODS
    # ------------------------------------------------------------

    def _inverse_customer_lead(self):
        for line in self:
            if line.state == "done" and not line.order_id.date_commitment:
                # Propagate deadline on related stock move
                line.move_ids.date_deadline = line.order_id.date_order + timedelta(
                    days=line.customer_lead or 0.0,
                )

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def _action_launch_stock_rule(self, *, previous_product_uom_qty=False):
        """
        Launch procurement run method with required/custom fields generated by a
        sale order line. procurement will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self.env.context.get("skip_procurement"):
            return True

        precision = self.env["decimal.precision"].precision_get("Product Unit")
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if (
                line.state != "done"
                or line.order_id.locked
                or line.product_id.type != "consu"
            ):
                continue

            qty = line._get_procurement_qty(previous_product_uom_qty)

            if (
                float_compare(qty, line.product_uom_qty, precision_digits=precision)
                == 0
            ):
                continue

            references = line.order_id.stock_reference_ids

            if not references:
                self.env["stock.reference"].create(line._prepare_reference_vals())

            values = line._prepare_procurement_vals()
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom_id
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(
                product_qty,
                quant_uom,
            )
            procurements += line._create_procurements(
                product_qty,
                procurement_uom,
                values,
            )
        if procurements:
            self.env["stock.rule"].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped("order_id")
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(
                lambda p: p.state not in ["cancel", "done"],
            )
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    # ------------------------------------------------------------
    # CATALOGUE
    # ------------------------------------------------------------

    # FIXME VFE this hook is supported on the order, not the order line
    def _get_action_add_from_catalog_extra_context(self, order):
        extra_context = super()._get_action_add_from_catalog_extra_context(order)
        extra_context.update(warehouse_id=order.warehouse_id.id)
        return extra_context

    def _get_product_catalog_lines_data(self, **kwargs):
        """Override of `sale` to add the delivered quantity.

        :rtype: dict
        :return: A dict with the following structure:
            {
                'deliveredQty': float,
                'quantity': float,
                'price': float,
                'readOnly': bool,
            }
        """
        res = super()._get_product_catalog_lines_data(**kwargs)
        res["deliveredQty"] = sum(
            self.mapped(
                lambda line: line.product_uom_id._compute_quantity(
                    qty=line.qty_transferred,
                    to_unit=line.product_id.uom_id,
                ),
            ),
        )
        return res

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _create_procurements(self, product_qty, procurement_uom, values):
        self.ensure_one()
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
        # Can be overriden for inter-company transactions.
        self.ensure_one()
        return self.order_id.partner_shipping_id.property_stock_customer

    def _get_procurement_qty(self, previous_product_uom_qty=False):
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_stock_moves_outgoing_incoming(
            strict=False,
        )
        for move in outgoing_moves:
            qty_to_compute = (
                move.quantity if move.state == "done" else move.product_uom_qty
            )
            qty += move.product_uom._compute_quantity(
                qty_to_compute,
                self.product_uom_id,
                rounding_method="HALF-UP",
            )
        for move in incoming_moves:
            qty_to_compute = (
                move.quantity if move.state == "done" else move.product_uom_qty
            )
            qty -= move.product_uom._compute_quantity(
                qty_to_compute,
                self.product_uom_id,
                rounding_method="HALF-UP",
            )
        return qty

    def _get_stock_moves_outgoing_incoming(self, strict=True):
        """Return the outgoing and incoming moves of the sale order line.
        @param strict: If True, only consider the moves that are strictly delivered to the customer (old behavior).
                       If False, consider the moves that were created through the initial rule of the delivery route,
                       to support the new push mechanism.
        """
        outgoing_moves = self.env["stock.move"]
        incoming_moves = self.env["stock.move"]
        moves = self.move_ids.filtered(
            lambda m: m.state != "cancel"
            and m.location_dest_usage != "inventory"
            and m.product_id == self.product_id,
        )

        if not moves:
            return self.env["stock.move"], self.env["stock.move"]

        if not strict:
            # The first move created was the one created from the intial rule that started it all.
            sorted_moves = moves.sorted("id")
            seen_wh_ids = set()
            triggering_rule_ids = []

            for move in sorted_moves:
                if move.warehouse_id.id not in seen_wh_ids:
                    triggering_rule_ids.append(move.rule_id.id)
                    seen_wh_ids.add(move.warehouse_id.id)

        if self.env.context.get("accrual_entry_date"):
            accrual_date = fields.Date.from_string(
                self.env.context["accrual_entry_date"],
            )
            moves = moves.filtered(
                lambda r: fields.Date.context_today(r, r.date) <= accrual_date,
            )

        for move in moves:

            if not move._is_dropshipped_returned() and (
                (strict and move.location_dest_id._is_outgoing())
                or (
                    not strict
                    and move.rule_id.id in triggering_rule_ids
                    and (move.location_final_id or move.location_dest_id)._is_outgoing()
                )
            ):
                if not move.origin_returned_move_id or (
                    move.origin_returned_move_id and move.to_refund
                ):
                    outgoing_moves |= move
            elif move.to_refund and (
                (strict and move._is_incoming() or move.location_id._is_outgoing())
                or (
                    not strict
                    and move.rule_id.id in triggering_rule_ids
                    and (move.location_final_id or move.location_dest_id).usage
                    == "internal"
                )
            ):
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _prepare_procurement_vals(self):
        """Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super()._prepare_procurement_vals()
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.date_commitment or self._get_date_planned()
        date_planned = date_deadline - timedelta(
            days=self.order_id.company_id.security_lead,
        )
        values.update(
            {
                "origin": self.order_id.name,
                "reference_ids": self.order_id.stock_reference_ids,
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
            # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == "stock_move":
                qty = 0.0
                outgoing_moves, incoming_moves = (
                    line._get_stock_moves_outgoing_incoming()
                )
                for move in outgoing_moves:
                    if move.state != "done":
                        continue
                    qty += move.product_uom._compute_quantity(
                        move.quantity,
                        line.product_uom_id,
                        rounding_method="HALF-UP",
                    )
                for move in incoming_moves:
                    if move.state != "done":
                        continue
                    qty -= move.product_uom._compute_quantity(
                        move.quantity,
                        line.product_uom_id,
                        rounding_method="HALF-UP",
                    )
                delivered_qties[line] = qty
        return delivered_qties

    def _prepare_reference_vals(self):
        return {
            "name": self.order_id.name,
            "sale_ids": [(4, self.order_id.id)],
        }

    def _read_qties(self, date, wh):
        return (
            self.mapped("product_id")
            .with_context(to_date=date, warehouse_id=wh)
            .read(
                [
                    "qty_available",
                    "free_qty",
                    "virtual_available",
                ],
            )
        )

    def _update_line_quantity(self, values):
        precision = self.env["decimal.precision"].precision_get("Product Unit")
        line_products = self.filtered(lambda l: l.product_id.type == "consu")
        if (
            line_products.mapped("qty_transferred")
            and float_compare(
                values["product_uom_qty"],
                max(line_products.mapped("qty_transferred")),
                precision_digits=precision,
            )
            == -1
        ):
            raise UserError(
                _(
                    "The ordered quantity of a sale order line cannot be decreased below the amount already delivered. Instead, create a return in your inventory.",
                ),
            )
        super()._update_line_quantity(values)

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def has_valued_move_ids(self):
        return (
            any(move.state not in ("cancel", "draft") for move in self.move_ids)
            or super().has_valued_move_ids()  # TODO: remove in master
        )
