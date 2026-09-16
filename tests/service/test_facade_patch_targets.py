import re

from .conftest import patch_target_sources

FACADES = (
    "odoo.service.db",
    "odoo.service.server",
    "odoo.api",
    "odoo.fields",
    "odoo.models",
)

_TARGET = re.compile(
    r"""patch\(\s*["'](?P<facade>"""
    + "|".join(re.escape(f) for f in FACADES)
    + r""")\.(?P<name>[A-Za-z_]\w*)["']"""
)

FACADE_TARGETS_OK = {
    "odoo.service.db": {
        "check_super": "web/controllers/database.py does `db.check_super(...)`",
        "restore_db": "read off the package by the controller, per call",
        "list_dbs": "http/helpers.py does `odoo.service.db.list_dbs`",
        "dispatch": "read off the package by the RPC entry point",
        "dump_db": "read off the package by the controller, per call",
    },
    "odoo.service.server": {
        "is_ready": "web/controllers/health.py does `service_server.is_ready()`",
    },
    "odoo.api": {
        "Environment": "service/common.py and service/model.py read it per call",
    },
    "odoo.fields": {},
    "odoo.models": {},
}


def _targets():
    for path, text in patch_target_sources():
        for m in _TARGET.finditer(text):
            line = text[: m.start()].count("\n") + 1
            yield path, line, m.group("facade"), m.group("name")


def test_every_facade_patch_is_a_recorded_decision():
    bad = []
    for path, line, facade, name in _targets():
        if name not in FACADE_TARGETS_OK[facade]:
            bad.append(f"{path}:{line} -> {facade}.{name}")
    assert not bad, (
        "patch target(s) aimed at a re-export façade with no recorded reason.\n"
        "  " + "\n  ".join(bad) + "\n\n"
        "The façade only re-exports the name, so whether the patch reaches the "
        "code under test depends on how that code imported it:\n"
        "  * bound at module scope (`from odoo.api import X`) -> the patch is a "
        "SILENT NO-OP and the test drives the real collaborator;\n"
        "  * read per call (`odoo.api.X(...)`, or a function-local import) -> "
        "the patch is correct.\n"
        "Check which, then either patch the module that DEFINES the name, or add "
        "it to FACADE_TARGETS_OK with the caller that justifies it."
    )


def test_the_recorded_reasons_are_not_stale():
    live = {(facade, name) for _, _, facade, name in _targets()}
    stale = [
        f"{facade}.{name}"
        for facade, names in FACADE_TARGETS_OK.items()
        for name in names
        if facade != "odoo.service.db" and (facade, name) not in live
    ]
    assert not stale, (
        "FACADE_TARGETS_OK records a reason for a patch that no longer exists:\n"
        "  " + "\n  ".join(stale) + "\nDrop the entry."
    )


def test_the_two_gates_agree_about_the_db_package():
    from .test_db_patch_targets import PACKAGE_LEVEL_OK

    assert set(FACADE_TARGETS_OK["odoo.service.db"]) == set(PACKAGE_LEVEL_OK), (
        "the odoo.service.db entries here have drifted from "
        "test_db_patch_targets.PACKAGE_LEVEL_OK, which is the authority for that "
        "package"
    )


def test_the_gate_would_catch_a_regression():
    assert _TARGET.search('patch("odoo.api.SUPERUSER_ID")')
    assert _TARGET.search("patch('odoo.service.server.WorkerCron')")
    assert _TARGET.search('patch("odoo.fields.Many2one")')
    assert not _TARGET.search('patch("odoo.orm.runtime.environment.Environment")')
    assert not _TARGET.search('patch("odoo.service._threaded.ThreadedServer")')


def test_the_scan_reaches_the_files_it_claims_to():
    assert len(patch_target_sources()) > 100
    assert list(_targets()), "no façade-aimed patch found anywhere; scan is broken"
