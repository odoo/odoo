import functools
import os
import pathlib
import random
import threading
import zlib

import pytest

from .._pg import repo_root

SHUFFLE_SEED_VAR = "ODOO_SERVICE_TEST_SHUFFLE_SEED"


def pytest_collection_modifyitems(session, config, items):
    raw = os.environ.get(SHUFFLE_SEED_VAR)
    if not raw:
        return
    try:
        seed = int(raw)
    except ValueError:
        seed = zlib.crc32(raw.encode())
    random.Random(seed).shuffle(items)


def pytest_report_header(config):
    raw = os.environ.get(SHUFFLE_SEED_VAR)
    if raw:
        return f"service suite: collection shuffled with {SHUFFLE_SEED_VAR}={raw}"
    return None


@pytest.fixture(autouse=True)
def _no_global_state_leak():
    from odoo.service import _process_state

    thread = threading.current_thread()
    missing = object()

    from odoo.service import _base_server

    def snapshot():
        return {
            # A hook registered and not taken back runs for every server object
            # any later test builds.  There was no way to unregister until
            # `clear_on_stop` existed, so this went unnoticed.
            "_base_server._on_stop_hooks": tuple(_base_server._on_stop_hooks),
            "_process_state.server": _process_state.server,
            "_process_state.server_phoenix": _process_state.server_phoenix,
            "current_thread().name": thread.name,
            "current_thread().rpc_model_method": getattr(
                thread, "rpc_model_method", missing
            ),
            "current_thread().start_time": getattr(thread, "start_time", missing),
            "current_thread().type": getattr(thread, "type", missing),
        }

    before = snapshot()

    yield

    after = snapshot()
    problems = []
    leaked = {
        k: (before[k], after[k])
        for k in before
        if before[k] is not after[k] and before[k] != after[k]
    }
    if leaked:
        problems.append(
            "left process-global state altered, which changes the meaning of "
            "every test that runs after it:\n"
            + "\n".join(
                f"  {name}: {old!r} -> {new!r}" for name, (old, new) in leaked.items()
            )
            + "\nRestore it — usually by adding the name to this test's own patch "
            "list, so `patch` owns the teardown."
        )
    if problems:
        pytest.fail("this test " + "\n\nand ".join(problems), pytrace=False)


def _has_inotify() -> bool:
    from odoo.service import _watcher

    return _watcher.inotify is not None


requires_inotify = pytest.mark.skipif(
    not _has_inotify(), reason="inotify backend not installed"
)


def fake_pg_cursor(*, fetchone=None, fetchone_sequence=None, fetchall=(), execute=None):
    from unittest.mock import MagicMock

    cr = MagicMock()
    if fetchone_sequence is not None:
        cr.fetchone.side_effect = list(fetchone_sequence)
    else:
        cr.fetchone.return_value = fetchone
    cr.fetchall.return_value = fetchall
    if execute is not None:
        cr.execute.side_effect = execute
    cr.__enter__ = MagicMock(return_value=cr)
    cr.__exit__ = MagicMock(return_value=False)
    return cr


def fake_pg_connection(cursor=None, **cursor_kwargs):
    from unittest.mock import MagicMock

    cr = cursor if cursor is not None else fake_pg_cursor(**cursor_kwargs)
    conn = MagicMock()
    conn.cursor.return_value = cr
    return conn, cr


def retrying_env(*, on_commit=None, closed=False):
    from unittest.mock import MagicMock

    env = MagicMock()
    env.cr._closed = closed
    env.cr.closed = closed
    env.cr.flush = MagicMock()
    env.cr.rollback = MagicMock()
    env.cr.commit_count = 0
    env.cr.commit = MagicMock(
        side_effect=(lambda: on_commit(env)) if on_commit is not None else None
    )
    env.transaction.reset = MagicMock()
    env.registry.reset_changes = MagicMock()
    env.registry.signal_changes = MagicMock()
    env.registry.values.return_value = []
    env._.side_effect = lambda tmpl, *args: tmpl % args if args else tmpl
    return env


def durable_then_raise(exc=None):
    error = exc if exc is not None else RuntimeError("post-commit hook failed")

    def _commit(env):
        env.cr.commit_count += 1
        raise error

    return _commit


def durable_then_close(env):
    env.cr.commit_count += 1
    env.cr.closed = True


_SCANNED_TREES = ("tests/service", "odoo/addons", "addons")

_GATE_MODULES = frozenset({"test_db_patch_targets.py", "test_facade_patch_targets.py"})

_FACADE_NEEDLES = ("odoo.service", "odoo.api", "odoo.fields", "odoo.models")


@functools.cache
def patch_target_sources() -> tuple[tuple[pathlib.Path, str], ...]:
    root = repo_root()
    out = []
    for rel in _SCANNED_TREES:
        tree = root / rel
        if not tree.is_dir():
            continue
        for path in tree.rglob("*.py"):
            if path.name in _GATE_MODULES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(needle in text for needle in _FACADE_NEEDLES):
                out.append((path, text))
    return tuple(out)
