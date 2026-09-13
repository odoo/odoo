import pathlib
import re
import typing

import pytest

from odoo.orm.runtime.backend import InMemoryBackend, StorageBackend

_ORM_DIR = pathlib.Path(__file__).resolve().parent.parent
_MIXINS_DIR = _ORM_DIR / "models" / "mixins"
_DISPATCH_DIRS = (_MIXINS_DIR, _ORM_DIR / "fields", _ORM_DIR / "domain")
# base's models are port callers too (ir.ui.view walks view ancestry, res.users
# reads password columns); they also name their file-storage backends `backend`,
# so only the spelled-out `env.backend.` counts there
_BASE_MODELS_DIR = _ORM_DIR.parent / "addons" / "base" / "models"

_CAPABILITY_MEMBERS = {
    "supports_column_scan",
    "supports_recursive_queries",
}
_ATTRIBUTE_MEMBERS = _CAPABILITY_MEMBERS | {"sequences", "columns"}


def _protocol_methods() -> set[str]:
    return set(typing.get_protocol_members(StorageBackend)) - _ATTRIBUTE_MEMBERS


def test_in_memory_backend_implements_the_whole_protocol():
    missing = [
        m
        for m in typing.get_protocol_members(StorageBackend)
        if not hasattr(InMemoryBackend, m)
    ]
    assert not missing, f"InMemoryBackend does not implement: {missing}"


def test_every_protocol_method_has_a_dispatch_site():
    dispatched: set[str] = set()
    for directory in _DISPATCH_DIRS:
        for path in directory.rglob("*.py"):
            text = path.read_text()
            dispatched.update(re.findall(r"\bbackend\.([a-z_0-9]+)\(", text))
    for path in _BASE_MODELS_DIR.rglob("*.py"):
        text = path.read_text()
        dispatched.update(re.findall(r"\benv\.backend\.([a-z_0-9]+)\(", text))
    methods = _protocol_methods()
    missing_dispatch = methods - dispatched
    unknown_dispatch = dispatched - methods - _ATTRIBUTE_MEMBERS
    assert not missing_dispatch, (
        f"StorageBackend methods with no dispatch site (they would run "
        f"SQL against the in-memory backend): {sorted(missing_dispatch)}"
    )
    assert not unknown_dispatch, (
        f"dispatch to backend methods not on the Protocol: {sorted(unknown_dispatch)}"
    )


def test_every_capability_is_consulted_somewhere():
    text = "".join(
        path.read_text()
        for directory in _DISPATCH_DIRS
        for path in directory.rglob("*.py")
    )
    unread = sorted(m for m in _CAPABILITY_MEMBERS if f"backend.{m}" not in text)
    assert not unread, (
        f"capability flag(s) declared on StorageBackend but consulted nowhere: "
        f"{unread}. Either a site should branch on it, or it should not exist."
    )


def test_both_backends_declare_every_capability():
    from odoo.orm.runtime.backend import PostgresBackend

    for backend in (InMemoryBackend, PostgresBackend):
        missing = sorted(m for m in _ATTRIBUTE_MEMBERS if not hasattr(backend, m))
        assert not missing, f"{backend.__name__} does not declare: {missing}"


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
