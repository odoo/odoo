"""Pytest conftest that enables standalone locale testing.

Pre-registers minimal package stubs so that ``from odoo.libs.locale.X``
works without triggering the full Odoo import chain.
"""

import sys
import types
from pathlib import Path


def _stub_package(name: str, path: str) -> types.ModuleType:
    """Register a minimal package stub in sys.modules if not present."""
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = [path]
    mod.__package__ = name
    mod.__file__ = f"{path}/__init__.py"
    sys.modules[name] = mod
    return mod


# Build paths relative to this file:
#   tests/conftest.py → tests/ → locale/ → libs/ → odoo/
_tests_dir = Path(__file__).resolve().parent
_locale_dir = _tests_dir.parent
_libs_dir = _locale_dir.parent
_odoo_dir = _libs_dir.parent

# Register stubs for the package chain.  Order matters: parent before child.
_stub_package("odoo", str(_odoo_dir))
_stub_package("odoo.libs", str(_libs_dir))
_stub_package("odoo.libs.locale", str(_locale_dir))
