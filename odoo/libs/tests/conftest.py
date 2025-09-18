"""Pytest conftest that enables standalone libs testing.

Pre-registers minimal package stubs in ``sys.modules`` so that
``from odoo.libs.X import Y`` works without triggering the full
Odoo import chain (``odoo/__init__.py`` → werkzeug/HTTP/service).

The libs modules have zero Odoo imports, but Python's import system
walks up the package chain and would execute ``odoo/__init__.py``.
By stubbing the parent packages, we skip that and go straight to
the leaf modules.
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
#   tests/conftest.py → tests/ → libs/ → odoo/
_tests_dir = Path(__file__).resolve().parent
_libs_dir = _tests_dir.parent
_odoo_dir = _libs_dir.parent

# Register stubs for the package chain.  Order matters: parent before child.
_stub_package("odoo", str(_odoo_dir))
_stub_package("odoo.libs", str(_libs_dir))
