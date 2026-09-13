import logging
import os
import pathlib
import re
import sys
import unittest
from datetime import datetime

import odoo.tools
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread
from odoo.logutils import RUNBOT

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

HOST = "127.0.0.1"


class InfrastructureUnavailable(unittest.SkipTest):
    pass


_TEST_MODULE_PREFIXES = ("odoo.addons.", "odoo.upgrade.")


def addon_relative_path(module_name: str) -> str:
    for prefix in _TEST_MODULE_PREFIXES:
        module_name = module_name.removeprefix(prefix)
    return f"/{module_name.replace('.', '/')}.py"


def env_int(varname: str, default: int) -> int:
    raw = os.environ.get(varname, "")
    return int(raw) if raw.strip() else default


def get_db_name() -> str:
    dbnames = odoo.tools.config["db_name"]
    worker_dbname = getattr(current_worker_thread(), "dbname", None)
    if not dbnames and worker_dbname:
        _debug.logic("test.utils.db_from_worker", db=worker_dbname)
        return worker_dbname
    if not dbnames:
        _debug.logic("test.utils.db_missing")
        sys.exit("No database name found, please provide one with -d/--database")
    if len(dbnames) > 1:
        _debug.logic("test.utils.db_ambiguous", count=len(dbnames))
        sys.exit(
            "-d/--database/db_name has multiple database, please provide a single one"
        )
    return dbnames[0]


def save_test_file(
    test_name: str,
    content: bytes,
    prefix: str,
    extension: str = "png",
    logger: logging.Logger = _logger,
    document_type: str = "Screenshot",
    date_format: str = "%Y%m%d_%H%M%S_%f",
) -> None:
    if not re.fullmatch(r"\w*_?", prefix):
        raise ValueError(f"Invalid prefix: {prefix!r}")
    if not re.fullmatch(r"[a-z]+", extension):
        raise ValueError(f"Invalid extension: {extension!r}")
    if not re.fullmatch(r"\w+", test_name):
        raise ValueError(f"Invalid test_name: {test_name!r}")
    now = datetime.now().strftime(date_format)
    screenshots_dir = (
        pathlib.Path(odoo.tools.config["screenshots"]) / get_db_name() / "screenshots"
    )
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    full_path = screenshots_dir / f"{prefix}{now}_{test_name}.{extension}"
    full_path.write_bytes(content)
    _debug.lifecycle(
        "test.utils.file_saved",
        kind=document_type,
        test=test_name,
        extension=extension,
        size=len(content),
    )
    logger.log(RUNBOT, "%s in: %s", document_type, full_path)
