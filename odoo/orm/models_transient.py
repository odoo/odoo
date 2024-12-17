import datetime

from odoo.tools import SQL, config, lazy_classproperty
from odoo.tools.constants import GC_UNLINK_LIMIT

from . import decorators as api
from .models import Model


class TransientModel(Model):
    """ Model super-class for transient records, meant to be temporarily
    persistent, and regularly vacuum-cleaned.

    A TransientModel has a simplified access rights management, all users can
    create new records, and may only access the records they created. The
    superuser has unrestricted access to all TransientModel records.
    """
    _auto: bool = True          # automatically create database backend
    _register: bool = False     # not visible in ORM registry, meant to be python-inherited only
    _abstract = False           # not abstract
    _transient = True           # transient

    # default values for _transient_vacuum()
    _transient_max_count = lazy_classproperty(lambda _: int(config.get('osv_memory_count_limit')))
    "maximum number of transient records, unlimited if ``0``"
    _transient_max_hours = lazy_classproperty(lambda _: float(config.get('transient_age_limit')))
    "maximum idle lifetime (in hours), unlimited if ``0``"

    @api.autovacuum
    def _transient_vacuum(self):
        """Clean the transient records.

        This unlinks old records from the transient model tables whenever the
        :attr:`_transient_max_count` or :attr:`_transient_max_hours` conditions
        (if any) are reached.

        Actual cleaning will happen only once every 5 minutes. This means this
        method can be called frequently (e.g. whenever a new record is created).

        Example with both max_hours and max_count active:

        Suppose max_hours = 0.2 (aka 12 minutes), max_count = 20, there are
        55 rows in the table, 10 created/changed in the last 5 minutes, an
        additional 12 created/changed between 5 and 10 minutes ago, the rest
        created/changed more than 12 minutes ago.

        - age based vacuum will leave the 22 rows created/changed in the last 12
          minutes
        - count based vacuum will wipe out another 12 rows. Not just 2,
          otherwise each addition would immediately cause the maximum to be
          reached again.
        - the 10 rows that have been created/changed the last 5 minutes will NOT
          be deleted
        """
        has_remaining = False
        if self._transient_max_hours:
            # Age-based expiration
            has_remaining |= self._transient_clean_rows_older_than(self._transient_max_hours * 60 * 60)

        if self._transient_max_count:
            # Count-based expiration
            has_remaining |= self._transient_clean_old_rows(self._transient_max_count)
        # This method is shared by all transient models therefore,
        # return the model name to be logged and if whether there are more rows to process
        return self._name, has_remaining

    def _transient_clean_old_rows(self, max_count: int) -> bool:
        # Check how many rows we have in the table
        self._cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(self._table)))
        [count] = self._cr.fetchone()
        if count > max_count:
            return self._transient_clean_rows_older_than(300)
        return False

    def _transient_clean_rows_older_than(self, seconds: int) -> bool:
        # Never delete rows used in last 5 minutes
        seconds = max(seconds, 300)
        now = self.env.cr.now()
        domain = [('write_date', '<', now - datetime.timedelta(seconds=seconds))]
        records = self.sudo().search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records) == GC_UNLINK_LIMIT
