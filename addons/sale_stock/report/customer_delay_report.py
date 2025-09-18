from odoo import fields, models, tools
from odoo.fields import Domain
from odoo.tools import SQL


class CustomerDelayReport(models.Model):
    _name = "customer.delay.report"
    _description = "Customer Delay Report"
    _auto = False

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        readonly=True,
    )
    category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        readonly=True,
    )
    date = fields.Datetime(string="Effective Date", readonly=True)
    qty_total = fields.Float(string="Total Quantity", readonly=True)
    qty_on_time = fields.Float(string="On-Time Quantity", readonly=True)
    on_time_rate = fields.Float(string="On-Time Delivery Rate", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, "customer_delay_report")
        self.env.cr.execute(
            """
            CREATE OR replace VIEW customer_delay_report AS(
            SELECT sol.id                AS id,
                Min(m.date)              AS date,
                sol.id                   AS sale_line_id,
                sol.product_id           AS product_id,
                Min(pc.id)               AS category_id,
                sol.partner_id           AS partner_id,
                sol.product_uom_qty      AS qty_total,
                SUM(CASE
                        WHEN (m.state = 'done' and so.date_commitment::date >= m.date::date) THEN ((ml.quantity * ml_uom.factor) / pt_uom.factor)
                        ELSE 0
                    END)                 AS qty_on_time
            FROM stock_move m
                JOIN sale_order_line sol
                    ON sol.id = m.sale_line_id
                JOIN sale_order so
                    ON so.id = sol.order_id
                JOIN product_product p
                    ON p.id = m.product_id
                JOIN product_template pt
                    ON pt.id = p.product_tmpl_id
                JOIN uom_uom pt_uom
                    ON pt_uom.id = pt.uom_id
                LEFT JOIN product_category pc
                    ON pc.id = pt.categ_id
                LEFT JOIN stock_move_line ml
                    ON ml.move_id = m.id
                LEFT JOIN uom_uom ml_uom
                    ON ml_uom.id = ml.product_uom_id
            WHERE so.date_commitment IS NOT NULL
            GROUP BY
                sol.id
            )
            """,
        )

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == "on_time_rate:sum":
            # Make a weighted average instead of simple average for these fields
            return SQL(
                "CASE WHEN SUM(%s) !=0 THEN SUM(%s) / SUM(%s) * 100 ELSE 100 END",
                self._field_to_sql(self._table, "qty_total", query),
                self._field_to_sql(self._table, "qty_on_time", query),
                self._field_to_sql(self._table, "qty_total", query),
            )
        return super()._read_group_select(aggregate_spec, query)

    def _read_group(
        self,
        domain,
        groupby=(),
        aggregates=(),
        having=(),
        offset=0,
        limit=None,
        order=None,
    ):
        if "on_time_rate:sum" in aggregates:
            having = Domain.AND([having, [("qty_total:sum", ">", "0")]])
        return super()._read_group(
            domain, groupby, aggregates, having, offset, limit, order
        )
