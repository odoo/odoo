from odoo import api, fields, models
from odoo.tools.sql import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    order_reference = fields.Reference(
        selection_add=[("pos.order", "POS Order")],
    )
    state = fields.Selection(
        selection_add=[
            ("paid", "Paid"),
            ("invoiced", "Invoiced"),
            ("done", "Posted"),
        ],
    )

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    @api.model
    def _get_done_states(self):
        done_states = super()._get_done_states()
        done_states.extend(["paid", "invoiced", "done"])
        return done_states

    # ------------------------------------------------------------
    # QUERY OVERRIDE (UNION ALL with POS)
    # ------------------------------------------------------------

    @property
    def _table_query(self) -> SQL:
        """Override to add UNION ALL with POS orders.

        Returns:
            SQL: SQL object containing sale orders UNION ALL pos orders
        """
        sale_query = super()._table_query

        # Build POS query using registries
        pos_select = self._select_pos()
        pos_from = self._from_pos()
        pos_where = self._where_pos()
        pos_group_by = self._group_by_pos()

        pos_query = SQL(
            "SELECT %s FROM %s WHERE %s GROUP BY %s",
            pos_select,
            pos_from,
            pos_where,
            pos_group_by,
        )

        return SQL("( %s ) UNION ALL ( %s )", sale_query, pos_query)

    # ------------------------------------------------------------
    # POS QUERY BUILDERS (similar to mixin pattern)
    # ------------------------------------------------------------

    def _select_pos(self) -> SQL:
        """Build SELECT clause for POS orders from field registry."""
        fields = self._get_pos_select_fields()

        field_parts = []
        for field_name, expression in fields.items():
            field_parts.append(
                SQL("%s AS %s", SQL(expression), SQL.identifier(field_name)),
            )

        return SQL(",\n    ").join(field_parts)

    def _from_pos(self) -> SQL:
        """Build FROM clause for POS orders from table registry."""
        tables = self._get_pos_from_tables()

        from_parts = []
        for table_name, alias, join_type, on_condition in tables:
            if join_type is None:
                # Base table
                from_parts.append(SQL("%s %s", SQL(table_name), SQL(alias)))
            else:
                # JOIN clause
                if isinstance(table_name, SQL):
                    from_parts.append(
                        SQL(
                            "%s %s ON %s",
                            SQL(join_type),
                            table_name,
                            SQL(on_condition),
                        ),
                    )
                else:
                    from_parts.append(
                        SQL(
                            "%s %s %s ON %s",
                            SQL(join_type),
                            SQL(table_name),
                            SQL(alias),
                            SQL(on_condition),
                        ),
                    )

        return SQL("\n    ").join(from_parts)

    def _where_pos(self) -> SQL:
        """Build WHERE clause for POS orders from condition registry."""
        conditions = self._get_pos_where_conditions()
        return SQL("\n    AND ").join([SQL(cond) for cond in conditions])

    def _group_by_pos(self) -> SQL:
        """Build GROUP BY clause for POS orders from field registry."""
        fields = self._get_pos_group_by_fields()
        return SQL(",\n    ").join([SQL(field) for field in fields])

    # ------------------------------------------------------------
    # POS REGISTRIES (similar to mixin pattern)
    # ------------------------------------------------------------

    def _get_pos_select_fields(self) -> dict:
        """Registry of fields for POS SELECT clause.

        Returns:
            dict: Mapping of {field_name: sql_expression}
        """
        currency_rate_pos = self._case_value_or_one("pos.currency_rate")
        currency_rate_table = self._case_value_or_one("account_currency_table.rate")

        fields = {
            "id": "-MIN(l.id)",  # Negative to avoid ID conflicts with sale orders
            "order_reference": "CONCAT('pos.order', ',', pos.id)",
            "company_id": "pos.company_id",
            "currency_id": str(self.env.company.currency_id.id),
            "partner_id": "pos.partner_id",
            "commercial_partner_id": "partner.commercial_partner_id",
            "country_id": "partner.country_id",
            "state_id": "partner.state_id",
            "partner_zip": "partner.zip",
            "industry_id": "partner.industry_id",
            "pricelist_id": "pos.pricelist_id",
            "team_id": "pos.crm_team_id",
            "user_id": "pos.user_id",
            "campaign_id": "NULL",  # POS doesn't have UTM fields
            "medium_id": "NULL",
            "source_id": "NULL",
            "date_order": "pos.date_order",
            "name": "pos.name",
            "state": """CASE WHEN pos.state = 'done'
                    THEN 'done'
                    ELSE pos.state
                END""",
            "invoice_state": "NULL",
            "line_invoice_state": "NULL",
            "product_id": "l.product_id",
            "product_tmpl_id": "p.product_tmpl_id",
            "product_category_id": "t.categ_id",
            "product_uom_id": "t.uom_id",
            "product_uom_qty": "SUM(l.qty)",
            "qty_transferred": "SUM(l.qty_transferred)",
            "qty_to_transfer": "SUM(l.qty - l.qty_transferred)",
            "qty_invoiced": """CASE WHEN pos.account_move IS NOT NULL
                    THEN SUM(l.qty)
                    ELSE 0
                END""",
            "qty_to_invoice": """CASE WHEN pos.account_move IS NULL
                    THEN SUM(l.qty)
                    ELSE 0
                END""",
            "price_unit": f"""AVG(l.price_unit)
                    / MIN({currency_rate_pos})
                    * {currency_rate_table}""",
            "price_average": f"""(SUM(l.qty * l.price_unit)
                    / MIN({currency_rate_pos})
                    * {currency_rate_table})
                    / NULLIF(SUM(l.qty), 0.0)""",
            "price_subtotal": f"""SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal))
                    / MIN({currency_rate_pos})
                    * {currency_rate_table}""",
            "price_total": f"""SUM(SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal_incl))
                    / MIN({currency_rate_pos})
                    * {currency_rate_table}""",
            "discount": "l.discount",
            "discount_amount": f"""SUM(l.price_unit * l.discount * l.qty / 100.0
                    / {currency_rate_pos}
                    * {currency_rate_table})""",
            "amount_taxexc_invoiced": f"""(CASE WHEN pos.account_move IS NOT NULL
                    THEN SUM(l.price_subtotal)
                    ELSE 0
                END)
                    / MIN({currency_rate_pos})
                    * {currency_rate_table}""",
            "amount_taxexc_to_invoice": f"""(CASE WHEN pos.account_move IS NULL
                    THEN SUM(l.price_subtotal)
                    ELSE 0
                END)
                    / MIN({currency_rate_pos})
                    * {currency_rate_table}""",
            "weight": "SUM(p.weight * l.qty)",
            "volume": "SUM(p.volume * l.qty)",
            "nbr_lines": "COUNT(*)",
        }

        # Add additional fields from hooks (with POS-specific mappings)
        additional_fields = (
            self._get_select_fields()
        )  # Get sale.report additional fields
        additional_fields_info = self._fill_pos_fields(additional_fields)
        fields.update(additional_fields_info)

        return fields

    def _get_pos_from_tables(self) -> list:
        """Registry of tables and JOINs for POS FROM clause.

        Returns:
            list: List of tuples (table_name, alias, join_type, on_condition)
        """
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies,
        )

        return [
            ("pos_order_line", "l", None, None),  # Base table
            ("pos_order", "pos", "JOIN", "l.order_id = pos.id"),
            (
                "res_partner",
                "partner",
                "LEFT JOIN",
                "(pos.partner_id=partner.id OR pos.partner_id = NULL)",
            ),
            ("product_product", "p", "LEFT JOIN", "l.product_id=p.id"),
            ("product_template", "t", "LEFT JOIN", "p.product_tmpl_id=t.id"),
            ("uom_uom", "u", "LEFT JOIN", "u.id=t.uom_id"),
            ("pos_session", "session", "LEFT JOIN", "session.id = pos.session_id"),
            ("pos_config", "config", "LEFT JOIN", "config.id = session.config_id"),
            (
                "stock_picking_type",
                "picking",
                "LEFT JOIN",
                "picking.id = config.picking_type_id",
            ),
            (
                currency_table,
                "account_currency_table",
                "JOIN",
                "account_currency_table.company_id = pos.company_id",
            ),
        ]

    def _get_pos_where_conditions(self) -> list:
        """Registry of conditions for POS WHERE clause.

        Returns:
            list: List of SQL condition strings that will be AND'ed together
        """
        return [
            "l.sale_order_line_id IS NULL",  # Exclude lines linked to sale orders
        ]

    def _get_pos_group_by_fields(self) -> list:
        """Registry of fields for POS GROUP BY clause.

        Returns:
            list: List of field expressions for GROUP BY clause
        """
        return [
            "l.order_id",
            "l.product_id",
            "l.price_unit",
            "l.discount",
            "l.qty",
            "t.uom_id",
            "t.categ_id",
            "pos.id",
            "pos.name",
            "pos.date_order",
            "pos.partner_id",
            "pos.user_id",
            "pos.state",
            "pos.company_id",
            "pos.pricelist_id",
            "p.product_tmpl_id",
            "partner.commercial_partner_id",
            "partner.country_id",
            "partner.industry_id",
            "partner.state_id",
            "partner.zip",
            "u.factor",
            "pos.crm_team_id",
            "account_currency_table.rate",
            "picking.warehouse_id",
        ]

    # ------------------------------------------------------------
    # POS FIELD MAPPING HOOKS
    # ------------------------------------------------------------

    def _available_additional_pos_fields(self):
        """Hook to map additional sale.report fields to POS equivalents.

        Returns:
            dict: Mapping of {field_name: pos_sql_expression}
        """
        return {
            "warehouse_id": "picking.warehouse_id",
        }

    def _fill_pos_fields(self, additional_fields):
        """Fill additional fields for POS with appropriate values.

        For fields that exist in sale.report but not in POS, set to NULL.
        For fields that have POS equivalents, use the mapped expression.

        Args:
            additional_fields: Dictionary mapping fields with their values

        Returns:
            dict: Filtered dictionary with POS-compatible fields
        """
        # Start with NULL for all additional fields
        filled_fields = {}

        # Only include fields that are in the additional_fields from sale.report
        available_pos_mappings = self._available_additional_pos_fields()
        for fname in additional_fields:
            if fname in available_pos_mappings:
                # Use POS-specific mapping
                filled_fields[fname] = available_pos_mappings[fname]
            else:
                # Set to NULL for fields that don't exist in POS
                filled_fields[fname] = "NULL"

        return filled_fields
