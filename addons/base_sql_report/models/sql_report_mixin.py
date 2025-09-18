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

        :returns: Complete SQL query for the report view
        :rtype: SQL
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
        """Return CTE definition for the WITH clause (without the WITH keyword).

        Override to add Common Table Expressions. The mixin prepends ``WITH``
        automatically. Return empty ``SQL("")`` for no CTE (default).

        If you need multiple CTEs, separate them with commas inside the
        returned SQL object.

        :returns: CTE definition, or empty SQL for no CTE
        :rtype: SQL
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
        """Return field registry for the SELECT clause.

        Override to define report fields as ``{field_name: sql_expression}``.
        Dictionary order is preserved in the generated SQL.  Inheriting
        modules add, modify, or remove entries via standard dict operations.

        :returns: mapping of field names to SQL expressions
        :rtype: dict
        """
        return {}

    def _get_from_tables(self) -> list:
        """Return table registry for the FROM clause.

        Override to define tables and JOINs as a list of 4-tuples
        ``(table_name, alias, join_type, on_condition)``.  The first entry
        is the base table (``join_type=None``); subsequent entries are JOINs.
        ``table_name`` may be a string or a ``SQL`` object (for subqueries).

        Inheriting modules append, insert, or filter the list.

        :returns: list of ``(table_name, alias, join_type, on_condition)`` tuples
        :rtype: list
        """
        return []

    def _get_where_conditions(self) -> list:
        """Return condition registry for the WHERE clause.

        Override to define filter conditions as a list of SQL condition
        strings.  All conditions are joined with ``AND``.  Use parentheses
        for ``OR`` groups inside a single condition string.

        Inheriting modules append, filter, or replace entries in the list.

        :returns: list of SQL condition strings
        :rtype: list
        """
        return []

    def _get_group_by_fields(self) -> list:
        """Return field registry for the GROUP BY clause.

        Override to list all non-aggregated field expressions that must
        appear in ``GROUP BY``.  Fields using aggregate functions (SUM, AVG,
        MIN, MAX, COUNT) should **not** be included here.

        Inheriting modules append, filter, or reorder entries in the list.

        :returns: list of field expressions for GROUP BY
        :rtype: list
        """
        return []

    def _get_order_by_fields(self) -> list:
        """Return field registry for the ORDER BY clause (optional).

        Override to define custom sort expressions with direction (ASC/DESC).
        Most reports should use the ``_order`` class attribute instead; only
        use this for ORDER BY logic that requires runtime evaluation.

        :returns: list of field expressions with sort direction
        :rtype: list
        """
        return []
