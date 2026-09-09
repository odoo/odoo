import logging
from collections import defaultdict

from dateutil import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

_LEAD_TIME_STATS_QUERY = """
WITH RECURSIVE receipt AS (
    SELECT DISTINCT
        sp.id,
        sp.backorder_id,
        sp.create_date,
        sp.date_done
    FROM stock_picking sp
    JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
    JOIN stock_move sm ON sm.picking_id = sp.id
    WHERE sp.state = 'done'
      AND sm.state = 'done'
      AND sp.date_done IS NOT NULL
      AND sp.date_done >= %s
      AND spt.code = 'incoming'
      AND sm.product_id = ANY(%s)
      AND sm.location_dest_id IN (
          SELECT id FROM stock_location
          WHERE parent_path LIKE %s
      )
),
chain AS (
    SELECT r.id AS receipt_id, r.backorder_id, r.create_date
    FROM receipt r
    UNION ALL
    SELECT c.receipt_id, sp.backorder_id, sp.create_date
    FROM chain c
    JOIN stock_picking sp ON sp.id = c.backorder_id
),
ordered AS (
    SELECT receipt_id, create_date AS ordered_date
    FROM chain
    WHERE backorder_id IS NULL
      AND create_date IS NOT NULL
),
receipts AS (
    SELECT DISTINCT ON (sm.product_id, r.id)
        sm.product_id,
        r.date_done,
        EXTRACT(EPOCH FROM (r.date_done - o.ordered_date)) / 86400.0
            AS lead_time_days
    FROM stock_move sm
    JOIN receipt r ON sm.picking_id = r.id
    JOIN ordered o ON o.receipt_id = r.id
    WHERE sm.state = 'done'
      AND r.date_done - o.ordered_date >= interval '1 hour'
      AND sm.product_id = ANY(%s)
      AND sm.location_dest_id IN (
          SELECT id FROM stock_location
          WHERE parent_path LIKE %s
      )
    ORDER BY sm.product_id, r.id
),
ranked_receipts AS (
    SELECT
        product_id,
        lead_time_days,
        ROW_NUMBER() OVER (
            PARTITION BY product_id
            ORDER BY date_done DESC
        ) AS rn
    FROM receipts
)
SELECT
    product_id,
    COALESCE(AVG(lead_time_days), 0),
    COALESCE(STDDEV_POP(lead_time_days), 0),
    COUNT(*)
FROM ranked_receipts
WHERE rn <= %s
GROUP BY product_id
"""


