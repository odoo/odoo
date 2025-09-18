from odoo import models
from odoo.tools.sql import SQL


class SqlReportMixin(models.AbstractModel):
    """Mixin for SQL-based analytical reports with registry-driven construction.

    This mixin provides a clean inheritance pattern for Odoo SQL reports (_auto = False)
    where SQL clauses are built from structured registries (dicts/lists) rather than
    string manipulation. This makes reports much easier to extend via inheritance.

    Design Philosophy
    -----------------
    Traditional Odoo reports build SQL using monolithic methods that return complete
    clauses (e.g., "_select_sale() returns 'SELECT ... AS id, ...'"). This makes
    inheritance difficult because you need string manipulation to modify the SQL.

    This mixin uses the **Registry Pattern** where each clause is built from structured
    data (dicts for SELECT, lists for FROM/WHERE/GROUP BY). Inheriting modules simply
    modify the registry data structures - no SQL string parsing required.

    Based on the excellent design in addons/purchase/report/purchase_report.py

    Architecture
    ------------
    1. **Registry Methods** (_get_*): Return structured data (dict/list)
       - _get_select_fields() → dict: {field_name: sql_expression}
       - _get_from_tables() → list: [(table, alias, join_type, on_condition)]
       - _get_where_conditions() → list: [condition_string]
       - _get_group_by_fields() → list: [field_expression]
       - _get_order_by_fields() → list: [field_expression]  (optional)
       - _with_cte() → SQL: CTE definition (optional)

    2. **Builder Methods** (_select, _from, _where, _group_by, _order_by):
       - Called by _table_query to construct SQL from registries
       - Handle formatting, SQL object creation, and joining
       - Generally should NOT be overridden (override registries instead)

    3. **Main Query Method** (_table_query):
       - Property that assembles final SQL from builder methods
       - Handles optional clauses (WITH, WHERE, ORDER BY)
       - Should NOT be overridden unless you need custom assembly logic

    Usage Example
    -------------
    class MyReport(models.Model):
        _name = 'my.report'
        _inherit = 'sql.report.mixin'
        _description = 'My Analysis Report'
        _auto = False

        # Define fields
        id = fields.Integer(readonly=True)
        product_id = fields.Many2one('product.product', readonly=True)
        total_qty = fields.Float(readonly=True)

        # Implement registries
        def _get_select_fields(self):
            return {
                'id': 'MIN(l.id)',
                'product_id': 'l.product_id',
                'total_qty': 'SUM(l.quantity)',
            }

        def _get_from_tables(self):
            return [
                ('sale_order_line', 'l', None, None),  # Base table
                ('sale_order', 'o', 'LEFT JOIN', 'l.order_id=o.id'),
            ]

        def _get_where_conditions(self):
            return ['l.display_type IS NULL']

        def _get_group_by_fields(self):
            return ['l.product_id']

    Inheritance Example
    -------------------
    class MyReportInherit(models.Model):
        _inherit = 'my.report'

        margin = fields.Monetary(readonly=True)

        def _get_select_fields(self):
            fields = super()._get_select_fields()
            fields['margin'] = 'SUM(l.margin)'  # Add field
            fields['total_qty'] = 'SUM(l.quantity * 2)'  # Modify field
            return fields

        def _get_where_conditions(self):
            conditions = super()._get_where_conditions()
            conditions.append("o.state != 'cancel'")  # Add condition
            return conditions

    Benefits
    --------
    Clear separation: Data (registries) vs Logic (builders)
    Easy inheritance: Add/modify/remove via dict/list operations
    Type safety: SQL objects prevent injection
    Readable: Registry structure is self-documenting
    Testable: Can unit test registries independently
    Maintainable: No fragile string manipulation
    Consistent: Same pattern across all reports
    """

    _name = "sql.report.mixin"
    _description = "SQL Report Construction Helper"
    _auto = False

    # ============================================================
    # MAIN QUERY ASSEMBLY
    # ============================================================

    def _query(self):
        """Return SQL query object for compatibility with materialized.view.mixin.

        This method bridges the registry pattern with the materialized view mixin
        by delegating to _table_query property.

        When used with materialized.view.mixin, this allows _create_materialized_view()
        to work correctly by calling self._query() which delegates to _table_query.

        Returns:
            SQL: Complete SQL query built from registries
        """
        return self._table_query

    @property
    def _table_query(self) -> SQL:
        """Build complete SQL query from registries.

        Assembles the final SQL query by calling builder methods in the correct
        order and handling optional clauses (WITH, WHERE, GROUP BY, ORDER BY).

        This method should rarely be overridden. Instead, customize behavior by
        overriding registry methods (_get_select_fields, etc.).

        Returns:
            SQL: Complete SQL query for the report view

        Example Output:
            WITH my_cte AS (SELECT ...)
            SELECT
                MIN(l.id) AS id,
                l.product_id AS product_id,
                SUM(l.quantity) AS total_qty
            FROM
                sale_order_line l
                LEFT JOIN sale_order o ON l.order_id=o.id
            WHERE
                l.display_type IS NULL
            GROUP BY
                l.product_id
            ORDER BY
                total_qty DESC
        """
        cte = self._with_cte()
        select = self._select()
        from_clause = self._from()
        where = self._where()
        group_by = self._group_by()
        order_by = self._order_by()

        # Build query parts (optional clauses are skipped if empty)
        parts = []

        if cte:
            parts.append(SQL("WITH %s", cte))

        parts.extend([select, from_clause])

        if where:
            parts.append(where)

        if group_by:
            parts.append(group_by)

        if order_by:
            parts.append(order_by)

        return SQL("\n").join(parts)

    # ============================================================
    # BUILDER METHODS (construct SQL from registries)
    # ============================================================

    def _with_cte(self) -> SQL:
        """Optional WITH clause for Common Table Expressions (CTEs).

        Override this method to add CTEs to your query. Return the CTE definition
        WITHOUT the "WITH" keyword (the mixin adds it automatically).

        Returns:
            SQL: CTE definition (without WITH keyword), or empty SQL for no CTE

        Example:
            def _with_cte(self):
                return SQL('''
                    ranked_products AS (
                        SELECT
                            product_id,
                            ROW_NUMBER() OVER (PARTITION BY categ_id ORDER BY qty DESC) as rank
                        FROM product_sales
                    )
                ''')

        Note:
            If you need multiple CTEs, separate them with commas:
            return SQL("cte1 AS (SELECT ...), cte2 AS (SELECT ...)")
        """
        return SQL("")

    def _select(self) -> SQL:
        """Build SELECT clause from field registry.

        Constructs the SELECT clause by iterating over the field registry and
        formatting each field as "expression AS field_name".

        Do NOT override this method. Instead, override _get_select_fields() to
        customize the field list.

        Returns:
            SQL: SELECT clause with all fields, nicely formatted

        Example Output:
            SELECT
                MIN(l.id) AS id,
                l.product_id AS product_id,
                SUM(l.quantity) AS total_qty
        """
        fields = self._get_select_fields()

        field_parts = []
        for field_name, expression in fields.items():
            field_parts.append(
                SQL("%s AS %s", SQL(expression), SQL.identifier(field_name)),
            )

        return SQL("SELECT\n    %s", SQL(",\n    ").join(field_parts))

    def _from(self) -> SQL:
        """Build FROM clause from table registry.

        Constructs the FROM clause with base table and all JOINs by iterating over
        the table registry. Handles both string table names and SQL objects
        (for currency tables, subqueries, etc.).

        Do NOT override this method. Instead, override _get_from_tables() to
        customize tables and joins.

        Returns:
            SQL: FROM clause with all JOINs, nicely formatted

        Example Output:
            FROM
                sale_order_line l
                LEFT JOIN sale_order o ON l.order_id=o.id
                LEFT JOIN res_partner p ON o.partner_id=p.id
        """
        tables = self._get_from_tables()
        from_parts = []

        for table_name, alias, join_type, on_condition in tables:
            if join_type is None:
                # Base table (first FROM clause)
                if alias:
                    table_sql = (
                        table_name if isinstance(table_name, SQL) else SQL(table_name)
                    )
                    from_parts.append(SQL("%s %s", table_sql, SQL(alias)))
                else:
                    from_parts.append(
                        table_name if isinstance(table_name, SQL) else SQL(table_name),
                    )
            else:
                # JOIN clause
                if isinstance(table_name, SQL):
                    # SQL object (e.g., currency_table) - use as-is
                    if on_condition:
                        from_parts.append(
                            SQL(
                                "%s %s ON %s",
                                SQL(join_type),
                                table_name,
                                SQL(on_condition),
                            ),
                        )
                    else:
                        from_parts.append(SQL("%s %s", SQL(join_type), table_name))
                else:
                    # String table name - add alias
                    table_sql = SQL(table_name)
                    alias_sql = SQL(alias) if alias else SQL("")
                    if on_condition:
                        from_parts.append(
                            SQL(
                                "%s %s %s ON %s",
                                SQL(join_type),
                                table_sql,
                                alias_sql,
                                SQL(on_condition),
                            ),
                        )
                    else:
                        from_parts.append(
                            SQL("%s %s %s", SQL(join_type), table_sql, alias_sql),
                        )

        return SQL("FROM\n    %s", SQL("\n    ").join(from_parts))

    def _where(self) -> SQL:
        """Build WHERE clause from condition registry.

        Constructs the WHERE clause by joining all conditions with AND.
        Returns empty SQL if no conditions exist (optional WHERE clause).

        Do NOT override this method. Instead, override _get_where_conditions()
        to customize filter conditions.

        Returns:
            SQL: WHERE clause with all conditions, or empty SQL if no conditions

        Example Output:
            WHERE
                l.display_type IS NULL
                AND o.state != 'cancel'
                AND o.amount_total > 0
        """
        conditions = self._get_where_conditions()

        if not conditions:
            return SQL("")

        condition_parts = [SQL(cond) for cond in conditions]
        return SQL("WHERE\n    %s", SQL("\n    AND ").join(condition_parts))

    def _group_by(self) -> SQL:
        """Build GROUP BY clause from field registry.

        Constructs the GROUP BY clause by joining all field expressions.
        Returns empty SQL if no fields exist (optional GROUP BY clause).

        Do NOT override this method. Instead, override _get_group_by_fields()
        to customize grouping fields.

        Returns:
            SQL: GROUP BY clause with all fields, or empty SQL if no fields

        Example Output:
            GROUP BY
                l.product_id,
                o.partner_id,
                o.date_order
        """
        fields = self._get_group_by_fields()

        if not fields:
            return SQL("")

        field_parts = [SQL(field) for field in fields]
        return SQL("GROUP BY\n    %s", SQL(",\n    ").join(field_parts))

    def _order_by(self) -> SQL:
        """Build ORDER BY clause from field registry.

        Constructs the ORDER BY clause by joining all field expressions.
        Returns empty SQL if no fields exist (optional ORDER BY clause).

        Do NOT override this method. Instead, override _get_order_by_fields()
        to customize sort order.

        Returns:
            SQL: ORDER BY clause with all fields, or empty SQL if no fields

        Example Output:
            ORDER BY
                o.date_order DESC,
                o.id

        Note:
            Usually not needed - use the _order class attribute instead.
            Only use this for complex ORDER BY that can't be expressed in _order.
        """
        fields = self._get_order_by_fields()

        if not fields:
            return SQL("")

        field_parts = [SQL(field) for field in fields]
        return SQL("ORDER BY\n    %s", SQL(",\n    ").join(field_parts))

    # ============================================================
    # REGISTRY METHODS (override these in subclass)
    # ============================================================

    def _get_select_fields(self) -> dict:
        """Registry of fields for SELECT clause.

        Override this method to define the fields in your report's SELECT clause.
        Return a dictionary mapping field names to SQL expressions.

        The dictionary order is preserved (Python 3.7+ behavior), so fields will
        appear in the SELECT clause in the order you define them.

        Returns:
            dict: Mapping of {field_name: sql_expression}
                - Keys: Field names (will be used with SQL.identifier for safety)
                - Values: SQL expressions (strings or SQL objects)

        Example:
            def _get_select_fields(self):
                return {
                    'id': 'MIN(l.id)',
                    'order_reference': "CONCAT('sale.order', ',', o.id)",
                    'product_id': 'l.product_id',
                    'partner_id': 'o.partner_id',
                    'total_qty': 'SUM(l.product_uom_qty)',
                    'price_total': '''SUM(
                        l.price_total / COALESCE(o.currency_rate, 1.0)
                    ) * currency_table.rate''',  # Multi-line expressions OK
                }

        Inheritance - Add Field:
            def _get_select_fields(self):
                fields = super()._get_select_fields()
                fields['margin'] = 'SUM(l.margin)'
                return fields

        Inheritance - Modify Field:
            def _get_select_fields(self):
                fields = super()._get_select_fields()
                fields['price_total'] = 'SUM(l.custom_price)'
                return fields

        Inheritance - Remove Field:
            def _get_select_fields(self):
                fields = super()._get_select_fields()
                del fields['unwanted_field']
                return fields

        Inheritance - Reorder Fields:
            def _get_select_fields(self):
                fields = super()._get_select_fields()
                # Move 'margin' to end
                margin = fields.pop('margin')
                fields['margin'] = margin
                return fields
        """
        return {}

    def _get_from_tables(self) -> list:
        """Registry of tables and JOINs for FROM clause.

        Override this method to define the tables and joins in your report's
        FROM clause. Return a list of tuples, where each tuple represents
        either the base table or a JOIN.

        Returns:
            list: List of tuples (table_name, alias, join_type, on_condition)
                - table_name: Table name (str) or SQL object (for subqueries/CTEs)
                - alias: Table alias (str) or None for base table
                - join_type: None for base table, or 'LEFT JOIN', 'INNER JOIN', etc.
                - on_condition: JOIN condition (str) or None for base table

        Example:
            def _get_from_tables(self):
                currency_table = self.env['res.currency']._get_simple_currency_table(
                    self.env.companies
                )

                return [
                    # Base table (first FROM)
                    ('sale_order_line', 'l', None, None),

                    # Regular JOINs
                    ('sale_order', 'o', 'LEFT JOIN', 'l.order_id=o.id'),
                    ('res_partner', 'p', 'LEFT JOIN', 'o.partner_id=p.id'),
                    ('product_product', 'prod', 'INNER JOIN', 'l.product_id=prod.id'),

                    # SQL object (currency table)
                    (currency_table, 'currency_table', 'LEFT JOIN',
                     'o.company_id=currency_table.company_id'),
                ]

        Inheritance - Add JOIN:
            def _get_from_tables(self):
                tables = super()._get_from_tables()
                tables.append(
                    ('custom_table', 'ct', 'LEFT JOIN', 'o.custom_id=ct.id')
                )
                return tables

        Inheritance - Insert JOIN at Specific Position:
            def _get_from_tables(self):
                tables = super()._get_from_tables()
                # Insert after base table (position 1)
                tables.insert(1, ('early_table', 'et', 'LEFT JOIN', 'l.id=et.line_id'))
                return tables

        Inheritance - Remove JOIN by Alias:
            def _get_from_tables(self):
                tables = super()._get_from_tables()
                # Remove join with alias 'unwanted_alias'
                tables = [t for t in tables if t[1] != 'unwanted_alias']
                return tables

        Inheritance - Modify JOIN Condition:
            def _get_from_tables(self):
                tables = super()._get_from_tables()
                # Change ON condition for 'partner' join
                tables = [
                    (t[0], t[1], t[2], 'o.partner_id=p.id AND p.active=true')
                    if t[1] == 'p' else t
                    for t in tables
                ]
                return tables
        """
        return []

    def _get_where_conditions(self) -> list:
        """Registry of conditions for WHERE clause.

        Override this method to define the filter conditions in your report's
        WHERE clause. Return a list of condition strings that will be joined
        with AND.

        Returns:
            list: List of SQL condition strings (will be AND'ed together)

        Example:
            def _get_where_conditions(self):
                return [
                    'l.display_type IS NULL',
                    "o.state != 'cancel'",
                    'o.amount_total > 0',
                ]

        Advanced Example - OR Conditions:
            def _get_where_conditions(self):
                return [
                    'l.display_type IS NULL',
                    # Use parentheses for OR
                    "(o.state = 'sale' OR o.state = 'done')",
                ]

        Inheritance - Add Condition:
            def _get_where_conditions(self):
                conditions = super()._get_where_conditions()
                conditions.append("o.date_order >= '2024-01-01'")
                return conditions

        Inheritance - Remove Condition:
            def _get_where_conditions(self):
                conditions = super()._get_where_conditions()
                # Remove conditions containing 'display_type'
                conditions = [c for c in conditions if 'display_type' not in c]
                return conditions

        Inheritance - Replace Condition:
            def _get_where_conditions(self):
                conditions = super()._get_where_conditions()
                # Replace state condition
                conditions = [
                    "o.state IN ('sale', 'done', 'processing')"
                    if 'state' in c else c
                    for c in conditions
                ]
                return conditions
        """
        return []

    def _get_group_by_fields(self) -> list:
        """Registry of fields for GROUP BY clause.

        Override this method to define the grouping fields in your report's
        GROUP BY clause. These should include ALL non-aggregated fields from
        the SELECT clause.

        Returns:
            list: List of field expressions for GROUP BY

        Example:
            def _get_group_by_fields(self):
                return [
                    'l.product_id',
                    'o.partner_id',
                    'o.date_order',
                    'o.state',
                    'o.company_id',
                ]

        Note:
            Fields with aggregate functions (SUM, AVG, MIN, MAX, COUNT) should
            NOT be in GROUP BY. Only non-aggregated fields go here.

        Inheritance - Add Field:
            def _get_group_by_fields(self):
                fields = super()._get_group_by_fields()
                fields.append('o.warehouse_id')
                return fields

        Inheritance - Remove Field:
            def _get_group_by_fields(self):
                fields = super()._get_group_by_fields()
                # Remove partner grouping
                fields = [f for f in fields if 'partner' not in f]
                return fields

        Inheritance - Insert at Position:
            def _get_group_by_fields(self):
                fields = super()._get_group_by_fields()
                # Insert early in list
                fields.insert(0, 'o.company_id')
                return fields
        """
        return []

    def _get_order_by_fields(self) -> list:
        """Registry of fields for ORDER BY clause (optional).

        Override this method to define custom ORDER BY logic that can't be
        expressed using the _order class attribute. Most reports should use
        _order instead of this method.

        Returns:
            list: List of field expressions with sort direction (ASC/DESC)

        Example:
            def _get_order_by_fields(self):
                return [
                    'o.date_order DESC',
                    'o.name ASC',
                ]

        Note:
            Usually not needed - prefer using the _order class attribute:
                _order = 'date_order desc, name'

            Only use this for complex ORDER BY that requires runtime logic.

        Inheritance - Add Sort Field:
            def _get_order_by_fields(self):
                fields = super()._get_order_by_fields()
                fields.append('o.priority DESC')
                return fields
        """
        return []
