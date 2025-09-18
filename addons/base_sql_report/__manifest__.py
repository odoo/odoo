{
    "name": "Base SQL Report",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "SQL report construction and materialized view mixins",
    "description": """
Base SQL Report
===============

This module provides foundational mixins for building SQL-based analytical
reports using clean, registry-driven patterns.

Materialized View Mixin
------------------------
The ``materialized.view.mixin`` provides safe refresh() and helper methods for
models backed by PostgreSQL materialized views:

* **Safe refresh()**: Handles missing views during upgrades
* **View existence checks**: ``_view_exists()`` helper method
* **Population status**: ``_is_populated()`` helper method
* **Concurrent refresh**: Automatic CONCURRENTLY when view is populated
* **Error handling**: Graceful failures with logging for cron retry
* **Auto-detection**: Works with both registry pattern (``_table_query``) and custom ``_query()``

Usage Pattern 1 - Custom SQL with CTEs (for complex analytical queries)::

    class ComplexReport(models.Model):
        _inherit = 'materialized.view.mixin'
        _auto = False

        def _query(self):
            return '''
                WITH cte1 AS (...),
                     cte2 AS (...)
                SELECT ... FROM cte1 JOIN cte2 ...
            '''

        def init(self):
            self._create_materialized_view()

Usage Pattern 2 - Registry Pattern (for maintainable, extensible queries)::

    class ExtensibleReport(models.Model):
        _inherit = ['sql.report.mixin', 'materialized.view.mixin']
        _auto = False

        def _get_select_fields(self):
            return {'id': 'MIN(l.id)', 'total': 'SUM(l.amount)'}

        def _get_from_tables(self):
            return [('sale_order_line', 'l', None, None)]

        # _query() automatically uses _table_query!

        def init(self):
            self._create_materialized_view()

SQL Report Mixin
----------------
The ``sql.report.mixin`` provides a clean inheritance pattern for SQL-based
analytical reports (``_auto = False``) using the **Registry Pattern**:

* **SELECT fields**: Dict-based registry - easy add/modify/remove
* **FROM tables**: List-based registry - structured JOIN management
* **WHERE conditions**: List of conditions joined with AND
* **GROUP BY fields**: List of grouping expressions
* **ORDER BY fields**: List of ordering expressions (optional)
* **WITH CTEs**: Support for Common Table Expressions

Based on the excellent design in addons/purchase/report/purchase_report.py

Benefits vs traditional string manipulation:

* Add fields: ``fields['margin'] = 'SUM(l.margin)'``
* Modify fields: ``fields['total'] = 'CUSTOM_CALC'``
* Remove fields: ``del fields['unwanted']``
* Add JOINs: ``tables.append(('custom_table', 'ct', 'LEFT JOIN', 'o.id=ct.order_id'))``
* Filter JOINs: ``[t for t in tables if t[1] != 'unwanted_alias']``
* Add WHERE: ``conditions.append("o.state != 'cancel'")``
* No SQL string parsing/regex required!

Design Goals
------------
* Eliminate code duplication across analytical report modules
* Provide clean extension points for customization via inheritance
* Make SQL report behavior consistent and predictable
* Improve code readability and maintainability
* Type safety through SQL objects to prevent injection

Usage Example
-------------

::

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
                ('sale_order_line', 'l', None, None),
                ('sale_order', 'o', 'LEFT JOIN', 'l.order_id=o.id'),
            ]

        def _get_where_conditions(self):
            return ['l.display_type IS NULL']

        def _get_group_by_fields(self):
            return ['l.product_id']

This module is part of an aggressive refactoring initiative for Odoo 19+ with
no backward compatibility constraints.
    """,
    "author": "Odoo Community",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
