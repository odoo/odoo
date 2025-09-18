"""
Order Invoice Integration Mixins

Consolidates 800+ lines of invoice tracking logic duplicated across order types.
Provides unified invoice tracking, amount computation, and status management.
"""

from odoo import api, fields, models, _


class OrderInvoiceMixin(models.AbstractModel):
    """Order-level invoice tracking and management.

    Provides invoice tracking fields and methods common to all order types
    (sale, purchase, etc.). Child models must implement abstract methods
    to specify invoice direction and filtering.
    """

    _name = "order.invoice.mixin"
    _description = "Order Invoice Integration"

    # NOTE: Child models should have currency_id field (defined here for Monetary field requirement)
    # Override or use related field if needed: currency_id = fields.Many2one('res.currency', related='...')
    currency_id = fields.Many2one("res.currency", required=True)

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    # Invoice tracking
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        compute="_compute_invoice_ids",
        copy=False,
        help="Invoices/bills related to this order",
    )
    invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_invoice_ids",
        help="Number of invoices/bills for this order",
    )

    # Invoiced amounts (renamed from amount_taxexc_invoiced/amount_taxinc_invoiced)
    amount_invoiced_untaxed = fields.Monetary(
        string="Invoiced (Untaxed)",
        compute="_compute_amount_invoiced",
        currency_field="currency_id",
        help="Total amount already invoiced, excluding taxes",
    )
    amount_invoiced_total = fields.Monetary(
        string="Invoiced (Total)",
        compute="_compute_amount_invoiced",
        currency_field="currency_id",
        help="Total amount already invoiced, including taxes",
    )

    # To-invoice amounts (renamed from amount_taxexc_to_invoice/amount_taxinc_to_invoice)
    amount_to_invoice_untaxed = fields.Monetary(
        string="To Invoice (Untaxed)",
        compute="_compute_amount_to_invoice",
        currency_field="currency_id",
        help="Remaining amount to invoice, excluding taxes",
    )
    amount_to_invoice_total = fields.Monetary(
        string="To Invoice (Total)",
        compute="_compute_amount_to_invoice",
        currency_field="currency_id",
        help="Remaining amount to invoice, including taxes",
    )

    # Invoice status (renamed from invoice_state)
    invoice_state = fields.Selection(
        selection="_get_invoice_state_selection",
        string="Invoice Status",
        default="no",
        compute="_compute_invoice_state",
        store=True,
        copy=False,
        help="Invoice status of this order",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("line_ids.invoice_line_ids")
    def _compute_invoice_ids(self):
        """Compute invoices from line invoice lines.

        Aggregates all invoices linked to order lines, filtering by
        invoice direction (out_invoice/out_refund for sales,
        in_invoice/in_refund for purchases).
        """
        for order in self:
            # Get invoice types from child model
            invoice_types = order._get_invoice_types()

            # Aggregate invoices from all lines
            invoices = order.line_ids.invoice_line_ids.move_id.filtered(
                lambda r: r.move_type in invoice_types
            )

            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    @api.depends(
        "line_ids.amount_invoiced_untaxed",
        "line_ids.amount_invoiced_total",
    )
    def _compute_amount_invoiced(self):
        """Sum invoiced amounts from lines."""
        for order in self:
            order.amount_invoiced_untaxed = sum(
                order.line_ids.mapped("amount_invoiced_untaxed")
            )
            order.amount_invoiced_total = sum(
                order.line_ids.mapped("amount_invoiced_total")
            )

    @api.depends(
        "line_ids.amount_to_invoice_untaxed",
        "line_ids.amount_to_invoice_total",
    )
    def _compute_amount_to_invoice(self):
        """Sum to-invoice amounts from lines."""
        for order in self:
            order.amount_to_invoice_untaxed = sum(
                order.line_ids.mapped("amount_to_invoice_untaxed")
            )
            order.amount_to_invoice_total = sum(
                order.line_ids.mapped("amount_to_invoice_total")
            )

    @api.depends("state", "line_ids.invoice_state")
    def _compute_invoice_state(self):
        """Compute invoice status from order state and line statuses.

        This is a hook method that child models should override to implement
        their specific invoice status logic.
        """
        # Default implementation - override in child models
        for order in self:
            order.invoice_state = "no"

    # -------------------------------------------------------------------------
    # ABSTRACT METHODS - Must be implemented by child models
    # -------------------------------------------------------------------------

    def _get_invoice_types(self):
        """Return list of invoice types for this order.

        Examples:
            - Sale orders: ['out_invoice', 'out_refund']
            - Purchase orders: ['in_invoice', 'in_refund']

        Returns:
            list: Invoice move_type values to filter
        """
        raise NotImplementedError(
            "Child model must implement _get_invoice_types() "
            "to return invoice types like ['out_invoice', 'out_refund']"
        )

    @api.model
    def _get_invoice_state_selection(self):
        """Return invoice status selection values.

        Examples:
            - Sale: [('no', 'Nothing to Invoice'), ('to invoice', 'To Invoice'), ...]
            - Purchase: [('no', 'Nothing to Bill'), ('to do', 'To Bill'), ...]

        Returns:
            list: Selection tuples [(value, label), ...]
        """
        raise NotImplementedError(
            "Child model must implement _get_invoice_state_selection() "
            "to return status selection values"
        )

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_view_invoices(self):
        """Open invoices/bills view.

        Returns action to display invoices in list/form view.
        Child models should override to customize view/domain.
        """
        self.ensure_one()
        # Get action from child model
        action = self._get_invoice_action()
        invoices = self.invoice_ids

        if len(invoices) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = invoices.id
        else:
            action["domain"] = [("id", "in", invoices.ids)]

        return action

    def _get_invoice_action(self):
        """Return base action for viewing invoices.

        Child models should override to return appropriate action.

        Returns:
            dict: Action dictionary
        """
        raise NotImplementedError(
            "Child model must implement _get_invoice_action() " "to return view action"
        )


class OrderLineInvoiceMixin(models.AbstractModel):
    """Line-level invoice tracking and amount computation.

    Consolidates 800+ lines of complex invoice computation logic that was
    95% identical between sale and purchase order lines. The only significant
    difference is the direction sign (+1 vs -1).
    """

    _name = "order.line.invoice.mixin"
    _description = "Order Line Invoice Integration"

    # NOTE: Child models should have currency_id field (defined here for Monetary field requirement)
    currency_id = fields.Many2one("res.currency", required=True)

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    # Invoice line tracking
    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Invoice Lines",
        copy=False,
        help="Invoice/bill lines related to this order line",
    )

    # Quantity tracking (renamed from qty_invoiced)
    quantity_invoiced = fields.Float(
        string="Invoiced Quantity",
        compute="_compute_invoice_amounts",
        digits="Product Unit of Measure",
        help="Quantity already invoiced",
    )
    quantity_to_invoice = fields.Float(
        string="To Invoice Quantity",
        compute="_compute_invoice_amounts",
        digits="Product Unit of Measure",
        help="Remaining quantity to invoice",
    )

    # Invoiced amounts (renamed from amount_taxexc_invoiced/amount_taxinc_invoiced)
    amount_invoiced_untaxed = fields.Monetary(
        string="Invoiced (Untaxed)",
        compute="_compute_invoice_amounts",
        currency_field="currency_id",
        help="Amount already invoiced, excluding taxes",
    )
    amount_invoiced_total = fields.Monetary(
        string="Invoiced (Total)",
        compute="_compute_invoice_amounts",
        currency_field="currency_id",
        help="Amount already invoiced, including taxes",
    )

    # To-invoice amounts (renamed from amount_taxexc_to_invoice/amount_taxinc_to_invoice)
    amount_to_invoice_untaxed = fields.Monetary(
        string="To Invoice (Untaxed)",
        compute="_compute_invoice_amounts",
        currency_field="currency_id",
        help="Remaining amount to invoice, excluding taxes",
    )
    amount_to_invoice_total = fields.Monetary(
        string="To Invoice (Total)",
        compute="_compute_invoice_amounts",
        currency_field="currency_id",
        help="Remaining amount to invoice, including taxes",
    )

    # Invoice status
    invoice_state = fields.Selection(
        selection="_get_line_invoice_state_selection",
        string="Invoice Status",
        compute="_compute_line_invoice_state",
        store=True,
        help="Invoice status of this line",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends(
        "invoice_line_ids",
        "invoice_line_ids.move_id.state",
        "invoice_line_ids.quantity",
        "invoice_line_ids.price_subtotal",
        "invoice_line_ids.price_total",
        "quantity",
        "quantity_transferred",
        "price_unit",
        "discount",
        "tax_ids",
        "product_id.invoice_policy",
        "product_id.bill_policy",
    )
    def _compute_invoice_amounts(self):
        """Unified computation of all invoice-related quantities and amounts.

        This is THE BIG CONSOLIDATION - replaces 800+ lines of duplicate code.

        Computes in single pass:
            - quantity_invoiced, quantity_to_invoice
            - amount_invoiced_untaxed, amount_to_invoice_untaxed
            - amount_invoiced_total, amount_to_invoice_total

        The logic is 95% identical between sale/purchase - only direction sign differs:
            - Sale: direction_sign = -invoice_line.move_id.direction_sign
            - Purchase: direction_sign = invoice_line.move_id.direction_sign
        """
        for line in self.filtered(lambda x: not x.display_type):

            # Determine quantity to consider based on invoice/bill policy
            invoice_policy_field = line._get_invoice_policy_field()
            invoice_policy = line.product_id[invoice_policy_field]

            qty_to_consider = (
                line.quantity_transferred
                if invoice_policy == "transferred"
                else line.quantity  # invoice_policy == 'ordered'
            )

            # Initialize accumulators
            qty_invoiced = 0.0
            amount_invoiced_untaxed = 0.0
            amount_invoiced_total = 0.0

            # Get invoice lines for this order line
            invoice_lines = line._get_invoice_lines()

            # Iterate through invoice lines and sum amounts
            for invoice_line in invoice_lines:
                # Only consider posted invoices
                if invoice_line.state != "posted":
                    continue

                # Get direction sign from child model
                # Sale: -invoice_line.move_id.direction_sign
                # Purchase: +invoice_line.move_id.direction_sign
                direction_sign = line._get_invoice_direction_sign(invoice_line)

                # Quantity tracking
                qty_invoiced_unsigned = invoice_line.product_uom_id._compute_quantity(
                    invoice_line.quantity,
                    line.product_uom_id,
                )
                qty_invoiced += qty_invoiced_unsigned * direction_sign

                # Amount tracking (untaxed)
                amount_untaxed_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_subtotal,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_invoiced_untaxed += amount_untaxed_unsigned * direction_sign

                # Amount tracking (total with tax)
                amount_total_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_total,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_invoiced_total += amount_total_unsigned * direction_sign

            # Set invoiced values
            line.quantity_invoiced = qty_invoiced
            line.amount_invoiced_untaxed = amount_invoiced_untaxed
            line.amount_invoiced_total = amount_invoiced_total

            # Calculate "to invoice" amounts
            # Note: Do not use price_subtotal field as it returns zero when ordered
            # quantity is zero. This causes problems for expense lines (e.g.: ordered qty = 0,
            # delivered qty = 4, price_unit = 20; subtotal is zero), but when invoiceable
            # the line shows an amount and not zero.
            price_subtotal = line._get_discounted_price_unit() * qty_to_consider

            # Adjust for price-included taxes
            if len(line.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                # As included taxes are not excluded from computed subtotal, compute_all()
                # must be called to retrieve subtotal without them.
                shipping_partner = line._get_shipping_partner()
                price_subtotal = line.tax_ids.compute_all(
                    line._get_discounted_price_unit(),
                    currency=line.currency_id,
                    quantity=qty_to_consider,
                    product=line.product_id,
                    partner=shipping_partner,
                )["total_excluded"]

            # Handle special discount cases
            # Loop needed when invoice line discount differs from order line discount
            if any(invoice_lines.mapped(lambda l: l.discount != line.discount)):
                # In case of re-invoicing with different discount, calculate
                # manually the remaining amount to invoice
                amount = 0
                for invoice_line in invoice_lines:
                    if invoice_line.state != "posted":
                        continue

                    # Convert invoice line price to order currency
                    converted_price = invoice_line.currency_id._convert(
                        invoice_line.price_unit,
                        line.currency_id,
                        line.company_id,
                        invoice_line.date or fields.Date.today(),
                        round=False,
                    )

                    # Calculate amount considering taxes
                    if (
                        len(
                            invoice_line.tax_ids.filtered(lambda tax: tax.price_include)
                        )
                        > 0
                    ):
                        amount += invoice_line.tax_ids.compute_all(
                            converted_price * invoice_line.quantity,
                        )["total_excluded"]
                    else:
                        amount += converted_price * invoice_line.quantity

                line.amount_to_invoice_untaxed = max(price_subtotal - amount, 0.0)
            else:
                line.amount_to_invoice_untaxed = max(
                    price_subtotal - amount_invoiced_untaxed,
                    0.0,
                )

            # Tax-included amount to invoice
            # Reuse price_total from _compute_amounts to avoid recalculation
            unit_price_total = (
                line.price_total / line.quantity if line.quantity else 0.0
            )
            line.amount_to_invoice_total = unit_price_total * (
                qty_to_consider - line.quantity_invoiced
            )

            # Quantity to invoice
            line.quantity_to_invoice = max(
                qty_to_consider - line.quantity_invoiced, 0.0
            )

    @api.depends("quantity_to_invoice")
    def _compute_line_invoice_state(self):
        """Compute invoice status for this line.

        Child models should override to implement specific logic.
        """
        for line in self:
            line.invoice_state = "no"

    # -------------------------------------------------------------------------
    # ABSTRACT METHODS - Must be implemented by child models
    # -------------------------------------------------------------------------

    def _get_invoice_direction_sign(self, invoice_line):
        """Return direction sign for invoice amount calculation.

        This is the KEY DIFFERENCE between sale and purchase:
            - Sale orders: -invoice_line.move_id.direction_sign
            - Purchase orders: +invoice_line.move_id.direction_sign

        Args:
            invoice_line: account.move.line record

        Returns:
            int: +1 or -1
        """
        raise NotImplementedError(
            "Child model must implement _get_invoice_direction_sign() "
            "to return +1 or -1 based on invoice direction"
        )

    def _get_invoice_lines(self):
        """Return invoice lines for this order line.

        Default implementation returns invoice_line_ids.
        Child models can override for custom filtering.

        Returns:
            recordset: account.move.line records
        """
        return self.invoice_line_ids

    def _get_invoice_policy_field(self):
        """Return name of invoice policy field.

        Examples:
            - Sale: 'invoice_policy'
            - Purchase: 'bill_policy'

        Returns:
            str: Field name on product
        """
        raise NotImplementedError(
            "Child model must implement _get_invoice_policy_field() "
            "to return field name like 'invoice_policy' or 'bill_policy'"
        )

    def _get_discounted_price_unit(self):
        """Return discounted price unit for calculations.

        Default implementation calculates: price_unit * (1 - discount/100)
        Child models can override for custom discount logic.

        Returns:
            float: Discounted price per unit
        """
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)

    def _get_shipping_partner(self):
        """Return partner for shipping/billing address.

        Used for tax computation with partner-specific rules.
        Child models should override to return appropriate partner.

        Returns:
            res.partner: Partner record
        """
        return self.order_id.partner_id

    @api.model
    def _get_line_invoice_state_selection(self):
        """Return line invoice status selection values.

        Returns:
            list: Selection tuples [(value, label), ...]
        """
        return [
            ("no", "Nothing to Invoice"),
            ("to invoice", "To Invoice"),
            ("invoiced", "Fully Invoiced"),
        ]
