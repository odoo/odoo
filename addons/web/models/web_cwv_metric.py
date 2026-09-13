import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WebCwvMetric(models.Model):
    _name = "web.cwv.metric"
    _description = "Core Web Vitals Metric"
    _order = "recorded_at desc"
    _log_access = False

    recorded_at = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        readonly=True,
        required=True,
    )
    url = fields.Char(
        string="URL",
        size=2048,
        index="btree",
        readonly=True,
        required=True,
        help="Browser path at the time the beacon fired (the query string is "
        "stripped before persisting).  May be the same path for many records.  "
        "Capped at 2048 chars at the DB level so a rogue writer cannot bloat "
        "the row.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index="btree_not_null",
        readonly=True,
        ondelete="set null",
        help="User logged in when the beacon fired; null for anonymous "
        "frontend traffic.",
    )
    lcp = fields.Float(
        string="LCP (ms)",
        readonly=True,
        help="Largest Contentful Paint — time from navigation start to the "
        "render of the largest visible element.  Lighthouse 'good' is < 2500.",
    )
    fcp = fields.Float(
        string="FCP (ms)",
        readonly=True,
        help="First Contentful Paint — time from navigation start to first "
        "text/image paint.  Lighthouse 'good' is < 1800.",
    )
    ttfb = fields.Float(
        string="TTFB (ms)",
        readonly=True,
        help="Time To First Byte — time from request start to the first "
        "byte of the response.  Lighthouse 'good' is < 800.",
    )
    inp = fields.Float(
        string="INP (ms)",
        readonly=True,
        help="Interaction to Next Paint — reported as the worst-observed "
        "interaction duration over the page lifetime (P100), a strict upper "
        "bound on the canonical P98 metric.  Vendoring the web-vitals library "
        "for a true P98 is a future improvement; the wire format won't change.",
    )
    cls = fields.Float(
        string="CLS",
        readonly=True,
        help="Cumulative Layout Shift — unitless score (0 is best).  "
        "Lighthouse 'good' is < 0.1.",
    )
    user_agent = fields.Char(
        size=512,
        readonly=True,
        help="Truncated to 500 chars at the controller; the 512-char DB cap is "
        "a backstop for any other write path.",
    )
    pageview_id = fields.Char(
        string="Pageview ID",
        size=64,
        readonly=True,
        help="Client-generated id, stable for one page load. Metrics arrive "
        "across several beacons as INP/CLS keep growing after the first "
        "tab-switch; the controller upserts on this key so a pageview "
        "contributes one row (updated to the latest values) instead of "
        "accumulating duplicates.",
    )

    _PAGEVIEW_UNIQUE_INDEX = "web_cwv_metric__pageview_id_uniq"

    def init(self):
        self.env.cr.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self._PAGEVIEW_UNIQUE_INDEX}
            ON {self._table} (pageview_id)
            WHERE pageview_id IS NOT NULL
            """
        )

    @api.model
    def _record_beacon(self, values):
        cols = (
            "url",
            "user_id",
            "lcp",
            "fcp",
            "cls",
            "ttfb",
            "inp",
            "user_agent",
            "pageview_id",
        )
        params = {
            "url": values["url"],
            "user_id": values.get("user_id") or None,
            "lcp": values.get("lcp"),
            "fcp": values.get("fcp"),
            "cls": values.get("cls"),
            "ttfb": values.get("ttfb"),
            "inp": values.get("inp"),
            "user_agent": values.get("user_agent") or None,
            "pageview_id": values.get("pageview_id") or None,
        }
        assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
        self.env.cr.execute(
            f"""
            INSERT INTO {self._table}
                (url, user_id, lcp, fcp, cls, ttfb, inp, user_agent,
                 pageview_id, recorded_at)
            VALUES
                (%(url)s, %(user_id)s, %(lcp)s, %(fcp)s, %(cls)s, %(ttfb)s,
                 %(inp)s, %(user_agent)s, %(pageview_id)s,
                 (now() AT TIME ZONE 'UTC'))
            ON CONFLICT (pageview_id) WHERE pageview_id IS NOT NULL
            DO UPDATE SET {assignments}, recorded_at = EXCLUDED.recorded_at
            """,
            params,
        )

    _check_latency_range = models.Constraint(
        "CHECK("
        " (lcp  IS NULL OR (lcp  >= 0 AND lcp  <= 3600000))"
        " AND (fcp  IS NULL OR (fcp  >= 0 AND fcp  <= 3600000))"
        " AND (ttfb IS NULL OR (ttfb >= 0 AND ttfb <= 3600000))"
        " AND (inp  IS NULL OR (inp  >= 0 AND inp  <= 3600000))"
        ")",
        "Core Web Vitals latencies must be between 0 and 3600000 ms.",
    )
    _check_cls_range = models.Constraint(
        "CHECK(cls IS NULL OR (cls >= 0 AND cls <= 1000))",
        "Cumulative Layout Shift must be between 0 and 1000.",
    )

    @api.model
    def _remove_old_metrics(self):
        days_str = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "web.cwv.retention_days",
                "30",
            )
        )
        try:
            days = int(days_str)
        except TypeError, ValueError:
            _logger.warning(
                "web.cwv.retention_days=%r is not an integer; skipping GC",
                days_str,
            )
            return
        if days <= 0:
            return
        self.env.cr.execute(
            "DELETE FROM web_cwv_metric"
            " WHERE recorded_at < (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')",
            (days,),
        )
        deleted = self.env.cr.rowcount
        if deleted:
            _logger.info(
                "[cwv-gc] deleted %d rows older than %d day(s)",
                deleted,
                days,
            )
