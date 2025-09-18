"""
Order Invoice Integration Mixins

Two abstract mixins that consolidate invoice tracking logic shared between
sale.order/purchase.order and their respective line models.

Classes:
    OrderInvoiceMixin — order-level invoice tracking, state, and actions
    OrderLineInvoiceMixin — line-level invoice fields and shared helpers
"""

from odoo import api, fields, models


INVOICE_STATE = [
    ("no", "Nothing to invoice"),
    ("to do", "To invoice"),
    ("partial", "Partially invoiced"),
    ("done", "Fully invoiced"),
    ("over done", "Over-invoiced"),
]


# ════════════════════════════════════════════════════════════════════
# ORDER-LEVEL INVOICE MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderInvoiceMixin(models.AbstractModel):
    """Order-level invoice tracking and state computation.

    Uses ``_get_order_type()`` to derive invoice direction (out/in), move
    types, action XML-IDs, and partner payment term fields — eliminating
    the need for per-model overrides of boilerplate routing.

    Requires ``order.mixin`` for ``_get_order_type()``, ``partner_id``,
    ``payment_term_id``, ``state``.  Requires ``line_ids`` from the
    concrete model.
    """

    _name = "order.invoice.mixin"
    _description = "Order Invoice Integration"

    # ─── Invoice Tracking Fields ───────────────────────────────────

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        compute="_compute_invoice_ids",
        search="_search_invoice_ids",
    )
    invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_invoice_ids",
    )
    invoice_state = fields.Selection(
        selection=INVOICE_STATE,
        string="Invoice Status",
        default="no",
        compute="_compute_invoice_state",
        store=True,
        copy=False,
    )

    # ─── Invoice Type Routing ──────────────────────────────────────

    def _get_invoice_move_types(self):
        """Return invoice move_type values for this order type.

        Derived from ``_get_order_type()``:
        sale → ``('out_invoice', 'out_refund')``,
        purchase → ``('in_invoice', 'in_refund')``.
        """
        direction = "out" if self._get_order_type() == "sale" else "in"
        return (f"{direction}_invoice", f"{direction}_refund")

    # ─── Compute Invoice IDs ──────────────────────────────────────

    @api.depends(
        "line_ids.invoice_line_ids",
        "line_ids.invoice_line_ids.move_id.reversal_move_ids",
    )
    def _compute_invoice_ids(self):
        """Batched 3-step pattern: collect, search orphan refunds, assign.

        Identical in sale.order and purchase.order — only the move_type
        filter differs (routed via ``_get_invoice_move_types()``).

        Orphan refunds are credit notes created via the "Credit Note" button
        on an invoice — they are not directly linked to order lines.
        """
        move_types = self._get_invoice_move_types()
        refund_type = move_types[1]

        # Step 1: Collect directly linked invoices for all orders
        order_invoices = {}
        all_invoice_ids = set()
        for order in self:
            invoices = order.line_ids.invoice_line_ids.move_id.filtered(
                lambda r: r.move_type in move_types,
            )
            order_invoices[order.id] = set(invoices.ids)
            all_invoice_ids.update(invoices.ids)

        # Step 2: Single batched search for orphan refunds across all orders
        orphan_refunds_by_reversed_id = {}
        if all_invoice_ids:
            orphan_refunds = self.env["account.move"].search(
                [
                    ("reversed_entry_id", "in", list(all_invoice_ids)),
                    ("move_type", "=", refund_type),
                    ("id", "not in", list(all_invoice_ids)),
                ]
            )
            for refund in orphan_refunds:
                orphan_refunds_by_reversed_id.setdefault(
                    refund.reversed_entry_id.id,
                    [],
                ).append(refund.id)

        # Step 3: Assign invoices + orphan refunds to each order
        AccountMove = self.env["account.move"]
        for order in self:
            invoice_ids = order_invoices.get(order.id, set())
            for inv_id in list(invoice_ids):
                if inv_id in orphan_refunds_by_reversed_id:
                    invoice_ids.update(orphan_refunds_by_reversed_id[inv_id])
            order.invoice_ids = AccountMove.browse(invoice_ids)
            order.invoice_count = len(invoice_ids)

    def _search_invoice_ids(self, operator, value):
        """Generic ORM-based search for ``invoice_ids``.

        Concrete models should override with SQL-optimized version for
        the ``in`` operator (involves model-specific relation table names).
        """
        move_types = self._get_invoice_move_types()
        return [
            (
                "line_ids.invoice_line_ids",
                "any",
                [
                    ("move_id.move_type", "in", move_types),
                    ("move_id", operator, value),
                ],
            ),
        ]

    # ─── Compute Invoice State ─────────────────────────────────────

    @api.depends("state", "line_ids.invoice_state", "invoice_ids")
    def _compute_invoice_state(self):
        """Batched computation using ``_read_group`` over line invoice states.

        Priority: ``over done`` > ``to do`` > ``partial`` > ``done`` > ``no``.
        Sale overrides to add ``_can_be_invoiced_alone()`` auxiliary line check.
        """
        confirmed_orders = self.filtered(lambda o: o.state == "done")
        (self - confirmed_orders).invoice_state = "no"
        if not confirmed_orders:
            return

        # Batched: single _read_group query for all confirmed orders
        line_model = f"{self._name}.line"
        lines_domain = [
            ("is_downpayment", "=", False),
            ("display_type", "=", False),
        ]
        line_invoice_state_all = {}
        for order, invoice_state in self.env[line_model]._read_group(
            lines_domain + [("order_id", "in", confirmed_orders.ids)],
            ["order_id", "invoice_state"],
        ):
            line_invoice_state_all.setdefault(order.id, set()).add(invoice_state)

        for order in confirmed_orders:
            states = line_invoice_state_all.get(order._origin.id, set())
            if not states:
                order.invoice_state = "no"
                continue
            # Single state → direct assignment (common case optimization)
            if len(states) == 1:
                order.invoice_state = next(iter(states))
                continue
            # Multiple states → resolve by priority
            if "over done" in states:
                order.invoice_state = "over done"
            elif "to do" in states:
                order.invoice_state = "to do"
            elif "partial" in states or states == {"done", "no"}:
                order.invoice_state = "partial"
            else:
                order.invoice_state = "no"

    # ─── Invoice Action ────────────────────────────────────────────

    def action_view_invoice(self, invoices=False):
        """Open invoice/bill list or form view.

        Uses ``_get_order_type()`` to derive the action XML-ID and
        default move type.  Hook: ``_get_invoice_action_context()``
        for model-specific context values.
        """
        if not invoices:
            invoices = self.mapped("invoice_ids")

        direction = "out" if self._get_order_type() == "sale" else "in"
        action = self.env["ir.actions.actions"]._for_xml_id(
            f"account.action_move_{direction}_invoice_type",
        )

        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = invoices.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {"default_move_type": f"{direction}_invoice"}
        if len(self) == 1:
            context.update(self._get_invoice_action_context())
        action["context"] = context
        return action

    def _get_invoice_action_context(self):
        """Hook for model-specific invoice action context.

        Base provides partner and payment term (routed by order type).
        Sale overrides to add ``partner_shipping_id``.
        Purchase overrides to add ``invoice_origin``.
        """
        self.ensure_one()
        pt_field = (
            "property_payment_term_id"
            if self._get_order_type() == "sale"
            else "property_supplier_payment_term_id"
        )
        return {
            "default_partner_id": self.partner_id.id,
            "default_invoice_payment_term_id": (
                self.payment_term_id.id
                or self.partner_id[pt_field].id
                or self.env["account.move"]
                .default_get(["invoice_payment_term_id"])
                .get("invoice_payment_term_id")
            ),
        }


