from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class PurchaseBillLineMatch(models.Model):
    """Line-level matching view for Purchase Order lines and Account Move lines.

    This model provides a unified view enabling granular matching between:
    - Purchase Order lines awaiting invoicing
    - Vendor Bill lines not yet linked to a purchase order

    It supports matching operations, bill creation from PO lines,
    and adding bill lines to existing purchase orders.
    """

    _name = "purchase.bill.line.match"
    _description = "Purchase Order Line & Vendor Bill Line Matching"
    _auto = False
    _order = "product_id, aml_id, pol_id"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
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
        related="product_id.uom_id",
        comodel_name="uom.uom",
    )

    pol_id = fields.Many2one(
        comodel_name="purchase.order.line",
        readonly=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        readonly=True,
    )
    aml_id = fields.Many2one(
        comodel_name="account.move.line",
        readonly=True,
    )
    account_move_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
    )

    state = fields.Char(
        readonly=True,
    )
    reference = fields.Char(
        compute="_compute_reference",
    )

    line_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        readonly=True,
    )
    line_qty = fields.Float(
        readonly=True,
    )
    qty_invoiced = fields.Float(
        readonly=True,
    )
    qty_to_invoice = fields.Float(
        string="Qty to invoice",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        compute="_compute_product_uom_qty",
        readonly=False,
        inverse="_inverse_product_uom_qty",
    )

    product_uom_price = fields.Float(
        compute="_compute_product_uom_price",
        readonly=False,
        inverse="_inverse_product_uom_price",
    )
    line_amount_taxexc = fields.Monetary(
        readonly=True,
    )
    billed_amount_taxexc = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount_untaxed_fields",
    )
    purchase_amount_taxexc = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount_untaxed_fields",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_amount_untaxed_fields(self):
        for line in self:
            line.billed_amount_taxexc = (
                line.line_amount_taxexc if line.account_move_id else False
            )
            line.purchase_amount_taxexc = (
                line.line_amount_taxexc if line.purchase_order_id else False
            )

    def _compute_reference(self):
        for line in self:
            line.reference = (
                line.purchase_order_id.display_name or line.account_move_id.display_name
            )

    def _compute_display_name(self):
        for line in self:
            line.display_name = (
                line.product_id.display_name or line.aml_id.name or line.pol_id.name
            )

    def _compute_product_uom_qty(self):
        for line in self:
            line.product_uom_qty = line.line_uom_id._compute_quantity(
                line.line_qty, line.product_uom_id
            )

    @api.depends("aml_id.price_unit", "pol_id.price_unit")
    def _compute_product_uom_price(self):
        for line in self:
            line.product_uom_price = (
                line.aml_id.price_unit if line.aml_id else line.pol_id.price_unit
            )

    # ------------------------------------------------------------
    # ONCHANGE METHODS
    # ------------------------------------------------------------

    @api.onchange("product_uom_price")
    def _inverse_product_uom_price(self):
        for line in self:
            if line.aml_id:
                line.aml_id.price_unit = line.product_uom_price
            else:
                line.pol_id.price_unit = line.product_uom_price

    @api.onchange("product_uom_qty")
    def _inverse_product_uom_qty(self):
        for line in self:
            if line.aml_id:
                line.aml_id.quantity = line.product_uom_qty
            else:
                # on POL, setting product_qty will recompute price_unit to have the old value
                # this prevents the price to revert by saving the previous price and re-setting them again
                previous_price_unit = line.pol_id.price_unit
                line.pol_id.product_qty = line.product_uom_qty
                line.pol_id.price_unit = previous_price_unit

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_open_line(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move" if self.account_move_id else "purchase.order",
            "view_mode": "form",
            "res_id": (
                self.account_move_id.id
                if self.account_move_id
                else self.purchase_order_id.id
            ),
        }

    @api.model
    def _action_create_bill_from_po_lines(self, partner, po_lines):
        """Create a new vendor bill with the selected PO lines and returns an action to open it"""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
            }
        )
        bill._add_purchase_order_lines(po_lines)
        return bill._get_records_action()

    def action_match_lines(self):
        if not self.pol_id:  # we need POL(s) to either match or create bill
            raise UserError(
                _(
                    "You must select at least one Purchase Order line to match or create bill."
                )
            )
        if (
            not self.aml_id
        ):  # select POL(s) without AML -> create a draft bill with the POL(s)
            return self._action_create_bill_from_po_lines(self.partner_id, self.pol_id)

        pol_by_product = self.pol_id.grouped("product_id")
        aml_by_product = self.aml_id.grouped("product_id")
        residual_purchase_order_lines = self.pol_id
        residual_account_move_lines = self.aml_id

        # Match all matchable POL-AML lines and remove them from the residual group
        for product, po_line in pol_by_product.items():
            po_line = po_line[
                0
            ]  # in case of multiple POL with same product, only match the first one
            matching_bill_lines = aml_by_product.get(product)
            if matching_bill_lines:
                matching_bill_lines.purchase_line_ids = [Command.link(po_line.id)]
                residual_purchase_order_lines -= po_line
                residual_account_move_lines -= matching_bill_lines

        if len(residual_bill := self.aml_id.move_id) == 1:
            # Delete all unmatched selected AML
            if residual_account_move_lines:
                residual_account_move_lines.unlink()

            # Add all remaining POL to the residual bill
            residual_bill._add_purchase_order_lines(residual_purchase_order_lines)

    def action_add_to_po(self):
        if not self or not self.aml_id:
            raise UserError(_("Select Vendor Bill lines to add to a Purchase Order"))
        partner = self.mapped("partner_id.commercial_partner_id")
        if len(partner) > 1:
            raise UserError(_("Please select bill lines with the same vendor."))
        context = {
            "default_partner_id": partner.id,
            "dialog_size": "medium",
            "has_products": bool(self.aml_id.product_id),
        }
        if len(self.purchase_order_id) > 1:
            raise UserError(
                _("Vendor Bill lines can only be added to one Purchase Order.")
            )
        elif self.purchase_order_id:
            context["default_purchase_order_id"] = self.purchase_order_id.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Add to Purchase Order"),
            "res_model": "bill.to.po.wizard",
            "target": "new",
            "views": [(self.env.ref("purchase.bill_to_po_wizard_form").id, "form")],
            "context": context,
        }

    # ------------------------------------------------------------
    # QUERY METHODS
    # ------------------------------------------------------------

    @property
    def _table_query(self):
        """Generate SQL UNION query combining PO lines and vendor bill lines.

        This creates a unified view of:
        - Purchase order lines awaiting invoicing
        - Vendor bill lines not yet linked to a purchase order

        Returns:
            SQL: Combined query with PO lines (positive IDs) and
                 bill lines (negative IDs to avoid collision)
        """
        return SQL(
            "%s UNION ALL %s",
            self._query_po_line(),
            self._query_am_line(),
        )

    @api.model
    def _query_po_line(self):
        """Select purchase order lines awaiting invoicing.

        Includes:
        - Lines with quantities not yet invoiced
        - Lines with non-zero qty_to_invoice
        - Downpayment lines that have been invoiced

        Returns:
            SQL: Query for purchase order lines from confirmed POs
        """
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_po_line(),
            self._from_po_line(),
            self._where_po_line(),
        )

    @api.model
    def _select_po_line(self):
        """Define field selection for purchase order lines.

        Returns:
            SQL: Field list for PO line selection
        """
        return SQL(
            """
            pol.id,
            pol.id AS pol_id,
            NULL::INTEGER AS aml_id,
            pol.company_id,
            pol.partner_id,
            pol.product_id,
            pol.product_qty AS line_qty,
            pol.product_uom_id AS line_uom_id,
            pol.qty_invoiced,
            pol.qty_to_invoice,
            po.id AS purchase_order_id,
            NULL::INTEGER AS account_move_id,
            pol.price_subtotal AS line_amount_taxexc,
            po.currency_id,
            po.state
            """,
        )

    @api.model
    def _from_po_line(self):
        """Define FROM clause for purchase order lines.

        Returns:
            SQL: FROM clause with PO line and PO join
        """
        return SQL(
            """
            purchase_order_line pol
            LEFT JOIN purchase_order po ON pol.order_id = po.id
            """,
        )

    @api.model
    def _where_po_line(self):
        """Build WHERE clause for purchase order line selection.

        Returns:
            SQL: Conditions for selecting uninvoiced, over-invoiced, or downpayment PO lines
        """
        return SQL(
            """
            (
                po.state = 'done'
                AND (
                    -- Lines needing invoicing: no linked draft/posted invoices
                    (
                        (pol.product_qty > pol.qty_invoiced OR pol.qty_to_invoice > 0)
                        AND NOT EXISTS (
                            SELECT 1 FROM account_move_line_purchase_order_line_rel rel
                            JOIN account_move_line aml ON rel.move_line_id = aml.id
                            WHERE rel.order_line_id = pol.id
                            AND aml.parent_state IN ('draft', 'posted')
                        )
                    )
                    -- OR over-invoiced lines needing credit notes
                    OR pol.qty_to_invoice < 0
                )
            )
            OR (COALESCE(pol.display_type, '') = '' AND pol.is_downpayment AND pol.qty_invoiced > 0)
            """,
        )

    @api.model
    def _query_am_line(self):
        """Select vendor bill lines not linked to purchase orders.

        Includes only:
        - Product lines (display_type = 'product')
        - Lines from vendor invoices/refunds
        - Lines in draft or posted state
        - Lines not yet linked to a purchase order line

        Returns:
            SQL: Query for unlinked account move lines. Uses negative IDs
                 to prevent collision with PO line IDs.
        """
        return SQL(
            """
            SELECT
                %s
            FROM
                %s
            WHERE
                %s
            """,
            self._select_am_line(),
            self._from_am_line(),
            self._where_am_line(),
        )

    @api.model
    def _select_am_line(self):
        """Define field selection for account move lines.

        Returns:
            SQL: Field list for account move line selection
        """
        return SQL(
            """
            -aml.id AS id,
            NULL::INTEGER AS pol_id,
            aml.id AS aml_id,
            aml.company_id,
            am.partner_id,
            aml.product_id,
            aml.quantity AS line_qty,
            aml.product_uom_id AS line_uom_id,
            NULL::NUMERIC AS qty_invoiced,
            NULL::NUMERIC AS qty_to_invoice,
            NULL::INTEGER AS purchase_order_id,
            am.id AS account_move_id,
            aml.amount_currency AS line_amount_taxexc,
            aml.currency_id,
            aml.parent_state AS state
            """,
        )

    @api.model
    def _from_am_line(self):
        """Define FROM clause for account move lines.

        Returns:
            SQL: FROM clause with account move line and move join
        """
        return SQL(
            """
            account_move_line aml
            LEFT JOIN account_move am ON aml.move_id = am.id
            """,
        )

    @api.model
    def _where_am_line(self):
        """Build WHERE clause for account move line selection.

        Returns:
            SQL: Conditions for selecting unlinked vendor bill lines
        """
        return SQL(
            """
            aml.display_type = 'product'
            AND am.move_type IN ('in_invoice', 'in_refund')
            AND aml.parent_state IN ('draft', 'posted')
            AND NOT EXISTS (
                SELECT 1 FROM account_move_line_purchase_order_line_rel rel
                WHERE rel.move_line_id = aml.id
            )
            """,
        )
