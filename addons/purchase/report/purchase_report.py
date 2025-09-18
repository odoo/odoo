from odoo import api, fields, models
from odoo.tools import Query, SQL

from odoo.addons.purchase import const


class PurchaseReport(models.Model):
    _name = "purchase.report"
    _inherit = "sql.report.mixin"
    _description = "Purchase Report"
    _auto = False
    _rec_name = "date_order"
    _order = "date_order desc, price_total desc"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    nbr_lines = fields.Integer(
        string="# of Lines",
        readonly=True,
    )
    order_reference = fields.Reference(
        string="Order",
        selection=[("purchase.order", "Purchase Order")],
        aggregator="count_distinct",
    )
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
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        readonly=True,
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Commercial Entity",
        readonly=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Partner Country",
        readonly=True,
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Buyer",
        readonly=True,
    )
    date_order = fields.Datetime(
        string="Order Date",
        readonly=True,
    )
    date_confirmed = fields.Datetime(
        string="Confirmation Date",
        readonly=True,
    )
    state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Status",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        readonly=True,
    )
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Reference Unit of Measure",
        readonly=True,
    )
    product_uom_qty = fields.Float(string="Qty Ordered", readonly=True)
    qty_transferred = fields.Float(string="Qty Received", readonly=True)
    qty_invoiced = fields.Float(string="Qty Billed", readonly=True)
    qty_to_invoice = fields.Float(string="Qty to be Billed", readonly=True)
    price_unit = fields.Float(string="Unit Price", aggregator="avg", readonly=True)
    price_average = fields.Monetary(
        string="Average Cost",
        readonly=True,
        aggregator="avg",
    )
    price_subtotal = fields.Monetary(string="Untaxed Total", readonly=True)
    price_total = fields.Monetary(string="Total", readonly=True)
    delay = fields.Float(
        string="Days to Confirm",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
        help="Amount of time between purchase confirmation and order by date.",
    )
    delay_pass = fields.Float(
        string="Days to Receive",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
        help="Amount of time between date planned and order by date for each purchase order line.",
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
    # REGISTRY METHODS
    # ------------------------------------------------------------

    def _get_select_fields(self) -> dict:
        """Registry of fields for SELECT clause.

        Returns:
            dict: Mapping of {field_name: SQL_expression}
                  Keys are field names (without AS clause)
                  Values are SQL expressions (can be multi-line strings)
                  Order is preserved (Python 3.7+ dict behavior)

        Example inheritance:
            def _get_select_fields(self):
                fields = super()._get_select_fields()
                fields['custom_field'] = 'o.custom_column'  # Add
                fields['price_unit'] = 'CUSTOM_CALCULATION'  # Modify
                del fields['unwanted_field']  # Remove
                return fields
        """
        return {
            "id": "MIN(l.id)",
            "order_reference": "CONCAT('purchase.order', ',', o.id)",
            "company_id": "o.company_id",
            "currency_id": "c.currency_id",
            "dest_address_id": "o.dest_address_id",
            "partner_id": "o.partner_id",
            "commercial_partner_id": "partner.commercial_partner_id",
            "country_id": "partner.country_id",
            "user_id": "o.user_id",
            "fiscal_position_id": "o.fiscal_position_id",
            "date_order": "o.date_order",
            "date_confirmed": "o.date_confirmed",
            "state": "o.state",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_category_id": "t.categ_id",
            "product_uom_id": "t.uom_id",
            "delay": """EXTRACT(
                    EPOCH FROM age(
                        o.date_confirmed, o.date_order
                    )
                ) / (24 * 60 * 60)::decimal(16,2)""",
            "delay_pass": """EXTRACT(
                    EPOCH FROM age(
                        l.date_planned, o.date_order
                    )
                ) / (24 * 60 * 60)::decimal(16,2)""",
            "product_uom_qty": """SUM(
                    l.product_qty * line_uom.factor / product_uom.factor
                )""",
            "qty_transferred": """SUM(
                    l.qty_transferred * line_uom.factor / product_uom.factor
                )""",
            "qty_invoiced": """SUM(
                    l.qty_invoiced * line_uom.factor / product_uom.factor
                )""",
            "qty_to_invoice": """CASE WHEN t.bill_policy = 'ordered'
                    THEN SUM(l.product_qty * line_uom.factor / product_uom.factor) - SUM(l.qty_invoiced * line_uom.factor / product_uom.factor)
                    ELSE SUM(l.qty_transferred * line_uom.factor / product_uom.factor) - SUM(l.qty_invoiced * line_uom.factor / product_uom.factor)
                END""",
            "price_unit": """AVG(
                    l.price_unit / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "price_average": """(
                    SUM(
                        l.product_qty * l.price_unit / COALESCE(o.currency_rate, 1.0)
                    ) / NULLIF(
                        SUM(
                            l.product_qty * line_uom.factor / product_uom.factor
                        ),
                        0.0
                    )
                )::decimal(16,2) * account_currency_table.rate""",
            "price_total": """SUM(
                    l.price_total / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "weight": """SUM(
                    p.weight * l.product_qty * line_uom.factor / product_uom.factor
                )""",
            "volume": """SUM(
                    p.volume * l.product_qty * line_uom.factor / product_uom.factor
                )""",
            "price_subtotal": """SUM(
                    l.price_subtotal / COALESCE(o.currency_rate, 1.0)
                )::decimal(16,2) * account_currency_table.rate""",
            "nbr_lines": "COUNT(*)",
        }

    def _get_from_tables(self) -> list:
        """Registry of tables and joins for FROM clause.

        Returns:
            list: List of tuples defining tables and joins.
                  Each tuple is: (table_name, alias, join_type, on_condition)
                  - table_name: Table name or SQL object (for subqueries/CTEs)
                  - alias: Table alias (or None for base table)
                  - join_type: None (base table), 'LEFT JOIN', 'INNER JOIN', etc.
                  - on_condition: JOIN condition string (or None for base table)

        Example inheritance:
            def _get_from_tables(self):
                tables = super()._get_from_tables()
                # Add new join
                tables.append(('custom_table', 'ct', 'LEFT JOIN', 'o.custom_id=ct.id'))
                # Remove a join (filter by alias)
                tables = [t for t in tables if t[1] != 'unwanted_alias']
                return tables
        """
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies,
        )

        return [
            ("purchase_order_line", "l", None, None),  # Base table
            ("purchase_order", "o", "LEFT JOIN", "l.order_id=o.id"),
            ("res_partner", "partner", "LEFT JOIN", "o.partner_id=partner.id"),
            (
                currency_table,
                "account_currency_table",
                "LEFT JOIN",
                "o.company_id=account_currency_table.company_id",
            ),
            ("product_product", "p", "LEFT JOIN", "l.product_id=p.id"),
            ("product_template", "t", "LEFT JOIN", "p.product_tmpl_id=t.id"),
            ("res_company", "c", "LEFT JOIN", "o.company_id=c.id"),
            ("uom_uom", "line_uom", "LEFT JOIN", "l.product_uom_id=line_uom.id"),
            ("uom_uom", "product_uom", "LEFT JOIN", "t.uom_id=product_uom.id"),
        ]

    def _get_where_conditions(self) -> list:
        """Registry of conditions for WHERE clause.

        Returns:
            list: List of SQL condition strings that will be AND'ed together

        Example inheritance:
            def _get_where_conditions(self):
                conditions = super()._get_where_conditions()
                # Add new condition
                conditions.append("o.state != 'cancel'")
                # Remove condition
                conditions = [c for c in conditions if 'display_type' not in c]
                return conditions
        """
        return [
            "l.display_type IS NULL",
        ]

    def _get_group_by_fields(self) -> list:
        """Registry of fields for GROUP BY clause.

        Returns:
            list: List of field expressions for GROUP BY clause.
                  These should be all non-aggregated fields from SELECT.

        Example inheritance:
            def _get_group_by_fields(self):
                fields = super()._get_group_by_fields()
                # Add new field
                fields.append('o.custom_field')
                # Remove field
                fields = [f for f in fields if 'unwanted' not in f]
                return fields
        """
        return [
            "o.company_id",
            "o.user_id",
            "o.partner_id",
            "line_uom.factor",
            "c.currency_id",
            "l.price_unit",
            "o.date_confirmed",
            "l.date_planned",
            "l.product_uom_id",
            "o.dest_address_id",
            "o.fiscal_position_id",
            "l.product_id",
            "p.product_tmpl_id",
            "t.categ_id",
            "o.date_order",
            "o.state",
            "t.uom_id",
            "t.bill_policy",
            "line_uom.id",
            "product_uom.factor",
            "partner.country_id",
            "partner.commercial_partner_id",
            "o.id",
            "account_currency_table.rate",
        ]

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        """This override allows us to correctly calculate the average price of products."""
        if aggregate_spec != "price_average:avg":
            return super()._read_group_select(aggregate_spec, query)
        return SQL(
            "SUM(%(f_price)s * %(f_qty)s) / NULLIF(SUM(%(f_qty)s), 0.0)",
            f_qty=self._field_to_sql(self._table, "product_uom_qty", query),
            f_price=self._field_to_sql(self._table, "price_average", query),
        )