class StockWarehouseOrderpointLeadTime(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @api.depends(
        "location_id",
        "warehouse_id",
        "product_min_qty",
        "route_id",
        "rule_ids",
        "product_id.route_ids",
        "product_id.stock_move_ids.date",
        "product_id.stock_move_ids.state",
        "product_id.seller_ids",
        "product_id.seller_ids.delay",
        "company_id.horizon_days",
    )
    @dbg.timed
    def _compute_deadline_date(self):
        canonical = self._with_canonical_horizon()
        critical_orderpoints = canonical.filtered(
            lambda o: o.product_uom_id.compare(o.qty_on_hand, o.product_min_qty) < 0,
        )
        critical_orderpoints.deadline_date = fields.Date.today()
        orderpoints_to_compute = canonical - critical_orderpoints
        dbg.logic.debug(
            "_compute_deadline_date: critical %s, timeline for %s",
            dbg.rec(critical_orderpoints),
            dbg.rec(orderpoints_to_compute),
        )
        if not orderpoints_to_compute:
            return

        for company in orderpoints_to_compute.company_id:
            company_orderpoints = orderpoints_to_compute.filtered(
                lambda c, company=company: c.company_id == company,
            )
            horizon_date = fields.Date.today() + relativedelta.relativedelta(
                days=company.horizon_days,
            )
            moves_by_product = company_orderpoints._read_pending_moves_by_product(
                horizon_date,
            )
            for orderpoint in company_orderpoints:
                orderpoint.deadline_date = orderpoint._get_deadline_from_timeline(
                    moves_by_product.get(orderpoint.product_id.id, ()),
                    horizon_date,
                )

    def _get_domains_pending_moves(self, horizon_date):
        _dummy, domain_move_in, domain_move_out = self.env[
            "stock.location"
        ]._get_domains_quantity(self.location_id.ids)
        scope = Domain.AND(
            [
                [("product_id", "in", self.product_id.ids)],
                [
                    (
                        "state",
                        "in",
                        ("waiting", "confirmed", "assigned", "partially_available"),
                    ),
                ],
                [("date", "<=", horizon_date)],
            ],
        )
        return scope & domain_move_in, scope & domain_move_out

    def _read_pending_moves_by_product(self, horizon_date):
        domain_move_in, domain_move_out = self._get_domains_pending_moves(horizon_date)
        Move = self.env["stock.move"].with_context(active_test=False)
        moves_by_product = defaultdict(list)
        for product, location_dest, location_final, in_date, in_qty in Move._read_group(
            domain_move_in,
            ["product_id", "location_dest_id", "location_final_id", "date:day"],
            ["product_qty:sum"],
        ):
            arrival = location_final or location_dest
            moves_by_product[product.id].append(
                (arrival.parent_path or "", in_date.date(), in_qty),
            )
        for product, location, out_date, out_qty in Move._read_group(
            domain_move_out,
            ["product_id", "location_id", "date:day"],
            ["product_qty:sum"],
        ):
            moves_by_product[product.id].append(
                (location.parent_path or "", out_date.date(), -out_qty),
            )
        dbg.performance.debug(
            "_read_pending_moves_by_product until %s: %d products, %d timeline rows",
            horizon_date,
            len(moves_by_product),
            sum(len(rows) for rows in moves_by_product.values()),
        )
        return moves_by_product

    def _get_deadline_from_timeline(self, timeline, horizon_date):
        self.check_singleton()
        location_path = self.location_id.parent_path or ""
        qty_by_date = defaultdict(float)
        for move_path, move_date, move_qty in timeline:
            if location_path and move_path.startswith(location_path):
                qty_by_date[move_date] += move_qty
        qty_on_hand_at_date = self.qty_on_hand
        for move_date, move_qty in sorted(qty_by_date.items()):
            qty_on_hand_at_date += move_qty
            if (
                self.product_uom_id.compare(qty_on_hand_at_date, self.product_min_qty)
                < 0
            ):
                deadline = move_date - relativedelta.relativedelta(days=self.lead_days)
                dbg.logic.debug(
                    "[orderpoint:%s] below min on %s (%s), deadline %s (horizon %s)",
                    self.id,
                    move_date,
                    qty_on_hand_at_date,
                    deadline,
                    horizon_date,
                )
                return deadline if deadline < horizon_date else False
        return False

    @api.depends("product_id", "warehouse_id")
    def _compute_lead_time_stats(self):
        result_map = self._read_lead_time_stats()
        for orderpoint in self:
            avg, stddev, count = result_map.get(
                (orderpoint.product_id.id, orderpoint.warehouse_id.id),
                (0.0, 0.0, 0),
            )
            orderpoint.actual_lead_time_avg = avg
            orderpoint.actual_lead_time_stddev = stddev
            orderpoint.lead_time_sample_count = count

    @dbg.timed
    def _read_lead_time_stats(self):
        self.env["stock.move"].flush_model()
        self.env["stock.picking"].flush_model()
        wh_orderpoints = defaultdict(lambda: self.env["stock.warehouse.orderpoint"])
        for orderpoint in self:
            if orderpoint.product_id and orderpoint.warehouse_id:
                wh_orderpoints[orderpoint.warehouse_id] |= orderpoint

        date_done_cutoff = fields.Datetime.now() - relativedelta.relativedelta(
            days=self._LEAD_TIME_LOOKBACK_DAYS,
        )
        result_map = {}
        for warehouse, orderpoints in wh_orderpoints.items():
            product_ids = orderpoints.product_id.ids
            parent_path = warehouse.view_location_id.parent_path
            if not product_ids or not parent_path:
                continue

            self.env.cr.execute(
                _LEAD_TIME_STATS_QUERY,
                (
                    date_done_cutoff,
                    product_ids,
                    f"{parent_path}%",
                    product_ids,
                    f"{parent_path}%",
                    self._LEAD_TIME_SAMPLE_SIZE,
                ),
            )

            for product_id, avg_lt, stddev_lt, count in self.env.cr.fetchall():
                result_map[(product_id, warehouse.id)] = (
                    max(avg_lt, 0.0),
                    max(stddev_lt, 0.0),
                    count,
                )
        dbg.performance.debug(
            "_read_lead_time_stats: %d warehouses queried, %d (product, warehouse) rows",
            len(wh_orderpoints),
            len(result_map),
        )
        return result_map

    @api.depends(
        "rule_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.delay",
        "company_id.horizon_days",
    )
    @api.depends_context("global_horizon_days")
    def _compute_lead_time(self):
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: orderpoint.product_id and orderpoint.location_id,
        )
        values_by_orderpoint = orderpoints_to_compute._prepare_lead_time_params_map()
        for orderpoint in orderpoints_to_compute.with_context(
            bypass_delay_description=True,
        ):
            values = values_by_orderpoint[orderpoint.id]
            lead_days, _dummy = orderpoint.rule_ids.with_context(
                global_horizon_days=orderpoint._get_horizon_days(),
            )._get_lead_days(
                orderpoint.product_id,
                **values,
            )
            orderpoint.lead_horizon_date = (
                fields.Date.today()
                + relativedelta.relativedelta(
                    days=lead_days["total_delay"] + lead_days["horizon_time"],
                )
            )
            orderpoint.lead_days = lead_days["total_delay"]
            dbg.logic.debug(
                "[orderpoint:%s] lead days %s, horizon %s -> %s",
                orderpoint.id,
                lead_days["total_delay"],
                lead_days["horizon_time"],
                orderpoint.lead_horizon_date,
            )
        excluded = self - orderpoints_to_compute
        excluded.lead_horizon_date = False
        excluded.lead_days = 0.0

    @api.depends("route_id", "product_id")
    def _compute_days_to_order(self):
        self.days_to_order = 0
