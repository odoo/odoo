"""Database-free tests for ``ir.ui.menu`` compute methods.

Covers ``_get_full_name()`` which builds hierarchical menu paths
by recursively walking ``parent_id`` with a depth limit.

Run with::

    python -m pytest core/tests/models/test_ir_ui_menu.py -v
"""


# ── _get_full_name / _compute_complete_name ──────────────────────


class TestMenuFullName:
    """``_get_full_name()``: recursive path with depth cutoff."""

    def test_root_menu(self, env):
        """Root menu with no parent → just its name."""
        menu = env["ir.ui.menu"].create({"name": "Settings"})
        assert menu._get_full_name() == "Settings"

    def test_two_level(self, env):
        """Child menu → 'Parent/Child'."""
        parent = env["ir.ui.menu"].create({"name": "Settings"})
        child = env["ir.ui.menu"].create({
            "name": "Users",
            "parent_id": parent.id,
        })
        assert child._get_full_name() == "Settings/Users"

    def test_three_level(self, env):
        """Three-level path: 'Root/Mid/Leaf'."""
        root = env["ir.ui.menu"].create({"name": "Settings"})
        mid = env["ir.ui.menu"].create({
            "name": "Technical",
            "parent_id": root.id,
        })
        leaf = env["ir.ui.menu"].create({
            "name": "Sequences",
            "parent_id": mid.id,
        })
        assert leaf._get_full_name() == "Settings/Technical/Sequences"

    def test_depth_limit(self, env):
        """Exceeding depth limit truncates with '...'."""
        # _get_full_name(level=6) stops at level=0 with "..."
        # Build a chain of 8 menus to exceed the limit
        menus = []
        parent = None
        for i in range(8):
            menu = env["ir.ui.menu"].create({
                "name": f"L{i}",
                "parent_id": parent.id if parent else False,
            })
            menus.append(menu)
            parent = menu

        result = menus[-1]._get_full_name()
        assert result.startswith("...")

    def test_compute_complete_name(self, env):
        """``_compute_complete_name`` delegates to ``_get_full_name``."""
        parent = env["ir.ui.menu"].create({"name": "App"})
        child = env["ir.ui.menu"].create({
            "name": "Sub",
            "parent_id": parent.id,
        })
        child._compute_complete_name()
        assert child.complete_name == "App/Sub"

    def test_empty_name(self, env):
        """Menu with False name uses empty string in path."""
        parent = env["ir.ui.menu"].create({"name": "App"})
        child = env["ir.ui.menu"].create({
            "name": False,
            "parent_id": parent.id,
        })
        result = child._get_full_name()
        assert result == "App/"
