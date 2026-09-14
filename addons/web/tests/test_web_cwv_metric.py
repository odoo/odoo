import json
from unittest.mock import patch

from psycopg.errors import CheckViolation

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("web_unit", "web_cwv")
class TestWebCwvMetric(TransactionCase):
    def _create(self, vals):
        rec = self.env["web.cwv.metric"].sudo().create(vals)
        self.env.flush_all()
        return rec

    def _assert_rejected(self, vals):
        with (
            self.assertRaises(CheckViolation),
            mute_logger("odoo.db"),
            self.cr.savepoint(),
        ):
            self._create(vals)

    def test_valid_metric_is_accepted(self):
        rec = self._create({"url": "/odoo", "lcp": 1200.0, "fcp": 900.0, "cls": 0.05})
        self.assertTrue(rec.id)

    def test_null_metrics_allowed(self):
        rec = self._create({"url": "/odoo"})
        self.assertTrue(rec.id)

    def test_negative_latency_rejected(self):
        self._assert_rejected({"url": "/odoo", "lcp": -1.0})

    def test_infinity_rejected(self):
        self._assert_rejected({"url": "/odoo", "lcp": float("inf")})

    def test_nan_rejected(self):
        self._assert_rejected({"url": "/odoo", "cls": float("nan")})

    def test_latency_over_cap_rejected(self):
        self._assert_rejected({"url": "/odoo", "ttfb": 36_000_000.0})

    def test_cls_over_cap_rejected(self):
        self._assert_rejected({"url": "/odoo", "cls": 99_999.0})

    def test_url_capped_at_db_level(self):
        rec = self._create({"url": "/" + "x" * 5000})
        self.assertLessEqual(len(rec.url), 2048)

    def test_controller_clamps_reject_non_finite(self):
        from odoo.addons.web.controllers.observability import (
            _MAX_CLS,
            _MAX_LATENCY_MS,
            _get_clamped_metric,
        )

        for bad in (float("nan"), float("inf"), float("-inf"), -1.0, True):
            for maximum in (_MAX_LATENCY_MS, _MAX_CLS):
                self.assertIsNone(
                    _get_clamped_metric(bad, maximum),
                    f"_get_clamped_metric({bad!r}, {maximum}) must be None",
                )
        self.assertEqual(_get_clamped_metric(1200, _MAX_LATENCY_MS), 1200.0)
        self.assertEqual(_get_clamped_metric(0.05, _MAX_CLS), 0.05)

    def test_rate_limiter_key_map_stays_bounded(self):
        from odoo.addons.web.controllers import observability as obs

        obs._rate_state.clear()
        self.addCleanup(obs._rate_state.clear)
        for i in range(obs._RATE_LIMIT_MAX_KEYS + 500):
            obs._is_rate_limited(f"flood:{i}")
        self.assertLessEqual(
            len(obs._rate_state),
            obs._RATE_LIMIT_MAX_KEYS,
            "the key map must stay bounded under a distinct-key flood",
        )


@tagged("-at_install", "post_install", "web_http", "web_cwv")
class TestWebCwvBeacon(HttpCase):
    def _beacon(self, payload):
        return self.url_open(
            "/web/observability/cwv",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_pageview_upsert(self):
        Metric = self.env["web.cwv.metric"].sudo()
        before = Metric.search_count([])

        pid = "pageview-upsert-test"
        r1 = self._beacon({"url": "/odoo", "pageview_id": pid, "lcp": 1000.0})
        self.assertEqual(r1.status_code, 204)
        r2 = self._beacon(
            {"url": "/odoo", "pageview_id": pid, "lcp": 1000.0, "inp": 250.0}
        )
        self.assertEqual(r2.status_code, 204)

        rows = Metric.search([("pageview_id", "=", pid)])
        self.assertEqual(len(rows), 1, "one row per pageview_id")
        self.assertEqual(rows.inp, 250.0, "row updated to the latest values")
        self.assertEqual(Metric.search_count([]) - before, 1)

    def test_missing_pageview_id_always_creates(self):
        Metric = self.env["web.cwv.metric"].sudo()
        before = Metric.search_count([])
        self._beacon({"url": "/odoo", "lcp": 1100.0})
        self._beacon({"url": "/odoo", "lcp": 1200.0})
        self.assertEqual(Metric.search_count([]) - before, 2)

    def test_rate_limited_beacons_are_capped(self):
        from odoo.addons.web.controllers import observability

        Metric = self.env["web.cwv.metric"].sudo()
        observability._rate_state.clear()
        self.addCleanup(observability._rate_state.clear)
        before = Metric.search_count([])

        with patch.object(observability, "_RATE_LIMIT_MAX", 3):
            statuses = [
                self._beacon(
                    {"url": "/odoo", "pageview_id": f"rate-{i}", "lcp": 1000.0}
                ).status_code
                for i in range(6)
            ]

        self.assertEqual(
            statuses[:3], [204, 204, 204], "beacons within the cap must be accepted"
        )
        self.assertTrue(
            all(s == 429 for s in statuses[3:]),
            f"beacons over the cap must be rejected with 429, got {statuses}",
        )
        self.assertEqual(Metric.search_count([]) - before, 3)

    def test_cwv_and_js_error_have_separate_budgets(self):
        from odoo.addons.web.controllers import observability as obs

        obs._rate_state.clear()
        self.addCleanup(obs._rate_state.clear)

        with (
            patch.object(obs, "_RATE_LIMIT_MAX", 2),
            mute_logger("odoo.addons.web.controllers.observability"),
        ):
            cwv = [
                self._beacon(
                    {"url": "/odoo", "pageview_id": f"sep-{i}", "lcp": 1000.0}
                ).status_code
                for i in range(3)
            ]
            err = self.url_open(
                "/web/observability/js_error",
                data=json.dumps({"message": "boom", "kind": "error"}),
                headers={"Content-Type": "application/json"},
            ).status_code

        self.assertEqual(cwv, [204, 204, 429], "CWV budget must be exhausted")
        self.assertEqual(
            err, 204, "js_error has its own budget, not starved by CWV volume"
        )
