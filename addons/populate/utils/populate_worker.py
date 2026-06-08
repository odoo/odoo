"""Bootstrap helpers for populate workers started with multiprocessing.

This module is intentionally imported as top-level ``populate_worker`` by the
parent process. Spawned workers must import their initializer before it runs, so
the initializer cannot live behind ``odoo.addons.populate``: that namespace may
only be available after Odoo's addons' path is initialized.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import signal

_worker_logger = logging.getLogger('odoo.addons.populate.worker')


def initialize(dbname: str, options: dict):
    """Initialize a spawned populate worker before it receives jobs.

    The parent passes this function directly to ``ProcessPoolExecutor``. It must
    therefore be importable in a fresh Python process without relying on
    ``odoo.addons.populate``. Once imported, it restores the parent Odoo config,
    initializes the addons' path, and loads the registry so regular populate job
    execution can safely import and use addon code.
    """
    from odoo.modules import initialize_sys_path  # noqa: PLC0415
    from odoo.modules.registry import Registry  # noqa: PLC0415
    from odoo.netsvc import init_logger  # noqa: PLC0415
    from odoo.tools import config, mute_logger  # noqa: PLC0415

    # Only 'spawn' is supported. With 'fork', the child inherits the
    # parent's PostgreSQL connection pools (shared socket fds), and
    # psycopg2 offers no way to cleanly detach without sending a
    # termination message that would corrupt the parent's connections.
    assert mp.get_start_method() == 'spawn'

    # SIGINT is handled by the parent process; subprocesses should exit immediately.
    # Use os._exit() instead of sys.exit() to avoid raising SystemExit,
    # which ProcessPoolExecutor's internals would catch, allowing the worker
    # to continue processing queued tasks. We want to prevent this since
    # abruptly terminated jobs can be resumed later anyway.
    signal.signal(signal.SIGINT, lambda *_: os._exit(0))

    # Initialize addons' path to ensure all installed modules
    # are discovered when loading the Registry.
    config.options.update(options)
    initialize_sys_path()
    init_logger()

    with mute_logger('odoo.registry', 'odoo.modules.loading'):
        Registry(dbname)

    _worker_logger.info("Worker (%s) alive", os.getpid())
