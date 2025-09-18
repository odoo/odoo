"""Pytest conftest that enables standalone component testing.

Pre-registers minimal package stubs in ``sys.modules`` so that
``from odoo.orm.components.X import Y`` works without triggering
the full Odoo import chain (``orm/__init__.py`` → ``import odoo.init``
→ circular import through werkzeug/http/service/api).

**Why stubs?**

The component test files use absolute imports like::

    from odoo.orm.components.cache import FieldCache

Python's standard import system resolves this by walking up the package
chain: ``odoo`` → ``odoo.orm`` → ``odoo.orm.components`` → ``.cache``.
Each step executes the package's ``__init__.py``.  The problem is
``odoo/orm/__init__.py`` does ``import odoo.init``, which pulls in
the entire Odoo framework (werkzeug, HTTP stack, etc.) and causes
circular imports.

By pre-registering stubs with correct ``__path__`` attributes, Python
skips the real ``__init__.py`` files and goes straight to the leaf
modules (``cache.py``, ``compute.py``, etc.) which have zero Odoo
imports.

This conftest lives in ``tests/`` (not ``components/``) because a
conftest at the ``components/`` level would itself be imported as
part of the ``odoo.orm.components`` package.
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
#   tests/conftest.py → tests/ → components/ → orm/ → odoo/
_tests_dir = Path(__file__).resolve().parent
_components_dir = _tests_dir.parent
_orm_dir = _components_dir.parent
_odoo_dir = _orm_dir.parent

# Register stubs for the package chain.  Order matters: parent before child.
_stub_package("odoo", str(_odoo_dir))
_stub_package("odoo.orm", str(_orm_dir))
_stub_package("odoo.orm.components", str(_components_dir))
