from odoo import api, fields, models
from odoo.tools import Query, SQL

from odoo.addons.sale import const


class SaleReport(models.Model):
    _name = "sale.report"
    _inherit = "sql.report.mixin"
    _description = "Sales Analysis Report"
    _auto = False
    _rec_name = "date_order"
    _order = "date_order desc"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    nbr_lines = fields.Integer(
        string="# of Lines",
        readonly=True,
    )
    order_reference = fields.Reference(
        string="Order",
        selection=[("sale.order", "Sales Order")],
        aggregator="count_distinct",
    )
    # sale.order fields
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
    )
    # res.partner fields
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer Entity",
        readonly=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Customer Country",
        readonly=True,
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Customer State",
        readonly=True,
    )
    partner_zip = fields.Char(
        string="Customer ZIP",
        readonly=True,
    )
    industry_id = fields.Many2one(
        comodel_name="res.partner.industry",
        string="Customer Industry",
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        readonly=True,
    )
    team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        readonly=True,
    )
    # utm fields
    campaign_id = fields.Many2one(
        comodel_name="utm.campaign",
        string="Campaign",
        readonly=True,
    )
    medium_id = fields.Many2one(
        comodel_name="utm.medium",
        string="Medium",
        readonly=True,
    )
    source_id = fields.Many2one(
        comodel_name="utm.source",
        string="Source",
        readonly=True,
    )
    date_order = fields.Datetime(
        string="Order Date",
        readonly=True,
    )
    name = fields.Char(
        string="Order Reference",
        readonly=True,
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Status",
        readonly=True,
    )
    invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Order Invoice Status",
        readonly=True,
    )
    # sale.order.line fields
    line_invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Invoice Status",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Variant",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        readonly=True,
    )
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        readonly=True,
    )
    product_uom_qty = fields.Float(string="Qty Ordered", readonly=True)
    qty_transferred = fields.Float(string="Qty Delivered", readonly=True)
    qty_to_transfer = fields.Float(string="Qty To Deliver", readonly=True)
    qty_invoiced = fields.Float(string="Qty Invoiced", readonly=True)
    qty_to_invoice = fields.Float(string="Qty To Invoice", readonly=True)
    price_unit = fields.Float(string="Unit Price", aggregator="avg", readonly=True)
    price_average = fields.Monetary(
        string="Average Cost",
        readonly=True,
        aggregator="avg",
    )
    discount = fields.Float(string="Discount %", readonly=True, aggregator="avg")
    discount_amount = fields.Monetary(string="Discount Amount", readonly=True)
    price_subtotal = fields.Monetary(string="Untaxed Total", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    amount_taxexc_invoiced = fields.Monetary(
        string="Untaxed Amount Invoiced",
        readonly=True,
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Untaxed Amount To Invoice",
        readonly=True,
    )
    weight = fields.Float(string="Gross Weight", readonly=True)
    volume = fields.Float(string="Volume", readonly=True)

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    @api.readonly
    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.order_reference._name,
            "views": [[False, "form"]],
            "res_id": self.order_reference.id,
        }

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    @api.model
    def _get_done_states(self):
        return ["done"]

    def _case_value_or_one(self, value):
        """Helper to handle division by zero in currency rates."""
        return f"""CASE COALESCE({value}, 0) WHEN 0 THEN 1.0 ELSE {value} END"""

    # ------------------------------------------------------------
    # REGISTRY METHODS
    # ------------------------------------------------------------

    def _get_select_fields(self) -> dict:
        """Registry of fields for SELECT clause.

        Returns:
            dict: Mapping of {field_name: sql_expression}
        """
        currency_rate_o = self._case_value_or_one("o.currency_rate")
        currency_rate_table = self._case_value_or_one("account_currency_table.rate")

        fields = {
            "id": "MIN(l.id)",
            "order_reference": "CONCAT('sale.order', ',', o.id)",
            "company_id": "o.company_id",
            "currency_id": str(self.env.company.currency_id.id),
            "partner_id": "o.partner_id",
            "commercial_partner_id": "partner.commercial_partner_id",
            "country_id": "partner.country_id",
            "state_id": "partner.state_id",
            "partner_zip": "partner.zip",
            "industry_id": "partner.industry_id",
            "pricelist_id": "o.pricelist_id",
            "team_id": "o.team_id",
            "user_id": "o.user_id",
            "campaign_id": "o.campaign_id",
            "medium_id": "o.medium_id",
            "source_id": "o.source_id",
            "date_order": "o.date_order",
            "name": "o.name",
            "state": "o.state",
            "invoice_state": "o.invoice_state",
            "line_invoice_state": "l.invoice_state",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_category_id": "t.categ_id",
            "product_uom_id": "t.uom_id",
            "product_uom_qty": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_transferred": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_transferred * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_to_transfer": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM((l.product_qty - l.qty_transferred) * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_invoiced": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_invoiced * u.factor / u2.factor)
                    ELSE 0
                END""",
            "qty_to_invoice": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(l.qty_to_invoice * u.factor / u2.factor)
                    ELSE 0
                END""",
            "price_unit": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN AVG(
                        l.price_unit
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "price_average": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN (
                        SUM(
                            l.product_qty * l.price_unit
                            / {currency_rate_o}
                            * {currency_rate_table}
                        ) / NULLIF(
                            SUM(
                                l.product_qty * u.factor / u2.factor
                            ),
                            0.0
                        )
                    )
                    ELSE 0
                END""",
            "price_subtotal": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_subtotal
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "price_total": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_total
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "discount": "l.discount",
            "discount_amount": f"""CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(
                        l.price_unit * l.product_qty * l.discount / 100.0
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "amount_taxexc_invoiced": f"""CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment
                    THEN SUM(
                        l.amount_taxexc_invoiced
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "amount_taxexc_to_invoice": f"""CASE WHEN l.product_id IS NOT NULL OR l.is_downpayment
                    THEN SUM(
                        l.amount_taxexc_to_invoice
                        / {currency_rate_o}
                        * {currency_rate_table}
                    )
                    ELSE 0
                END""",
            "weight": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(p.weight * l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "volume": """CASE WHEN l.product_id IS NOT NULL
                    THEN SUM(p.volume * l.product_qty * u.factor / u2.factor)
                    ELSE 0
                END""",
            "nbr_lines": "COUNT(*)",
        }

        # Add additional fields from hook
        additional_fields = self._select_additional_fields()
        fields.update(additional_fields)

        return fields

    def _get_from_tables(self) -> list:
        """Registry of tables and JOINs for FROM clause.

        Returns:
            list: List of tuples (table_name, alias, join_type, on_condition)
        """
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies,
        )

        return [
            ("sale_order_line", "l", None, None),  # Base table
            ("sale_order", "o", "LEFT JOIN", "l.order_id=o.id"),
            ("res_partner", "partner", "LEFT JOIN", "o.partner_id=partner.id"),
            (
                currency_table,
                "account_currency_table",
                "LEFT JOIN",
                "o.company_id=account_currency_table.company_id",
            ),
            ("product_product", "p", "LEFT JOIN", "l.product_id=p.id"),
            ("product_template", "t", "LEFT JOIN", "p.product_tmpl_id=t.id"),
            ("uom_uom", "u", "LEFT JOIN", "l.product_uom_id=u.id"),
            ("uom_uom", "u2", "LEFT JOIN", "t.uom_id=u2.id"),
        ]

    def _get_where_conditions(self) -> list:
        """Registry of conditions for WHERE clause.

        Returns:
            list: List of SQL condition strings that will be AND'ed together
        """
        return [
            "l.display_type IS NULL",
        ]

    def _get_group_by_fields(self) -> list:
        """Registry of fields for GROUP BY clause.

        Returns:
            list: List of field expressions for GROUP BY clause
        """
        return [
            "l.product_id",
            "l.order_id",
            "l.price_unit",
            "l.invoice_state",
            "t.uom_id",
            "t.categ_id",
            "o.name",
            "o.date_order",
            "o.partner_id",
            "o.user_id",
            "o.state",
            "o.invoice_state",
            "o.company_id",
            "o.campaign_id",
            "o.medium_id",
            "o.source_id",
            "o.pricelist_id",
            "o.team_id",
            "p.product_tmpl_id",
            "partner.commercial_partner_id",
            "partner.country_id",
            "partner.industry_id",
            "partner.state_id",
            "partner.zip",
            "l.is_downpayment",
            "l.discount",
            "o.id",
            "account_currency_table.rate",
        ]

    def _select_additional_fields(self):
        """Hook to return additional fields SQL specification for select part of the table query.

        This method can be overridden by inheriting modules to add custom fields to the report.

        Returns:
            dict: Mapping field_name -> SQL computation of field

        Example:
            return {'custom_field': 'o.custom_column'}
        """
        return {}

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        """Override to correctly calculate the weighted average price of products."""
        if aggregate_spec != "price_average:avg":
            return super()._read_group_select(aggregate_spec, query)
        return SQL(
            "SUM(%(f_price)s * %(f_qty)s) / NULLIF(SUM(%(f_qty)s), 0.0)",
            f_qty=self._field_to_sql(self._table, "product_uom_qty", query),
            f_price=self._field_to_sql(self._table, "price_average", query),
        )
