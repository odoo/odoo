from odoo import fields, models
from odoo.db.schema import drop_view_if_exists

from ..tools import debug_log as dbg


class ReportStockQuantity(models.Model):
    _name = "report.stock.quantity"
    _auto = False
    _description = "Stock Quantity Report"

    _depends = {
        "product.product": ["product_tmpl_id"],
        "product.template": ["is_storable", "uom_id"],
        "stock.location": ["usage", "warehouse_id"],
        "stock.move": [
            "company_id",
            "date",
            "location_dest_id",
            "location_final_id",
            "location_id",
            "product_id",
            "product_qty",
            "product_uom_id",
            "quantity",
            "state",
        ],
        "stock.quant": ["company_id", "location_id", "product_id", "quantity"],
        "uom.uom": ["factor"],
    }

    date = fields.Date(readonly=True)
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("forecast", "Forecasted Stock"),
            ("in", "Forecasted Receipts"),
            ("out", "Forecasted Deliveries"),
        ],
        readonly=True,
    )
    product_qty = fields.Float(
        string="Quantity",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        readonly=True,
    )

    def _get_product_qty_col(self):
        return "q.quantity"

    def _with_clause(self):
        return """
WITH
    existing_sm (id, product_id, tmpl_id, product_qty, quantity, date, state, company_id, whs_id, whd_id) AS (
        SELECT m.id, m.product_id, pt.id, m.product_qty,
            m.quantity * move_uom.factor / pt_uom.factor AS quantity,
            m.date, m.state, m.company_id, source.warehouse_id, dest.warehouse_id
        FROM stock_move m
        LEFT JOIN stock_location source ON source.id = m.location_id
        LEFT JOIN stock_location dest ON dest.id = CASE
            WHEN m.state != 'done' THEN COALESCE(m.location_final_id, m.location_dest_id)
            ELSE m.location_dest_id
        END
        LEFT JOIN product_product pp on pp.id=m.product_id
        LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
        LEFT JOIN uom_uom pt_uom ON pt_uom.id = pt.uom_id
        LEFT JOIN uom_uom move_uom ON move_uom.id = m.product_uom_id
        WHERE pt.is_storable = true AND
            source.warehouse_id IS DISTINCT FROM dest.warehouse_id AND
            m.product_qty != 0 AND
            m.state NOT IN ('draft', 'cancel') AND
            (m.state != 'done' or m.date >= ((now() at time zone 'utc')::date - make_interval(months => %(report_period)s)))
    ),
    all_sm (id, product_id, tmpl_id, product_qty, quantity, date, state, company_id, whs_id, whd_id) AS (
        SELECT sm.id, sm.product_id, sm.tmpl_id,
            CASE
                WHEN is_duplicated = 0 OR sm.whs_id != sm.whd_id THEN sm.product_qty
                ELSE 0
            END,
            CASE
                WHEN is_duplicated = 0 THEN sm.quantity
                WHEN sm.whs_id IS NOT NULL AND sm.whd_id IS NOT NULL AND sm.whs_id != sm.whd_id THEN sm.quantity
                ELSE 0
            END,
            sm.date, sm.state, sm.company_id,
            CASE WHEN is_duplicated = 0 THEN sm.whs_id END,
            CASE
                WHEN is_duplicated = 0 AND (sm.whs_id IS NULL OR sm.whd_id IS NULL OR sm.whs_id = sm.whd_id) THEN sm.whd_id
                WHEN is_duplicated = 1 AND (sm.whs_id IS NOT NULL AND sm.whd_id IS NOT NULL AND sm.whs_id != sm.whd_id) THEN sm.whd_id
            END
        FROM
            GENERATE_SERIES(0, 1, 1) is_duplicated,
            existing_sm sm
    )
"""

    def _select_moves(self):
        return """
    SELECT
        m.id,
        m.product_id,
        m.tmpl_id as product_tmpl_id,
        CASE
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL THEN 'out'
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL THEN 'in'
        END AS state,
        m.date::date AS date,
        CASE
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL THEN -m.product_qty
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL THEN m.product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL THEN m.whs_id
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL THEN m.whd_id
        END AS warehouse_id
    FROM
        all_sm m
    WHERE
        m.product_qty != 0 AND
        m.state != 'done'
"""

    def _select_quants(self):
        return f"""
    SELECT
        -q.id as id,
        q.product_id,
        pp.product_tmpl_id,
        'forecast' as state,
        date.*::date,
        {self._get_product_qty_col()} as product_qty,
        q.company_id,
        l.warehouse_id as warehouse_id
    FROM
        GENERATE_SERIES((now() at time zone 'utc')::date - make_interval(months => %(report_period)s),
        (now() at time zone 'utc')::date + make_interval(months => %(report_period)s), '1 day'::interval) date,
        stock_quant q
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN product_product pp on pp.id=q.product_id
    WHERE
        (l.usage = 'internal' AND l.warehouse_id IS NOT NULL) OR
        l.usage = 'transit'
"""

    def _select_forecast(self):
        return """
    SELECT
        m.id,
        m.product_id,
        m.tmpl_id as product_tmpl_id,
        'forecast' as state,
        GENERATE_SERIES(
        CASE
            WHEN m.state = 'done' THEN (now() at time zone 'utc')::date - make_interval(months => %(report_period)s)
            ELSE GREATEST(m.date::date, (now() at time zone 'utc')::date - make_interval(months => %(report_period)s))
        END,
        CASE
            WHEN m.state != 'done' THEN (now() at time zone 'utc')::date + make_interval(months => %(report_period)s)
            ELSE m.date::date - interval '1 day'
        END, '1 day'::interval)::date date,
        CASE
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL AND m.state = 'done' THEN m.quantity
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL AND m.state = 'done' THEN -m.quantity
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL THEN -m.product_qty
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL THEN m.product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN m.whs_id IS NOT NULL AND m.whd_id IS NULL THEN m.whs_id
            WHEN m.whd_id IS NOT NULL AND m.whs_id IS NULL THEN m.whd_id
        END AS warehouse_id
    FROM
        all_sm m
    WHERE
        m.product_qty != 0
"""

    def _get_report_period(self):
        report_period = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("stock.report_stock_quantity_period", default="3")
        )
        try:
            return int(report_period)
        except ValueError:
            dbg.logic.debug(
                "report_stock_quantity_period %r is not an int, using 3", report_period
            )
            return 3

    def init(self):
        dbg.lifecycle.debug(
            "report_stock_quantity view rebuilt (period %s)", self._get_report_period()
        )
        drop_view_if_exists(self.env.cr, "report_stock_quantity")
        query = f"""
CREATE or REPLACE VIEW report_stock_quantity AS (
{self._with_clause()}
SELECT
    MIN(id) as id,
    product_id,
    product_tmpl_id,
    state,
    date,
    sum(product_qty) as product_qty,
    company_id,
    warehouse_id
FROM ({self._select_moves()}
    UNION ALL
{self._select_quants()}
    UNION ALL
{self._select_forecast()}
) AS forecast_qty
GROUP BY product_id, product_tmpl_id, state, date, company_id, warehouse_id
);
"""
        self.env.cr.execute(query, {"report_period": self._get_report_period()})
