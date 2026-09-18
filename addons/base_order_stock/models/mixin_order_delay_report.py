from odoo import fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class MixinOrderDelayReport(models.AbstractModel):
    _name = "mixin.order.delay.report"
    _inherit = ["mixin.sql.report"]
    _description = "Order On-Time Transfer Report"
    _auto = False

    _order_line_table = ""
    _order_table = ""
    _link_column = ""
    _date_commitment_alias = ""
    # the move's end that meets the partner, and the usage it carries there:
    # a return reverses the direction and shares the order line, so without
    # this it counts as a second on-time transfer
    _partner_location_field = ""
    _partner_location_usage = ""

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    date = fields.Datetime(
        string="Effective Date",
        readonly=True,
    )
    qty_total = fields.Float(
        string="Total Quantity",
        readonly=True,
    )
    qty_on_time = fields.Float(
        string="On-Time Quantity",
        readonly=True,
    )
    on_time_rate = fields.Float(
        string="On-Time Delivery Rate",
        readonly=True,
    )

    def _get_date_commitment(self):
        return f"{self._date_commitment_alias}.date_commitment"

    def _get_qty_on_time(self):
        return (
            "SUM(CASE WHEN (m.state = 'done' AND "
            f"{self._get_date_commitment()}::date >= m.date::date) "
            "THEN ((ml.quantity * ml_uom.factor) / pt_uom.factor) ELSE 0 END)"
        )

    def _get_fields_select(self):
        qty_on_time = self._get_qty_on_time()
        return {
            "id": "ol.id",
            "date": "Min(m.date) FILTER (WHERE m.state = 'done')",
            "product_id": "ol.product_id",
            "category_id": "Min(pc.id)",
            "partner_id": "ol.partner_id",
            "company_id": "o.company_id",
            "qty_total": "ol.product_uom_qty",
            "qty_on_time": qty_on_time,
            "on_time_rate": (
                "CASE WHEN ol.product_uom_qty = 0 THEN 100 "
                f"ELSE {qty_on_time} / ol.product_uom_qty * 100 END"
            ),
        }

    def _get_from_tables(self):
        return [
            ("stock_move", "m", None, None),
            (
                self._order_line_table,
                "ol",
                "JOIN",
                f"ol.id = m.{self._link_column}",
            ),
            (self._order_table, "o", "JOIN", "o.id = ol.order_id"),
            ("product_product", "p", "JOIN", "p.id = m.product_id"),
            ("product_template", "pt", "JOIN", "pt.id = p.product_tmpl_id"),
            ("uom_uom", "pt_uom", "JOIN", "pt_uom.id = pt.uom_id"),
            (
                "stock_location",
                "pl",
                "JOIN",
                f"pl.id = m.{self._partner_location_field}",
            ),
            ("product_category", "pc", "LEFT JOIN", "pc.id = pt.categ_id"),
            ("stock_move_line", "ml", "LEFT JOIN", "ml.move_id = m.id"),
            ("uom_uom", "ml_uom", "LEFT JOIN", "ml_uom.id = ml.product_uom_id"),
        ]

    def _get_where_conditions(self):
        return [
            f"{self._get_date_commitment()} IS NOT NULL",
            self._get_partner_end_condition(),
        ]

    def _get_partner_end_condition(self):
        condition = f"pl.usage = '{self._partner_location_usage}'"
        inter_company = self.env.ref(
            "stock.stock_location_inter_company", raise_if_not_found=False
        )
        if inter_company and inter_company.parent_path:
            condition = f"({condition} OR starts_with(pl.parent_path, '{inter_company.parent_path}'))"
        return condition

    def _get_fields_group_by(self):
        return ["ol.id", "o.company_id"]

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == "on_time_rate:sum":
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
            having = Domain.AND([having, [("qty_total:sum", ">", 0)]])
        return super()._read_group(
            domain, groupby, aggregates, having, offset, limit, order
        )
