"""Database-free tests for ``ir.sequence`` model methods.

Tests ``get_next_char()`` and ``_get_prefix_suffix()`` with date
interpolation.  Uses ``no_gap`` implementation (no PostgreSQL
sequence objects needed).

Note: ``_get_prefix_suffix()`` reads ``self.env.tz`` for date
formatting.  The ``seq_env`` fixture injects ``tz='UTC'`` into the
context so timezone-dependent date lookups resolve without accessing
``res.users``.

Run with::

    python -m pytest core/tests/models/test_ir_sequence.py -v
"""

from datetime import datetime

import pytest

from odoo.orm.testing import model_test_env

# ── Sequence-specific fixtures ───────────────────────────────────


@pytest.fixture
def seq_env(base_registry):
    """Environment with ``tz`` context set for ``ir.sequence`` methods."""
    with model_test_env(registry=base_registry) as test_env:
        yield test_env(context={"tz": "UTC"})


@pytest.fixture
def make_seq(seq_env):
    """Factory: create ``ir.sequence`` with defaults + tz context."""

    def _make(name="Test", prefix="", suffix="", padding=0, **kwargs):
        defaults = {
            "name": name,
            "prefix": prefix,
            "suffix": suffix,
            "padding": padding,
            "implementation": "no_gap",
            "number_increment": 1,
            "number_next": 1,
            "active": True,
            "company_id": False,
            "code": False,
            "use_date_range": False,
        }
        defaults.update(kwargs)
        return seq_env["ir.sequence"].create(defaults)

    return _make


# ── get_next_char() ──────────────────────────────────────────────


class TestGetNextChar:
    """``ir.sequence.get_next_char()`` — number formatting with padding."""

    def test_prefix_suffix_padding(self, make_seq):
        seq = make_seq(prefix="INV/", suffix="/END", padding=5)
        assert seq.get_next_char(42) == "INV/00042/END"

    def test_no_prefix_suffix(self, make_seq):
        seq = make_seq(padding=4)
        assert seq.get_next_char(1) == "0001"
        assert seq.get_next_char(9999) == "9999"

    def test_overflow_padding(self, make_seq):
        """Number exceeding padding width is not truncated."""
        seq = make_seq(padding=4)
        assert seq.get_next_char(10000) == "10000"

    def test_zero_padding(self, make_seq):
        seq = make_seq(prefix="X", padding=0)
        assert seq.get_next_char(7) == "X7"

    def test_large_number(self, make_seq):
        seq = make_seq(prefix="SO", padding=8)
        assert seq.get_next_char(123456) == "SO00123456"

    def test_year_interpolation(self, make_seq):
        """%(year)s in prefix is interpolated at runtime."""
        seq = make_seq(prefix="INV/%(year)s/", padding=5)
        result = seq.get_next_char(1)
        year = datetime.now().strftime("%Y")
        assert result == f"INV/{year}/00001"


# ── _get_prefix_suffix() ────────────────────────────────────────


class TestPrefixSuffix:
    """``ir.sequence._get_prefix_suffix()`` — date interpolation."""

    def test_static_values(self, make_seq):
        seq = make_seq(prefix="A-", suffix="-Z")
        prefix, suffix = seq._get_prefix_suffix()
        assert prefix == "A-"
        assert suffix == "-Z"

    def test_year_month_day(self, make_seq):
        """Date placeholders resolve to current date."""
        seq = make_seq(prefix="%(year)s/%(month)s/", suffix="-%(day)s")
        prefix, suffix = seq._get_prefix_suffix()
        now = datetime.now()
        assert prefix == f"{now:%Y}/{now:%m}/"
        assert suffix == f"-{now:%d}"

    def test_iso_week(self, make_seq):
        """ISO week and year placeholders."""
        seq = make_seq(prefix="W%(isoweek)s/%(isoyear)s/")
        prefix, _suffix = seq._get_prefix_suffix()
        now = datetime.now()
        assert prefix == f"W{now:%V}/{now:%G}/"

    def test_false_prefix_suffix(self, make_seq):
        """False/empty prefix and suffix produce empty strings."""
        seq = make_seq(prefix=False, suffix=False, padding=3)
        assert seq.get_next_char(1) == "001"

    def test_short_year(self, make_seq):
        """%(y)s gives 2-digit year."""
        seq = make_seq(prefix="%(y)s-")
        prefix, _suffix = seq._get_prefix_suffix()
        now = datetime.now()
        assert prefix == f"{now:%y}-"

    def test_time_components(self, make_seq):
        """Hour/minute/second placeholders."""
        seq = make_seq(suffix="-%(h24)s%(min)s")
        _prefix, suffix = seq._get_prefix_suffix()
        now = datetime.now()
        assert suffix == f"-{now:%H}{now:%M}"
