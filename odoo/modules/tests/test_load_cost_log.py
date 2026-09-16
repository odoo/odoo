import logging
import types
import typing
from unittest import mock

from odoo.modules import loading
from odoo.modules.loading import _PackageLoader


def _loader(*, cursor_start, cursor_now, global_start, global_now, test_queries=0):
    loader: typing.Any = object.__new__(_PackageLoader)
    loader.cr = types.SimpleNamespace(sql_log_count=cursor_now)
    loader.cursor_queries_at_start = cursor_start
    loader.extra_queries_at_start = global_start
    loader.test_queries = test_queries
    loader.test_time = 0.0
    loader.test_results = None
    loader.started_at = 0.0
    loader.log_level = logging.INFO
    loader.index = 1
    loader.module_count = 1
    loader.operation = "upgrade"
    loader.package = types.SimpleNamespace(name="mod")
    return loader, mock.patch.object(
        loading.odoo, "db", types.SimpleNamespace(sql_counter=global_now)
    )


def test_other_queries_exclude_the_module_cursors_own(caplog):
    loader, patched = _loader(
        cursor_start=10, cursor_now=110, global_start=1000, global_now=1130
    )
    with patched, caplog.at_level(logging.INFO, logger="odoo.modules.loading"):
        loader.log_cost()
    assert "100 queries (+30 other)" in caplog.text, (
        "the process-wide counter includes this cursor's statements; only the "
        "remainder ran elsewhere"
    )


def test_test_queries_are_reported_apart_from_other(caplog):
    loader, patched = _loader(
        cursor_start=0, cursor_now=50, global_start=0, global_now=80, test_queries=20
    )
    with patched, caplog.at_level(logging.INFO, logger="odoo.modules.loading"):
        loader.log_cost()
    assert "50 queries (+20 test, +10 other)" in caplog.text


def test_a_module_that_ran_alone_reports_no_extras(caplog):
    loader, patched = _loader(
        cursor_start=5, cursor_now=45, global_start=200, global_now=240
    )
    with patched, caplog.at_level(logging.INFO, logger="odoo.modules.loading"):
        loader.log_cost()
    assert "40 queries" in caplog.text
    assert "other" not in caplog.text
