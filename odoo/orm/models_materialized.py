import time
import logging

from datetime import timedelta

from odoo import fields, _
from odoo.tools import SQL

from . import decorators as api
from .models import Model

_logger = logging.getLogger(__name__)


class MaterializedModel(Model):
    """ Model super-class for materialized views.

    A MaterializedModel is backed by a PostgreSQL materialized view instead of
    a regular table. It provides a framework for models that represent
    pre-computed aggregations or complex queries that benefit from being
    materialized for performance.

    materialized model should not have stored many2one fields since it doesn't
    have foreign keys. But computed many2one fields with ``exists()`` are allowed.

    Subclasses can:
    - Implement the init() method to create the materialized view
    - Add unique index on the view to allow concurrent refresh
    """
    _auto: bool = False         # do not automatically create database backend
    _register: bool = False     # not visible in ORM registry, meant to be python-inherited only
    _abstract = False           # not abstract
    _transient = False          # not transient

    _default_refresh_mode = 'non-concurrently'  # 'concurrently' is recommended especially when _web_auto_refresh is True
    _web_auto_refresh = False   # automatically refresh the view if it's stale after refresh the web page
    _stale_threshold = 3600     # 1 hour


    @api.model
    def freshness(self):
        """Get the version timestamp of the materialized view.

        Returns the last refresh timestamp and duration
        """
        model = self.env['ir.model']._get(self._name)
        return {
            'refresh_time': model.materialized_refresh_time,
            'refresh_duration': model.materialized_refresh_duration,
            'stale_threshold': self._stale_threshold,
            'web_auto_refresh': self._web_auto_refresh,
        }

    @api.model
    def refresh_stale(self, threshold=None, mode=None):
        """Refresh the materialized view if it's outdated.

        This method implements a simple throttling mechanism to avoid
        refreshing the view too frequently. It only refreshes if the
        version timestamp is before the timeout.

        If the view is locked by another transaction, it will raise a LockError.
        The web client should wait and try to refresh again later.

        Returns if the REFRESH MATERIAL

        """
        if threshold is None:
            threshold = self._stale_threshold
        outdated = fields.Datetime.now() - timedelta(seconds=threshold)
        last_refresh_time = self.freshness()['refresh_time']
        if not last_refresh_time or last_refresh_time < outdated:
            self._refresh(mode)
            return True
        return False

    @api.model
    def _refresh(self, mode=None):
        """Refresh the materialized view concurrently.

        This method:
        1. Invalidates all caches
        2. Updates the version timestamp in ir.model
        3. REFRESH MATERIALIZED VIEW

        """
        model = self.env['ir.model']._get(self._name)
        self.env.invalidate_all()
        # only one transaction is going to refresh the view at a time
        model.try_lock_for_update()
        time_start = time.monotonic()
        _logger.info(f"Refreshing materialized view {self._table} with mode {mode}")
        if mode == 'concurrently':
            self.env.cr.execute(SQL("REFRESH MATERIALIZED VIEW CONCURRENTLY %s", SQL.identifier(self._table)))
        else:
            self.env.cr.execute(SQL("REFRESH MATERIALIZED VIEW %s", SQL.identifier(self._table)))
        time_end = time.monotonic()
        model.materialized_refresh_time = fields.Datetime.now()
        model.materialized_refresh_duration = 0.2 * (int(time_end - time_start) + 1) + 0.8 * (model.materialized_refresh_duration)
