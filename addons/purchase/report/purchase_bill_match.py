from odoo import api, fields, models
from odoo.tools import formatLang, SQL


class PurchaseBillUnion(models.Model):
    _name = "purchase.bill.match"
    _description = "Purchases & Bills Union"
    _auto = False
    _rec_names_search = ["name", "reference"]
    _order = "date desc, name desc"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        readonly=True,
    )
    vendor_bill_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        readonly=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        readonly=True,
    )
    date = fields.Date(
        string="Date",
        readonly=True,
    )
    amount = fields.Float(
        string="Amount",
        readonly=True,
    )
    name = fields.Char(
        string="Reference",
        readonly=True,
    )
    reference = fields.Char(
        string="Source",
        readonly=True,
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends_context("show_total_amount")
    @api.depends("currency_id", "reference", "amount", "purchase_order_id")
    def _compute_display_name(self):
        for doc in self:
            name = doc.name or ""
            if doc.reference:
                name += " - " + doc.reference
            amount = doc.amount
            if doc.purchase_order_id and doc.purchase_order_id.invoice_state == "no":
                amount = 0.0
            name += ": " + formatLang(self.env, amount, currency_obj=doc.currency_id)
            doc.display_name = name

    # ------------------------------------------------------------
    # QUERY METHODS
    # ------------------------------------------------------------

    @property
    def _table_query(self):
        """Generate SQL UNION query combining vendor bills and purchase orders.

        This creates a unified view of:
        - Posted vendor bills (invoices and refunds)
        - Purchase orders awaiting invoicing
        - Additional sources from _get_additional_queries() hook

        Returns:
            SQL: Combined query with vendor bills (positive IDs) and
                 purchase orders (negative IDs to avoid collision)
        """
        queries = [
            self._query_vendor_bills(),
            self._query_purchase_orders(),
        ]

        # Hook for other modules to add additional queries
        additional_queries = self._get_additional_queries()
        queries.extend(additional_queries)

        # Build UNION ALL query
        if len(queries) == 1:
            return queries[0]

        result = queries[0]
        for query in queries[1:]:
            result = SQL("%s UNION ALL %s", result, query)

        return result

    @api.model
    def _get_additional_queries(self):
        """Hook for other modules to add queries to the UNION.

        This method should be overridden by inheriting modules to add
        additional data sources to the purchase.bill.match view.

        Example:
            @api.model
            def _get_additional_queries(self):
                queries = super()._get_additional_queries()
                queries.append(self._query_templates())
                return queries

        Returns:
            list[SQL]: List of SQL queries to add to the UNION
        """
        return []

    @api.model
    def _query_vendor_bills(self):
        """Select posted vendor bills from account_move.

        Returns:
            SQL: Query for posted vendor bills (in_invoice, in_refund)
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
            self._select_vendor_bills(),
            self._from_vendor_bills(),
            self._where_vendor_bills(),
        )

    @api.model
    def _select_vendor_bills(self):
        """Define field selection for vendor bills.

        Returns:
            SQL: Field list for vendor bill selection
        """
        return SQL(
            """
            am.id,
            am.name,
            am.ref AS reference,
            am.partner_id,
            am.date AS date,
            am.amount_untaxed AS amount,
            am.currency_id,
            am.company_id,
            am.id AS vendor_bill_id,
            NULL::INTEGER AS purchase_order_id
            """,
        )

    @api.model
    def _from_vendor_bills(self):
        """Define FROM clause for vendor bills.

        Returns:
            SQL: FROM clause for vendor bill selection
        """
        return SQL("account_move am")

    @api.model
    def _where_vendor_bills(self):
        """Define WHERE clause for vendor bills.

        Returns:
            SQL: Conditions for selecting posted vendor bills
        """
        return SQL(
            """
            am.move_type IN ('in_invoice', 'in_refund')
            AND am.state = 'posted'
            """,
        )

    @api.model
    def _query_purchase_orders(self):
        """Select purchase orders awaiting invoicing.

        Returns:
            SQL: Query for confirmed purchase orders with invoice_status
                 'to invoice' or 'no'. Uses negative IDs to prevent
                 collision with vendor bill IDs.
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
            self._select_purchase_orders(),
            self._from_purchase_orders(),
            self._where_purchase_orders(),
        )

    @api.model
    def _select_purchase_orders(self):
        """Define field selection for purchase orders.

        Returns:
            SQL: Field list for purchase order selection
        """
        return SQL(
            """
            -po.id AS id,
            po.name,
            po.partner_ref AS reference,
            po.partner_id,
            po.date_order::DATE AS date,
            po.amount_untaxed AS amount,
            po.currency_id,
            po.company_id,
            NULL::INTEGER AS vendor_bill_id,
            po.id AS purchase_order_id
            """,
        )

    @api.model
    def _from_purchase_orders(self):
        """Define FROM clause for purchase orders.

        Returns:
            SQL: FROM clause for purchase order selection
        """
        return SQL("purchase_order po")

    @api.model
    def _where_purchase_orders(self):
        """Define WHERE clause for purchase orders.

        Returns:
            SQL: Conditions for selecting POs awaiting invoicing
        """
        return SQL(
            """
            po.state = 'done'
            AND po.invoice_state IN ('to do', 'no')
            """,
        )
