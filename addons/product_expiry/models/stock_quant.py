from datetime import datetime

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.stock.tools.reservation import RemovalStrategy


def _fefo_sort_key(quant):
    """Python mirror of `removal_date, in_date, id` for the quants-cache path.

    `removal_date` may be unset; Postgres orders NULLs last in ASC, so unset
    dates sort after real ones. The leading `is False` flag reproduces that, so
    the sentinel beside it is only ever compared inside the unset group, never
    against a real date. Odoo datetimes are naive-UTC, hence naive `datetime.min`.
    """
    return (
        quant.removal_date is False,
        quant.removal_date or datetime.min,  # noqa: DTZ901  naive sentinel, the field is naive UTC
        quant.in_date,
        quant.id,
    )


FEFO_REMOVAL_STRATEGY = RemovalStrategy(
    order="removal_date, in_date, id",
    sort_key=_fefo_sort_key,
)


_debug = DebugLog(__name__)


class StockQuant(models.Model):
    _inherit = "stock.quant"

    expiration_date = fields.Datetime(
        related="lot_id.expiration_date",
    )
    removal_date = fields.Datetime(  # noqa: E8529  FEFO gathers ORDER BY removal_date, in_date, id, and report_stock_quantity reads the column
        related="lot_id.removal_date",
        store=True,
    )
    use_expiration_date = fields.Boolean(related="product_id.use_expiration_date")
    available_quantity = fields.Float(
        help="On hand quantity which hasn't been reserved on a transfer and is still fresh, in the default unit of measure of the product"
    )

    def _get_domain_expiration(self):
        cutoff = self.env.context.get("with_expiration")
        if not cutoff:
            return super()._get_domain_expiration()
        return Domain("removal_date", ">=", cutoff) | Domain("removal_date", "=", False)

    def _filtered_not_expired(self):
        _debug.logic("quants_expiry_filter", quants=self)
        cutoff = self.env.context.get("with_expiration")
        if not cutoff:
            return super()._filtered_not_expired()
        cutoff = fields.Datetime.to_datetime(cutoff)
        return self.filtered(
            lambda quant: not quant.removal_date or quant.removal_date >= cutoff
        )

    def _get_gs1_barcode(self, gs1_quantity_rules_ai_by_uom=False):
        barcode = super()._get_gs1_barcode(gs1_quantity_rules_ai_by_uom)
        if self.use_expiration_date:
            if self.expiration_date:
                barcode = "17" + self.expiration_date.strftime("%y%m%d") + barcode
            if self.lot_id.use_date:
                barcode = "15" + self.lot_id.use_date.strftime("%y%m%d") + barcode
        return barcode

    @api.model
    def _get_removal_strategies(self):
        _debug.logic("removal_strategies_read", quants=self)
        strategies = super()._get_removal_strategies()
        strategies["fefo"] = FEFO_REMOVAL_STRATEGY
        return strategies

    @api.depends("removal_date")
    def _compute_available_quantity(self):
        super()._compute_available_quantity()
        current_date = fields.Datetime.now()
        for quant in self:
            if quant.removal_date and quant.removal_date <= current_date:
                quant.available_quantity = 0

    def _aggregates_through_records(self, field, func):
        # _read_group_select below answers this one in SQL
        if field.name == "available_quantity" and func == "sum":
            return False
        return super()._aggregates_through_records(field, func)

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec != "available_quantity:sum":
            return super()._read_group_select(aggregate_spec, query)
        removal_date = self._field_to_sql(self._table, "removal_date", query)
        return SQL(
            "SUM(CASE WHEN %(removal_date)s IS NULL OR %(removal_date)s > %(now)s"
            " THEN %(quantity)s - %(reserved)s ELSE 0 END)",
            removal_date=removal_date,
            now=fields.Datetime.now(),
            quantity=self._field_to_sql(self._table, "quantity", query),
            reserved=self._field_to_sql(self._table, "reserved_quantity", query),
        )

    def _with_view_context(self):
        self_with_context = self
        if (
            self.env.context.get("default_product_id")
            and self.env["product.product"]
            .browse(self.env.context.get("default_product_id"))
            .use_expiration_date
        ):
            self_with_context = self.with_context(show_removal_date=True)
        return super(StockQuant, self_with_context)._with_view_context()