# ════════════════════════════════════════════════════════════════════
# LINE-LEVEL INVOICE MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderLineInvoiceMixin(models.AbstractModel):
    """Line-level invoice tracking fields and shared helpers.

    Provides:
    - Invoice line tracking (``invoice_line_ids``)
    - Quantity and amount fields (``qty_invoiced``, ``amount_taxexc_invoiced``, etc.)
    - Shared helpers (``_get_invoice_lines()``, ``_get_posted_invoice_lines()``)

    The compute methods ``_compute_invoice_amounts()`` and
    ``_compute_invoice_state()`` are **stubs** — implementations differ
    too much between sale and purchase to unify cleanly (combo products,
    direction sign, policy fields, over-invoicing semantics).

    Requires ``order_id``, ``company_id``, ``currency_id``, ``product_uom_id``
    from the concrete model.
    """

    _name = "order.line.invoice.mixin"
    _description = "Order Line Invoice Integration"

    # ─── Currency (required for Monetary fields) ───────────────────

    currency_id = fields.Many2one("res.currency")

    # ─── Invoice Line Tracking ─────────────────────────────────────

    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Invoice Lines",
        copy=False,
    )

    # ─── Quantity Fields ───────────────────────────────────────────

    qty_invoiced = fields.Float(
        string="Invoiced Quantity",
        digits="Product Unit",
        compute="_compute_invoice_amounts",
        store=True,
    )
    qty_to_invoice = fields.Float(
        string="Quantity To Invoice",
        digits="Product Unit",
        compute="_compute_invoice_amounts",
        store=True,
    )

    # ─── Invoice Amount Fields ─────────────────────────────────────

    amount_taxexc_invoiced = fields.Monetary(
        string="Untaxed Invoiced Amount",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Invoiced Amount",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Untaxed Amount To Invoice",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxinc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance",
        compute="_compute_invoice_amounts",
        store=True,
    )

    # ─── Invoice State ─────────────────────────────────────────────

    invoice_state = fields.Selection(
        selection=INVOICE_STATE,
        string="Invoice Status",
        default="no",
        compute="_compute_invoice_state",
        store=True,
    )

    # ─── Shared Helpers ────────────────────────────────────────────

    def _get_invoice_lines(self):
        """Return invoice lines, filtered by accrual date if in context.

        Identical in sale.order.line and purchase.order.line.
        """
        self.ensure_one()
        if self.env.context.get("accrual_entry_date"):
            accrual_date = fields.Date.from_string(
                self.env.context["accrual_entry_date"],
            )
            return self.invoice_line_ids.filtered(
                lambda l: l.move_id.invoice_date
                and l.move_id.invoice_date <= accrual_date,
            )
        return self.invoice_line_ids

    def _get_posted_invoice_lines(self):
        """Return posted invoice lines for this order line.

        Filters to posted invoices and ``invoicing_legacy`` payment state.
        Shared between sale and purchase.
        """
        self.ensure_one()
        return self._get_invoice_lines().filtered(
            lambda l: l.parent_state == "posted"
            or l.move_id.payment_state == "invoicing_legacy"
        )

    def _get_invoice_policy_field(self):
        """Return the product field name for invoice/bill policy.

        Derived from the parent order's ``_get_order_type()``:
        sale → ``'invoice_policy'``, purchase → ``'bill_policy'``.
        """
        order_type = self.order_id._get_order_type()
        return "invoice_policy" if order_type == "sale" else "bill_policy"

    # ─── Compute Stubs (concrete models must override) ─────────────

    def _compute_invoice_amounts(self):
        """Compute invoice quantities and amounts for each line.

        Implementations differ too much to unify:

        - **Sale**: monolithic with combo product post-processing,
          ``direction_sign = -move.direction_sign``
        - **Purchase**: decomposed into helpers
          (``_sum_invoiced_amounts``, ``_compute_to_invoice_amounts``),
          ``direction_sign = +move.direction_sign``

        Concrete models must override entirely with their own
        ``@api.depends`` decorator.
        """
        raise NotImplementedError(
            f"{self._name} must implement _compute_invoice_amounts()"
        )

    def _compute_invoice_state(self):
        """Compute per-line invoice state.

        Implementations differ in:

        - Policy field: ``invoice_policy`` (sale) vs ``bill_policy`` (purchase)
        - Over-invoicing: sale marks delivery-based as ``'to do'``,
          purchase always uses ``'over done'``
        - Sale has combo line post-processing

        Concrete models must override entirely with their own
        ``@api.depends`` decorator.
        """
        raise NotImplementedError(
            f"{self._name} must implement _compute_invoice_state()"
        )
