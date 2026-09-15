import logging
import typing
from contextlib import suppress

from odoo.libs.debug_log import DebugLog
from odoo.modules._protocols import SqlReader
from odoo.modules.module import Manifest
from odoo.tools.misc import file_open

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def get_installed_module_names(cursor: SqlReader) -> list[str]:
    cursor.execute("""
        SELECT name
          FROM ir_module_module
         WHERE state IN ('installed', 'to upgrade', 'to remove');
    """)
    names = [result[0] for result in cursor.fetchall()]
    _debug.perf.count("modules.neutralize.installed", modules=len(names))
    return names


def iter_neutralization_queries(modules: Iterable[str]) -> Iterator[tuple[str, str]]:
    for module in modules:
        if Manifest.for_addon(module, display_warning=False) is None:
            _debug.logic("modules.neutralize.module_missing", module=module)
            _logger.warning(
                "Module %r is installed but not found on the addons path; its "
                "neutralization (if any) is SKIPPED. The database may not be "
                "fully neutralized — configure all addons paths and re-run.",
                module,
            )
            continue
        filename = f"{module}/data/neutralize.sql"
        with suppress(FileNotFoundError):
            with file_open(filename) as file:
                content = file.read().strip()
                _debug.logic(
                    "modules.neutralize.script",
                    module=module,
                    empty=not content,
                    size=len(content),
                )
                if content:
                    yield module, content


def get_neutralization_queries(modules: Iterable[str]) -> Iterator[str]:
    for _module, query in iter_neutralization_queries(modules):
        yield query


def neutralize_database(cursor: SqlReader) -> None:
    with _debug.perf("modules.neutralize", cr=cursor) as span:
        executed = 0  # debuglog
        for module, query in iter_neutralization_queries(
            get_installed_module_names(cursor)
        ):
            _debug.pipeline("modules.neutralize.module", module=module)
            try:
                with _debug.perf("modules.neutralize.query", cr=cursor, module=module):
                    cursor.execute(query)
            except Exception as exc:
                exc.add_note(
                    f"while neutralizing {module} ({module}/data/neutralize.sql)"
                )
                raise
            executed += 1  # debuglog
        span.set(executed=executed)
    _logger.info("Neutralization finished")
