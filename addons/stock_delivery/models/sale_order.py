from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def set_delivery_line(self, carrier, amount):
        _debug.pipeline(
            "delivery_line_set", order=self.id, carrier=carrier.id, amount=amount
        )
        res = super().set_delivery_line(carrier, amount)
        for order in self:
            if order.state != "done":
                continue
            pending_deliveries = order.picking_ids.filtered(
                lambda p: (
                    p.state not in ("done", "cancel")
                    and not any(m.origin_returned_move_id for m in p.move_ids)
                )
            )
            pending_deliveries.carrier_id = carrier.id
        return res

    def _create_delivery_line(self, carrier, price_unit):
        _debug.lifecycle(
            "delivery_line_create", order=self.id, carrier=carrier.id, price=price_unit
        )
        sol = super()._create_delivery_line(carrier, price_unit)
        context = {}
        if self.partner_id:
            context["lang"] = self.partner_id.lang
        if carrier.invoice_policy == "real":
            sol.update(
                {
                    "price_unit": 0,
                    "name": self.with_context(**context).env._(
                        "%(name)s (Estimated Cost: %(cost)s)",
                        name=sol["name"],
                        cost=self.currency_id.format(price_unit),
                    ),
                }
            )
        return sol

    def _format_currency_amount(self, amount):
        pre = post = ""
        if self.currency_id.position == "before":
            pre = "{symbol}\N{NO-BREAK SPACE}".format(
                symbol=self.currency_id.symbol or ""
            )
        else:
            post = "\N{NO-BREAK SPACE}{symbol}".format(
                symbol=self.currency_id.symbol or ""
            )
        return f" {pre}{amount}{post}"


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_procurement_vals(self):
        values = super()._prepare_procurement_vals()
        if not values.get("route_ids") and self.order_id.carrier_id.route_ids:
            values["route_ids"] = self.order_id.carrier_id.route_ids
        return values

    def _get_fields_protected(self):
        fields = super()._get_fields_protected()
        if self.env.context.get("allow_delivery_cost_update") and all(
            self.mapped("is_delivery")
        ):
            fields = [f for f in fields if f not in ("price_unit", "name")]
        return fields
