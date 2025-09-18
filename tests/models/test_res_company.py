"""Database-free tests for ``res.company`` model methods.

Covers ``_compute_parent_ids()`` (parent_path string parsing) and
``_compute_empty_company_details()`` (HTML stripping to detect empty
company details).

Run with::

    python -m pytest core/tests/models/test_res_company.py -v
"""

from odoo.tools import html2plaintext

# ── _compute_parent_ids ──────────────────────────────────────────


class TestParentIds:
    """``_compute_parent_ids``: parse ``parent_path`` into ancestor set.

    Uses direct DictBackend seeding because ``res.company.create()``
    updates ``env.user.company_ids`` (Many2many), which triggers a
    constraint that DictBackend cannot satisfy.
    """

    @staticmethod
    def _seed_company(env, record_id, name, parent_path, parent_id=False):
        """Insert a company row directly into DictBackend storage."""
        storage = env.cr.storage
        tbl = storage._tables.setdefault("res_company", {})
        tbl[record_id] = {
            "id": record_id, "name": name, "parent_path": parent_path,
            "parent_id": parent_id, "active": True, "partner_id": 1,
        }
        storage._sequences["res_company"] = max(
            storage._sequences.get("res_company", 0), record_id
        )

    def test_root_company(self, env):
        """Seeded root company (id=1) has parent_path '1/'."""
        company = env["res.company"].browse(1)
        assert company.parent_path == "1/"
        company._compute_parent_ids()
        assert company.root_id == company
        assert list(company.parent_ids.ids) == [1]

    def test_child_company(self, env):
        """Child company's parent_ids include both parent and self."""
        self._seed_company(env, 2, "Child Corp", "1/2/", parent_id=1)
        child = env["res.company"].browse(2)
        child._compute_parent_ids()
        assert 1 in child.parent_ids.ids
        assert 2 in child.parent_ids.ids
        assert child.root_id.id == 1

    def test_deep_hierarchy(self, env):
        """Three-level hierarchy: root → parent → grandchild."""
        self._seed_company(env, 2, "Parent Corp", "1/2/", parent_id=1)
        self._seed_company(env, 3, "Grandchild Corp", "1/2/3/", parent_id=2)
        child = env["res.company"].browse(3)
        child._compute_parent_ids()
        assert child.root_id.id == 1
        assert len(child.parent_ids) == 3

    def test_no_parent_path(self, env):
        """Company with no parent_path falls back to self."""
        self._seed_company(env, 2, "Orphan Corp", False)
        company = env["res.company"].browse(2)
        company._compute_parent_ids()
        assert company.root_id == company
        assert company.parent_ids == company


# ── _compute_empty_company_details ───────────────────────────────


class TestEmptyCompanyDetails:
    """``_compute_empty_company_details``: HTML → plaintext emptiness check."""

    def test_empty_html(self, env):
        """Residual HTML markup (<p><br></p>) is detected as empty."""
        company = env["res.company"].browse(1)
        company.write({"company_details": "<p><br></p>"})
        company._compute_empty_company_details()
        assert company.is_company_details_empty is True

    def test_meaningful_content(self, env):
        """HTML with real text content is not empty."""
        company = env["res.company"].browse(1)
        company.write({"company_details": "<p>123 Main St</p>"})
        company._compute_empty_company_details()
        assert company.is_company_details_empty is False

    def test_false_details(self, env):
        """False/unset company_details is treated as empty."""
        company = env["res.company"].browse(1)
        company.write({"company_details": False})
        company._compute_empty_company_details()
        assert company.is_company_details_empty is True

    def test_whitespace_only(self, env):
        """HTML with only whitespace is detected as empty."""
        company = env["res.company"].browse(1)
        company.write({"company_details": "<p>   </p>"})
        company._compute_empty_company_details()
        assert company.is_company_details_empty is True

    def test_html2plaintext_consistency(self):
        """Verify html2plaintext strips residual markup correctly (pure)."""
        assert html2plaintext("<p><br></p>").strip() == ""
        assert html2plaintext("<p>Hello</p>").strip() == "Hello"
        assert html2plaintext("").strip() == ""
