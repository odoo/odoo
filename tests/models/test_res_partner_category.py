"""Database-free tests for ``res.partner.category`` model methods.

Covers ``_compute_display_name()`` which walks the parent_id chain
and joins category names with `` / ``.

Run with::

    python -m pytest core/tests/models/test_res_partner_category.py -v
"""


# ── _compute_display_name ────────────────────────────────────────


class TestCategoryDisplayName:
    """``_compute_display_name``: hierarchical name via parent_id chain."""

    def test_single_category(self, env):
        """Category with no parent → just its name."""
        cat = env["res.partner.category"].create({"name": "Electronics"})
        cat._compute_display_name()
        assert cat.display_name == "Electronics"

    def test_two_level_hierarchy(self, env):
        """Child category shows 'Parent / Child'."""
        parent = env["res.partner.category"].create({"name": "Products"})
        child = env["res.partner.category"].create({
            "name": "Electronics",
            "parent_id": parent.id,
        })
        child._compute_display_name()
        assert child.display_name == "Products / Electronics"

    def test_three_level_hierarchy(self, env):
        """Deep hierarchy: 'Root / Mid / Leaf'."""
        root = env["res.partner.category"].create({"name": "Root"})
        mid = env["res.partner.category"].create({
            "name": "Mid",
            "parent_id": root.id,
        })
        leaf = env["res.partner.category"].create({
            "name": "Leaf",
            "parent_id": mid.id,
        })
        leaf._compute_display_name()
        assert leaf.display_name == "Root / Mid / Leaf"

    def test_parent_display_name_unchanged(self, env):
        """Parent's display_name is just its own name."""
        parent = env["res.partner.category"].create({"name": "Services"})
        env["res.partner.category"].create({
            "name": "Consulting",
            "parent_id": parent.id,
        })
        parent._compute_display_name()
        assert parent.display_name == "Services"

    def test_empty_name(self, env):
        """Category with no name uses empty string in path."""
        parent = env["res.partner.category"].create({"name": "Parent"})
        child = env["res.partner.category"].create({
            "name": False,
            "parent_id": parent.id,
        })
        child._compute_display_name()
        assert child.display_name == "Parent / "
