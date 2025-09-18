"""Pytest conftest for model-level tests that need the full Odoo import chain.

Unlike ``odoo/orm/components/tests/conftest.py`` (which stubs the package
hierarchy to test pure components in isolation), this conftest ensures that
the real ``odoo`` package is importable so that model definition classes from
``odoo.addons.*`` can be imported with their correct ``__module__`` attribute.

MetaModel's ``__new__`` asserts that ``__module__`` starts with
``odoo.addons.``, so the import must go through the real package hierarchy.
"""

import sys
from pathlib import Path

import pytest

# Ensure 'core/' is the first entry in sys.path so that 'import odoo'
# resolves to 'core/odoo/' (a namespace package).
_core_dir = str(Path(__file__).resolve().parent.parent)
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)


@pytest.fixture(scope="session")
def base_registry():
    """Build the base-module ModelRegistry once per pytest session.

    ModelRegistry auto-discovers all models from the ``base`` module
    via ``MetaModel._module_to_models__``, so passing any single model
    class pulls in all ~124 sibling models.  Building takes ~100-200ms;
    reusing the same registry across tests is safe because each test
    gets isolation via a fresh ``DictBackend`` (from ``model_test_env``).
    """
    from odoo.orm.testing import ModelRegistry

    from odoo.addons.base.models.res_partner import ResPartner

    return ModelRegistry([ResPartner])
