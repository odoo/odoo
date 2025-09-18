import logging

from odoo import models
from odoo.tools.sql import SQL


_logger = logging.getLogger(__name__)


class MaterializedViewMixin(models.AbstractModel):
    """Abstract mixin for models using PostgreSQL materialized views.

    This mixin provides:
    - Safe refresh() that handles missing views during upgrades
    - Helper methods to check view existence and population status
    - Error handling for concurrent access during view recreation

    Usage:
        class MyReport(models.Model):
            _name = 'my.report'
            _inherit = 'materialized.view.mixin'
            _auto = False

            def _query(self):
                return "SELECT * FROM ..."

            def init(self):
                self._create_materialized_view()
    """

    _name = "materialized.view.mixin"
    _description = "Materialized View Mixin"

    def _query(self):
        """Get SQL query for the materialized view.

        This method automatically detects if the model inherits from sql.report.mixin
        and uses its _table_query property. Otherwise, subclasses must override this
        method to provide the SQL query.

        Returns:
            SQL: SQL object for creating the materialized view

        Raises:
            NotImplementedError: If neither _table_query exists nor _query() is overridden

        Example:
            # Option 1: Use sql.report.mixin (recommended)
            class MyReport(models.Model):
                _inherit = ['sql.report.mixin', 'materialized.view.mixin']

                def _get_select_fields(self):
                    return {'id': 'MIN(id)', 'name': 'name'}

                # _query() is automatically provided!

            # Option 2: Manual SQL query
            class MyReport(models.Model):
                _inherit = 'materialized.view.mixin'

                def _query(self):
                    return SQL("SELECT id, name FROM my_table")
        """
        if hasattr(self, "_table_query"):
            # Model inherits sql.report.mixin - use registry pattern
            sql_obj = self._table_query
            if not isinstance(sql_obj, SQL):
                # _table_query exists but returns wrong type
                raise TypeError(
                    f"{self._name}._table_query must return a SQL object, "
                    f"got {type(sql_obj).__name__}: {sql_obj!r}",
                )
            if not sql_obj:  # Empty SQL object (bool(SQL("")) is False)
                raise ValueError(
                    f"{self._name}._table_query returned an empty SQL object",
                )
            # Return SQL object directly - don't mogrify to string
            return sql_obj
        # No registry pattern - subclass must override
        raise NotImplementedError(
            f"{self._name}: Either inherit 'sql.report.mixin' to use the registry "
            "pattern, or override _query() method to provide SQL manually.",
        )

    def _view_exists(self, table):
        """Check if the materialized view exists in the database.

        Args:
            table: Name of the table to check

        Returns:
            bool: True if the materialized view exists, False otherwise
        """
        self.env.cr.execute(
            SQL("SELECT 1 FROM pg_class WHERE relname = %s and relkind = 'm'", table),
        )
        return bool(self.env.cr.fetchone())

    def _is_populated(self, table):
        """Check if the materialized view is populated with data.

        Args:
            table: Name of the table to check

        Returns:
            bool: True if the view is populated, False otherwise
        """
        self.env.cr.execute(
            SQL("SELECT relispopulated FROM pg_class WHERE relname = %s and relkind = 'm'", table),
        )
        res = self.env.cr.fetchone()
        return res and res[0]

    def refresh(self):
        """Refresh the materialized view with current data.

        This method safely refreshes the materialized view, handling cases where:
        - The view doesn't exist yet (during module upgrade)
        - The view exists but is not populated
        - The view is populated and can be refreshed concurrently

        The CONCURRENTLY option allows queries against the materialized view
        while it's being refreshed, but requires the view to be populated first
        and to have a unique index.

        Returns:
            bool: True if refresh succeeded, False if skipped
        """
        # Check if the view exists before trying to refresh
        if not self._view_exists(self._table):
            # View doesn't exist yet - this can happen during module upgrade
            # when init() drops and recreates the view
            _logger.warning(
                "Materialized view %s does not exist. "
                "Skipping refresh. Run init() to create the view.",
                self._table,
            )
            return False

        # Refresh the view
        # Use CONCURRENTLY if the view is already populated to avoid locking
        try:
            is_populated = self._is_populated(self._table)
            table_name = SQL.identifier(self._table)

            if is_populated:
                _logger.info("Refreshing materialized view %s (concurrently)", self._table)
                self.env.cr.execute(
                    SQL("REFRESH MATERIALIZED VIEW CONCURRENTLY %s", table_name),
                )
            else:
                _logger.info("Refreshing materialized view %s (with lock)", self._table)
                self.env.cr.execute(
                    SQL("REFRESH MATERIALIZED VIEW %s", table_name),
                )
            return True
        except Exception as e:
            # Log the error but don't crash - the cron will retry later
            _logger.error(
                "Failed to refresh materialized view %s: %s. "
                "Will retry on next cron run.",
                self._table,
                e,
            )
            return False

    def _cron_refresh_materialized_view(self):
        """Cron job wrapper to refresh the materialized view.

        This method provides a consistent API for cron jobs across all models
        that inherit from this mixin. It simply delegates to refresh().

        Returns:
            bool: True if refresh succeeded, False if skipped or failed
        """
        return self.refresh()

    def _create_materialized_view(self, with_data=False, index_field=None):
        """Create or recreate the materialized view with unique index.

        This is a helper method that can be called from init() to standardize
        materialized view creation across all report models.

        Args:
            with_data: bool, if True creates the view WITH DATA (populated),
                      if False creates WITH NO DATA (empty, faster for upgrades)
            index_field: str, field name for unique index. If None, uses 'id'.
                        Required for CONCURRENT refresh to work.

        Note:
            Subclasses must implement _query() method that returns a SQL object.
            The unique index enables REFRESH MATERIALIZED VIEW CONCURRENTLY.
        """
        table_name = SQL.identifier(self._table)
        query_sql = self._query()  # Returns SQL object

        # Determine index field (default to 'id')
        if index_field is None:
            index_field = "id"

        # Drop existing view/materialized view if it exists
        # Handle migration from regular VIEW (sql.report.mixin) to MATERIALIZED VIEW
        # PostgreSQL: relkind 'v' = view, 'm' = materialized view
        self.env.cr.execute(
            "SELECT relkind FROM pg_class WHERE relname = %s", (self._table,)
        )
        result = self.env.cr.fetchone()
        if result:
            if result[0] == "v":
                _logger.info("Dropping regular view %s (migration to materialized)", self._table)
                self.env.cr.execute(SQL("DROP VIEW IF EXISTS %s CASCADE", table_name))
            elif result[0] == "m":
                _logger.info("Dropping materialized view %s", self._table)
                self.env.cr.execute(SQL("DROP MATERIALIZED VIEW IF EXISTS %s CASCADE", table_name))

        # Create the view - compose SQL objects using parameter substitution
        if with_data:
            _logger.info("Creating materialized view %s WITH DATA", self._table)
            self.env.cr.execute(
                SQL("CREATE MATERIALIZED VIEW %s AS %s", table_name, query_sql),
            )
        else:
            _logger.info(
                "Creating materialized view %s WITH NO DATA (will be populated by cron)",
                self._table,
            )
            self.env.cr.execute(
                SQL("CREATE MATERIALIZED VIEW %s AS %s WITH NO DATA", table_name, query_sql),
            )

        # Create unique index for concurrent refresh support
        index_name = SQL.identifier(f"id_{self._table}")
        index_field_sql = SQL.identifier(index_field)
        _logger.info(
            "Creating unique index on %s.%s for concurrent refresh",
            self._table,
            index_field,
        )
        self.env.cr.execute(
            SQL(
                "CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s (%s)",
                index_name,
                table_name,
                index_field_sql,
            ),
        )
