import datetime

from odoo.libs.debug_log import DebugLog
from odoo.tools import config, lazy_classproperty

from .. import decorators as api
from ..domain import Domain
from ..primitives import GC_UNLINK_LIMIT
from .base import Model

_TRANSIENT_VACUUM_MIN_AGE_SECONDS = 300
_debug = DebugLog(__name__)


class TransientModel(Model):
    _auto: bool = True
    _register: bool = False
    _abstract = False
    _transient = True

    _transient_max_count = lazy_classproperty(
        lambda _: int(config.get("osv_memory_count_limit"))
    )
    _transient_max_hours = lazy_classproperty(
        lambda _: float(config.get("transient_age_limit"))
    )

    @api.autovacuum
    def _vacuum_transient_rows(self) -> tuple[int, bool]:
        counts = []
        if self._transient_max_hours:
            counts.append(
                self._remove_transient_rows_older_than(
                    self._transient_max_hours * 60 * 60
                )
            )

        if self._transient_max_count:
            counts.append(
                self._remove_transient_rows_over_count(self._transient_max_count)
            )
        _debug.pipeline(
            "transient.vacuum",
            model=self._name,
            max_hours=self._transient_max_hours,
            max_count=self._transient_max_count,
            removed=sum(counts),
            limit_hit=any(count >= GC_UNLINK_LIMIT for count in counts),
        )
        return sum(counts), any(count >= GC_UNLINK_LIMIT for count in counts)

    def _remove_transient_rows_over_count(self, max_count: int) -> int:
        if self.env.backend.has_rows_beyond(self, max_count):
            _debug.logic("transient.over_count", model=self._name, max_count=max_count)
            return self._remove_transient_rows_older_than(
                _TRANSIENT_VACUUM_MIN_AGE_SECONDS
            )
        return 0

    def _remove_transient_rows_older_than(self, seconds: float) -> int:
        seconds = max(seconds, _TRANSIENT_VACUUM_MIN_AGE_SECONDS)
        now = self.env.cr.now()
        domain = Domain("write_date", "<", now - datetime.timedelta(seconds=seconds))
        records = self.sudo().search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        _debug.lifecycle(
            "transient.vacuumed",
            model=self._name,
            older_than_s=seconds,
            removed=len(records),
            limit_hit=len(records) >= GC_UNLINK_LIMIT,
        )
        return len(records)
