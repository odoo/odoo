"""Database-free tests for ``report.paperformat`` model methods.

Covers ``_compute_print_page_size()`` which resolves paper dimensions
from format key or custom values, with Portrait/Landscape orientation
swapping.

Run with::

    python -m pytest core/tests/models/test_report_paperformat.py -v
"""

from odoo.addons.base.models.report_paperformat import PAPER_SIZES

# ── _compute_print_page_size ─────────────────────────────────────


class TestPrintPageSize:
    """``_compute_print_page_size``: paper dimensions with orientation."""

    def _make_paperformat(self, env, fmt="A4", orientation="Portrait", **kwargs):
        """Create a paper format record with sensible defaults."""
        defaults = {
            "name": "Test Format",
            "format": fmt,
            "orientation": orientation,
            "page_width": 0,
            "page_height": 0,
            "margin_top": 0,
            "margin_bottom": 0,
            "margin_left": 0,
            "margin_right": 0,
            "header_spacing": 0,
            "header_line": False,
            "dpi": 90,
        }
        defaults.update(kwargs)
        return env["report.paperformat"].create(defaults)

    def test_a4_portrait(self, env):
        """A4 Portrait: 210 x 297 mm."""
        pf = self._make_paperformat(env, "A4", "Portrait")
        pf._compute_print_page_size()
        assert pf.print_page_width == 210.0
        assert pf.print_page_height == 297.0

    def test_a4_landscape(self, env):
        """A4 Landscape: swapped to 297 x 210 mm."""
        pf = self._make_paperformat(env, "A4", "Landscape")
        pf._compute_print_page_size()
        assert pf.print_page_width == 297.0
        assert pf.print_page_height == 210.0

    def test_letter_portrait(self, env):
        """US Letter Portrait: 215.9 x 279.4 mm."""
        pf = self._make_paperformat(env, "Letter", "Portrait")
        pf._compute_print_page_size()
        assert pf.print_page_width == 215.9
        assert pf.print_page_height == 279.4

    def test_custom_dimensions(self, env):
        """Custom format uses explicit page_width/page_height."""
        pf = self._make_paperformat(
            env, "custom", "Portrait",
            page_width=100, page_height=200,
        )
        pf._compute_print_page_size()
        assert pf.print_page_width == 100
        assert pf.print_page_height == 200

    def test_custom_landscape(self, env):
        """Custom Landscape: width and height are swapped."""
        pf = self._make_paperformat(
            env, "custom", "Landscape",
            page_width=100, page_height=200,
        )
        pf._compute_print_page_size()
        assert pf.print_page_width == 200
        assert pf.print_page_height == 100

    def test_false_format(self, env):
        """No format selected → 0x0 dimensions."""
        pf = self._make_paperformat(env, False, "Portrait")
        pf._compute_print_page_size()
        assert pf.print_page_width == 0.0
        assert pf.print_page_height == 0.0

    def test_a3_dimensions(self, env):
        """A3 Portrait: 297 x 420 mm."""
        pf = self._make_paperformat(env, "A3", "Portrait")
        pf._compute_print_page_size()
        assert pf.print_page_width == 297.0
        assert pf.print_page_height == 420.0


# ── PAPER_SIZES constant ────────────────────────────────────────


class TestPaperSizesData:
    """Verify PAPER_SIZES constant integrity."""

    def test_all_have_required_keys(self):
        """Every non-custom entry has key, description, width, height."""
        for ps in PAPER_SIZES:
            assert "key" in ps
            assert "description" in ps
            if ps["key"] != "custom":
                assert "width" in ps, f"Missing width for {ps['key']}"
                assert "height" in ps, f"Missing height for {ps['key']}"

    def test_a4_in_list(self):
        """A4 is the most common format — must be present."""
        a4 = next(ps for ps in PAPER_SIZES if ps["key"] == "A4")
        assert a4["width"] == 210.0
        assert a4["height"] == 297.0

    def test_no_duplicate_keys(self):
        """Each paper size key is unique."""
        keys = [ps["key"] for ps in PAPER_SIZES]
        assert len(keys) == len(set(keys))
