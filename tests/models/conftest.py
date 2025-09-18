"""Fixtures for model-specific pytest tests.

Provides an ``env`` fixture that creates a fresh :func:`model_test_env`
for each test function, backed by the session-scoped ``base_registry``
defined in ``core/tests/conftest.py``.

All model test files in this directory should use the ``env`` fixture
instead of manually calling ``model_test_env()``.  Each test gets a
fully isolated :class:`DictBackend` — no cross-test pollution.

Usage::

    def test_partner_display_name(env):
        partner = env["res.partner"].create({"name": "Alice"})
        partner._compute_display_name()
        assert partner.display_name == "Alice"
"""

import pytest

from odoo.orm.testing import model_test_env

# ---------------------------------------------------------------------------
# Core fixture: fresh in-memory Environment per test
# ---------------------------------------------------------------------------


@pytest.fixture
def env(base_registry):
    """Fresh in-memory Environment per test, sharing the session registry.

    Yields an :class:`~odoo.orm.runtime.environment.Environment` backed by
    a fresh :class:`~odoo.orm.components.storage.DictBackend`.  Pre-seeded
    with ``res_partner(1)``, ``res_company(1)``, ``res_users(1)`` so that
    ``env.user`` and ``env.company`` resolve without errors.
    """
    with model_test_env(registry=base_registry) as test_env:
        yield test_env


# ---------------------------------------------------------------------------
# Factory fixtures — sensible defaults, override with **kwargs
# ---------------------------------------------------------------------------


@pytest.fixture
def make_partner(env):
    """Create a ``res.partner`` (person) with sensible defaults."""

    def _make(name="Test Partner", **kwargs):
        defaults = {"name": name, "is_company": False, "type": "contact"}
        defaults.update(kwargs)
        return env["res.partner"].create(defaults)

    return _make


@pytest.fixture
def make_company_partner(env):
    """Create a company-type ``res.partner``."""

    def _make(name="Test Corp", **kwargs):
        defaults = {"name": name, "is_company": True, "type": "contact"}
        defaults.update(kwargs)
        return env["res.partner"].create(defaults)

    return _make


@pytest.fixture
def make_currency(env):
    """Create a ``res.currency`` with sensible defaults."""

    def _make(name="TST", symbol="T", rounding=0.01, **kwargs):
        defaults = {
            "name": name,
            "symbol": symbol,
            "rounding": rounding,
            "decimal_places": 2,
            "active": True,
            "position": "before",
        }
        defaults.update(kwargs)
        return env["res.currency"].create(defaults)

    return _make


@pytest.fixture
def make_country(env):
    """Create a ``res.country`` with sensible defaults."""

    def _make(name="Testland", code="XX", **kwargs):
        defaults = {"name": name, "code": code}
        defaults.update(kwargs)
        return env["res.country"].create(defaults)

    return _make
