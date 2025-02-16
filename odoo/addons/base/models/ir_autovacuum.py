# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import inspect
import logging
import random
import time

from odoo import api, models
from odoo.exceptions import AccessDenied
from odoo.modules.registry import _CACHES_BY_KEY
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def is_autovacuum(func):
    """ Return whether ``func`` is an autovacuum method. """
    return callable(func) and getattr(func, '_autovacuum', False)


class IrAutovacuum(models.AbstractModel):
    """ Helper model to the ``@api.autovacuum`` method decorator. """
    _name = 'ir.autovacuum'
    _description = 'Automatic Vacuum'

    def _run_vacuum_cleaner(self):
        """
        Perform a complete database cleanup by safely calling every
        ``@api.autovacuum`` decorated method.
        """
        if not self.env.is_admin():
            raise AccessDenied()

        methods = collections.deque(
            (model, attr, func)
            for model in self.env.values()
            for attr, func in inspect.getmembers(model.__class__, is_autovacuum)
        )
        # shuffle methods at each run, prevents one blocking method from running
        # the following ones
        random.shuffle(methods)
        while methods:
            self.env.cron_commit_progress(remaining=len(methods))
            model, attr, func = methods.pop()
            _logger.debug('Calling %s.%s()', model, attr)
            start_time = time.monotonic()
            try:
                result = func(model)
                if isinstance(result, tuple) and len(result) == 2:
                    func_done, func_remaining = result
                    _logger.debug(
                        '  vacuumed %r records, remaining %r',
                        func_done, func_remaining,
                    )
                    if func_remaining:
                        methods.appendleft((model, attr, func))
                self.env.cron_commit_progress(1)
            except Exception:  # noqa: BLE001
                self.env.cr.rollback()
                _logger.debug(" took %.2fs", time.monotonic() - start_time)
                _logger.exception("Failed %s.%s()", model, attr)

    @api.autovacuum
    def _gc_orm_signaling(self):
        for signal in ['registry', *_CACHES_BY_KEY]:
            table = f'orm_signaling_{signal}'
            # keep the last 10 entries for each signal, and all entries from the last
            # hour. This keeps the signaling tables small enough for performance, but
            # also gives a useful glimpse into the recent signaling history, including
            # the timestamps of the increments.
            self.env.cr.execute(SQL(
                "DELETE FROM %s WHERE id < (SELECT max(id)-9 FROM %s) AND date < NOW() - interval '1 hours'",
                SQL.identifier(table), SQL.identifier(table)
            ))
