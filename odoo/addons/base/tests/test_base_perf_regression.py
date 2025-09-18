"""Query count regression tests for base module N+1 optimizations.

Each test pins the expected number of SQL queries for an optimized code path.
If a future change introduces an N+1 regression, the test will fail with a
higher-than-expected query count.

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags '/base:TestBasePerfRegression' -u base \
        --stop-after-init --workers=0
    grep "tests when loading" ./odoo.log
"""

from odoo.tests.common import TransactionCase, tagged, warmup


@tagged("post_install", "-at_install", "base_perf")
class TestBasePerfRegression(TransactionCase):
    """Pin query counts for optimized base module methods."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partners with unique barcodes (for constraint + compute tests)
        cls.partners = cls.env["res.partner"].create(
            [
                {"name": f"PerfPartner_{i}", "barcode": f"PERF-BC-{i:04d}"}
                for i in range(10)
            ]
        )

        # Partners with unique VATs that do NOT exist elsewhere in DB.
        # Use a distinctive prefix so the pre-filter _read_group finds them
        # only in this batch — the optimization skips per-partner search
        # when a VAT is unique in the entire database.
        cls.vat_partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"VATPartner_{i}",
                    "vat": f"BE099900{i:04d}",
                    "country_id": cls.env.ref("base.be").id,
                }
                for i in range(5)
            ]
        )

        # Server actions with code (for show_code_history)
        cls.server_actions = cls.env["ir.actions.server"].create(
            [
                {
                    "name": f"PerfAction_{i}",
                    "model_id": cls.env.ref("base.model_res_partner").id,
                    "state": "code",
                    "code": f"record.write({{'name': 'v{i}'}})",
                }
                for i in range(5)
            ]
        )
        # Create history entries that differ from current code
        cls.env["ir.actions.server.history"].create(
            [
                {
                    "action_id": action.id,
                    "code": f"# old code for {action.name}",
                }
                for action in cls.server_actions
            ]
        )

        # Window actions with paths (for _check_path constraint)
        cls.window_actions = cls.env["ir.actions.act_window"].create(
            [
                {
                    "name": f"PerfWindow_{i}",
                    "res_model": "res.partner",
                    "path": f"perf-path-{i}",
                }
                for i in range(10)
            ]
        )

    # ------------------------------------------------------------------
    # _check_path: batch path validation constraint
    # ------------------------------------------------------------------

    @warmup
    def test_check_path_batch(self):
        """Path constraint uses 1 grouped _read_group, not N search_counts."""
        actions = self.window_actions
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            # 1 flush + 1 _read_group (uniqueness)
            actions._check_path()

    # ------------------------------------------------------------------
    # _check_barcode_unicity: batch barcode uniqueness
    # ------------------------------------------------------------------

    @warmup
    def test_check_barcode_batch(self):
        """Barcode constraint uses 1 search_fetch, not N search_counts."""
        partners = self.partners
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            # 1 read (barcodes) + 1 search_fetch (uniqueness)
            partners._check_barcode_unicity()

    # ------------------------------------------------------------------
    # _compute_show_code_history: batch history check
    # ------------------------------------------------------------------

    @warmup
    def test_compute_show_code_history(self):
        """Code history compute uses 1 search_fetch, not N search_counts."""
        actions = self.server_actions
        self.env.invalidate_all()
        with self.assertQueryCount(9):
            # 1 read (state/code) + 1 search_fetch (history) + cache writes
            # + extra compute triggers from sale/project modules on ir.actions.server
            actions._compute_show_code_history()

    # ------------------------------------------------------------------
    # _get_bindings: batch action loading per model
    # ------------------------------------------------------------------

    @warmup
    def test_get_bindings_cold_cache(self):
        """First bindings load does batch reads per action type, not per action."""
        Actions = self.env["ir.actions.actions"]
        # Clear all ormcaches (includes _get_bindings)
        self.registry.clear_all_caches()
        self.env.invalidate_all()
        with self.assertQueryCount(10):
            # 1 flush + 1 raw SQL (action ids/types)
            # + exists() + read() per action type (multiple types bound)
            # + xml_id lookups for group_ids
            # + additional binding types from sale/project/account modules
            Actions._get_bindings("res.partner")

    # ------------------------------------------------------------------
    # _compute_partner_share: batch via _read_group
    # ------------------------------------------------------------------

    @warmup
    def test_compute_partner_share(self):
        """Partner share compute uses 1 _read_group, not N per-partner checks."""
        partners = self.partners
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            # 1 read (superuser partner) + 1 default write + 1 _read_group
            # + 1 extra read from additional partner computes (sale/project)
            partners._compute_partner_share()

    # ------------------------------------------------------------------
    # _compute_is_public: precomputed public user set
    # ------------------------------------------------------------------

    @warmup
    def test_compute_is_public(self):
        """Public compute queries group membership directly, not per partner."""
        partners = self.partners
        self.env.invalidate_all()
        with self.assertQueryCount(6):
            # 1 ref lookup + 1 _read_group (group membership) + batch writes
            # + 1 extra from additional partner computes (sale/project)
            partners._compute_is_public()

    # ------------------------------------------------------------------
    # _compute_main_user_id: batch user resolution
    # ------------------------------------------------------------------

    @warmup
    def test_compute_main_user_id(self):
        """Main user compute uses 1 batch search_fetch, not per-partner user_ids."""
        partners = self.partners
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # 1 xmlid lookup (partner_root) + 1 xmlid lookup (user_root)
            # + 1 search_fetch (all active users) + cache writes
            # + 1 extra from additional partner computes (sale/project)
            partners._compute_main_user_id()

    # ------------------------------------------------------------------
    # _compute_same_vat_partner_id: pre-filtering with _read_group
    # ------------------------------------------------------------------

    @warmup
    def test_compute_same_vat(self):
        """Same VAT compute pre-filters with _read_group, skips unique VATs."""
        partners = self.vat_partners
        self.env.invalidate_all()
        with self.assertQueryCount(10):
            # Phase 1: reads (vat/country/company/parent)
            # Phase 2: 2x _read_group (existence check for VATs + registries)
            # Phase 3: 1-2 batch search_fetch (all candidates)
            # Phase 4: Python-only matching (0 queries)
            # + extra reads from additional partner computes (sale/project)
            partners._compute_same_vat_partner_id()

    # ------------------------------------------------------------------
    # _selection_target_model: ormcache (0 queries on warm cache)
    # ------------------------------------------------------------------

    @warmup
    def test_selection_target_model_cached(self):
        """Second call to _selection_target_model hits ormcache → 0 queries."""
        ServerAction = self.env["ir.actions.server"]
        # First call warms the cache (done by @warmup decorator)
        ServerAction._selection_target_model()
        self.env.invalidate_all()
        with self.assertQueryCount(0):
            ServerAction._selection_target_model()

    # ------------------------------------------------------------------
    # ir.model._view_ids: batch view lookup
    # ------------------------------------------------------------------

    @warmup
    def test_ir_model_view_ids(self):
        """View IDs compute uses 1 batch search, not N per-model searches."""
        ir_models = self.env["ir.model"].search([], limit=20)
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            # 1 flush + 1 read (model names) + 1 search (views) + 1 read (view.model)
            ir_models._view_ids()

    # ------------------------------------------------------------------
    # ir.model._inherited_models: batch inherited lookup
    # ------------------------------------------------------------------

    @warmup
    def test_ir_model_inherited_models(self):
        """Inherited models compute uses 1 batch search, not N per-model."""
        ir_models = self.env["ir.model"].search([], limit=20)
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            # 1 read (model names) + 1 search (parent models)
            # + additional reads from ir.model computes (sale/project/account)
            ir_models._inherited_models()

    # ------------------------------------------------------------------
    # ir.model._compute_count: single UNION ALL query
    # ------------------------------------------------------------------

    @warmup
    def test_ir_model_compute_count(self):
        """Record count uses 1 UNION ALL query, not N COUNT(*) per table."""
        ir_models = self.env["ir.model"].search([], limit=20)
        self.env.invalidate_all()
        with self.assertQueryCount(3):
            # 1 flush + 1 read (model names) + 1 UNION ALL (all tables)
            ir_models._compute_count()
