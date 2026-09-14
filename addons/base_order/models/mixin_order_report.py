from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

_debug = DebugLog(__name__)


class MixinOrderReport(models.AbstractModel):
    _name = "mixin.order.report"
    _inherit = "mixin.sql.report"
    _description = "Order Analysis Report Base"
    _auto = False
    _rec_name = "date_order"

    currency_id = fields.Many2one(comodel_name="res.currency")

    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    nbr_lines = fields.Integer(
        string="# of Lines",
        readonly=True,
    )
    date_order = fields.Datetime(
        string="Order Date",
        readonly=True,
    )
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string="Qty Ordered",
        readonly=True,
    )
    price_unit = fields.Float(
        string="Unit Price",
        readonly=True,
        aggregator="avg",
    )
    price_subtotal = fields.Monetary(
        string="Untaxed Total",
        readonly=True,
    )
    price_total = fields.Monetary(
        string="Total",
        readonly=True,
    )
    weight = fields.Float(
        string="Gross Weight",
        readonly=True,
    )
    volume = fields.Float(readonly=True)

    @api.readonly
    def action_view_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.order_reference._name,
            "views": [[False, "form"]],
            "res_id": self.order_reference.id,
        }

    def _get_where_conditions(self) -> list:
        return [
            "l.display_type IS NULL",
        ]

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        if aggregate_spec != "price_average:avg":
            return super()._read_group_select(aggregate_spec, query)
        _debug.logic("price_average_weighted", model=self._name)
        return SQL(
            "SUM(%(f_price)s * %(f_qty)s) / NULLIF(SUM(%(f_qty)s), 0.0)",
            f_qty=self._field_to_sql(self._table, "product_uom_qty", query),
            f_price=self._field_to_sql(self._table, "price_average", query),
        )
