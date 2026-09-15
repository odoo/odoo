from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    use_expiration_date = fields.Boolean(related="product_id.use_expiration_date")

    def _read_qties(self, date, wh):
        res = super(
            SaleOrderLine, self.with_context(fresh_qty_forecast=True)
        )._read_qties(date, wh)
        if any(self.mapped("use_expiration_date")):
            _debug.logic("free_qty_from_expiry", lines=self)
            for res_record, read_record in zip(
                res,
                self.mapped("product_id")
                .with_context(warehouse_id=wh)
                .read(["qty_free"]),
                strict=True,
            ):
                res_record["qty_free"] = read_record["qty_free"]
        return res
