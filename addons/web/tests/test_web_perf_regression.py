"""Query count regression tests for web module operations.

Each test pins the expected number of SQL queries for an optimized code path.
If a future change introduces an N+1 regression, the test will fail with a
higher-than-expected query count.

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags '/web:TestWebPerfRegression' -u web \
        --stop-after-init --workers=0
    grep "tests when loading" ./odoo.log
"""

from odoo.tests.common import TransactionCase, tagged, warmup


@tagged("post_install", "-at_install", "web_perf")
class TestWebPerfRegression(TransactionCase):
    """Pin query counts for web module CRUD operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Dedicated company + user for stable query counts
        cls.company = cls.env["res.company"].create({"name": "PerfTest Company"})
        cls.user = cls.env["res.users"].create(
            {
                "login": "web_perf",
                "name": "Web Perf User",
                "email": "web_perf@test.example.com",
                "tz": "UTC",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("base.group_partner_manager").id,
                        ],
                    )
                ],
            }
        )

        # Categories for many2many testing
        cls.categories = cls.env["res.partner.category"].create(
            [{"name": f"PerfCat_{i}"} for i in range(5)]
        )

        cls.country_be = cls.env.ref("base.be")

        # 100 partners with many2one + many2many relationships
        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"PerfPartner_{i:03d}",
                    "email": f"perf{i}@test.example.com",
                    "country_id": cls.country_be.id,
                    "category_id": [(6, 0, cls.categories[:3].ids)],
                    "type": "contact",
                    "company_type": "person",
                }
                for i in range(100)
            ]
        )

        # Parent-child hierarchy for x2many tests
        cls.parent_partner = cls.env["res.partner"].create(
            {
                "name": "PerfParent",
                "country_id": cls.country_be.id,
            }
        )
        cls.child_partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"PerfChild_{i}",
                    "parent_id": cls.parent_partner.id,
                    "country_id": cls.country_be.id,
                }
                for i in range(10)
            ]
        )

        # Menu items for web_resequence test (ir.ui.menu has sequence field)
        cls.test_menus = cls.env["ir.ui.menu"].create(
            [{"name": f"PerfMenu_{i}", "sequence": i * 10} for i in range(10)]
        )

    def setUp(self):
        super().setUp()
        self.env = self.env(user=self.user)

    # ------------------------------------------------------------------
    # web_read: flat specification
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_basic(self):
        """web_read: 100 records, flat spec (name + email + type)."""
        partners = self.partners.with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            # 1 read (fields) + access rules
            partners.web_read({"name": {}, "email": {}, "type": {}})

    # ------------------------------------------------------------------
    # web_read: many2one with sub-fields
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_many2one_subfields(self):
        """web_read: 100 records with many2one (country_id) sub-spec."""
        partners = self.partners.with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            # 1 read (partner fields) + 1 read (country co-records)
            # + 1 sudo read (display_name) + access rules
            partners.web_read(
                {
                    "name": {},
                    "country_id": {
                        "fields": {
                            "display_name": {},
                            "code": {},
                        },
                    },
                }
            )

    # ------------------------------------------------------------------
    # web_read: one2many with sub-fields
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_x2many_subfields(self):
        """web_read: parent + 10 children with one2many sub-spec."""
        parent = self.parent_partner.with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # 1 flush + 1 read (parent) + 1 read (child co-records)
            # + access rules
            parent.web_read(
                {
                    "name": {},
                    "child_ids": {
                        "fields": {
                            "name": {},
                            "email": {},
                            "country_id": {"fields": {"display_name": {}}},
                        },
                    },
                }
            )

    # ------------------------------------------------------------------
    # web_read: many2many with sub-fields
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_many2many_subfields(self):
        """web_read: 100 records with many2many (category_id) sub-spec."""
        partners = self.partners.with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            # 1 read (partner fields incl. m2m rel table)
            # + 1 read (category co-records) + access rules
            partners.web_read(
                {
                    "name": {},
                    "category_id": {
                        "fields": {
                            "display_name": {},
                            "color": {},
                        },
                    },
                }
            )

    # ------------------------------------------------------------------
    # web_search_read
    # ------------------------------------------------------------------

    @warmup
    def test_web_search_read(self):
        """web_search_read: domain match ~100, limit=80 (triggers count)."""
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            # 1 search + 1 fetch + 1 read + 1 count
            Partners.web_search_read(
                domain=[("name", "like", "PerfPartner")],
                specification={"name": {}, "email": {}, "country_id": {}},
                limit=80,
            )

    # ------------------------------------------------------------------
    # web_read_group: single level, no unfold
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_group_single(self):
        """web_read_group: group by country_id, no auto_unfold."""
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(3):
            # 1 flush + 1 _read_group + 1 access rules
            Partners.web_read_group(
                domain=[("name", "like", "PerfPartner")],
                groupby=["country_id"],
                aggregates=["__count"],
            )

    # ------------------------------------------------------------------
    # web_read_group: with auto_unfold
    # ------------------------------------------------------------------

    @warmup
    def test_web_read_group_auto_unfold(self):
        """web_read_group: group by country_id, auto_unfold=True."""
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # _read_group + per-group search + union web_read + count
            Partners.web_read_group(
                domain=[("name", "like", "PerfPartner")],
                groupby=["country_id"],
                aggregates=["__count"],
                auto_unfold=True,
                unfold_read_specification={"name": {}, "email": {}},
            )

    # ------------------------------------------------------------------
    # search_panel_select_range: many2one with counters
    # ------------------------------------------------------------------

    @warmup
    def test_search_panel_m2o(self):
        """search_panel_select_range: many2one (country_id) with counters."""
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(3):
            # 1 _read_group (image) + 1 _read_group (count) + access rules
            Partners.search_panel_select_range(
                "country_id",
                search_domain=[("name", "like", "PerfPartner")],
                enable_counters=True,
            )

    # ------------------------------------------------------------------
    # search_panel_select_multi_range: many2many with counters (N+1)
    # ------------------------------------------------------------------

    @warmup
    def test_search_panel_m2m_counters(self):
        """search_panel_select_multi_range: m2m (category_id) with counters.

        Batched: single _search_panel_domain_image() replaces N search_count().
        """
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # 1 domain_image + 1 search_read + 1 count_image + access rules
            Partners.search_panel_select_multi_range(
                "category_id",
                search_domain=[("name", "like", "PerfPartner")],
                enable_counters=True,
            )

    # ------------------------------------------------------------------
    # web_name_search: display_name-only fast path
    # ------------------------------------------------------------------

    @warmup
    def test_web_name_search(self):
        """web_name_search: display_name-only fast path."""
        Partners = self.env["res.partner"].with_user(self.user)
        self.env.invalidate_all()
        with self.assertQueryCount(3):
            # 1 name_search + 1 browse/read + access rules
            Partners.web_name_search(
                "PerfPartner",
                specification={"display_name": {}},
                limit=100,
            )

    # ------------------------------------------------------------------
    # web_save_multi (N+1: per-record write)
    # ------------------------------------------------------------------

    @warmup
    def test_web_save_multi(self):
        """web_save_multi: write 10 records with unique vals (per-record write).

        Records with identical vals are batched into a single write().
        With unique vals (as here), falls back to per-record writes.
        """
        partners = self.partners[:10].with_user(self.user)
        vals_list = [{"name": f"Updated_{i}"} for i in range(10)]
        self.env.invalidate_all()
        with self.assertQueryCount(60):
            # 10 unique vals → 10 individual writes + final web_read
            # Each write triggers modified() cascade for complete_name
            # (3 queries per record: parent_id, commercial_partner_id, company)
            partners.web_save_multi(vals_list, specification={"name": {}})

    # ------------------------------------------------------------------
    # web_resequence (N+1: per-record write)
    # ------------------------------------------------------------------

    @warmup
    def test_web_resequence(self):
        """web_resequence: resequence 10 menu items (batched).

        Batched: access checks + mark_dirty loop + single modified().
        """
        menus = self.test_menus.with_user(self.env.ref("base.user_admin"))
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            # 1 flush (deferred write) + 1 web_read
            menus.web_resequence(
                specification={"name": {}, "sequence": {}},
                field_name="sequence",
            )
