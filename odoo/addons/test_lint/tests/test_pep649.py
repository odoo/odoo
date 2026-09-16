from odoo.tests.common import BaseCase, no_retry

from ._checker_pep649 import scan_module

CLEAN_MODULES = (
    "odoo.cli.command",
    "odoo.cli.module",
    "odoo.cli.obfuscate",
    "odoo.cli.populate",
    "odoo.cli.scaffold",
    "odoo.db.cursor",
    "odoo.db.pool",
    "odoo.db.utils",
    "odoo.http._cookies",
    "odoo.http._cors",
    "odoo.http._csrf",
    "odoo.http._dbfilter",
    "odoo.http._error_serialization",
    "odoo.http._protocols",
    "odoo.http._response",
    "odoo.http._serve",
    "odoo.http._session_lifecycle",
    "odoo.http.application",
    "odoo.http.controller",
    "odoo.http.dispatcher",
    "odoo.http._rpc",
    "odoo.http.request_class",
    "odoo.http.routing",
    "odoo.http._session_store",
    "odoo.http.session",
    "odoo.service.db",
    "odoo.service.server",
    "odoo.tools.cloc",
    "odoo.tools.config",
    "odoo.tools.files",
    "odoo.tools.locale_utils",
)


@no_retry
class TestPEP649Annotations(BaseCase):
    def test_clean_modules_introspect(self):
        for modname in CLEAN_MODULES:
            with self.subTest(module=modname):
                fails = scan_module(modname)
                self.assertFalse(
                    fails,
                    msg=(
                        f"{modname} has annotation-resolution failures.  "
                        f"Move the offending import out of `if TYPE_CHECKING:`, "
                        f"or — if a runtime import would cycle — keep the "
                        f"TYPE_CHECKING import and add a ``typing.Any`` "
                        f"fallback in an ``else:`` branch.  Failures:\n  "
                        + "\n  ".join(fails)
                    ),
                )
