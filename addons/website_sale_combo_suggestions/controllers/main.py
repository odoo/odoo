"""Website combo suggestion controllers.

This module suggests discounted combo packs during checkout and applies the
discount when requested.  The implementation follows Odoo guidelines and keeps
the logic compact and easy to maintain.
"""

from odoo import http, _
from odoo.http import request

import logging

_logger = logging.getLogger(__name__)


class ComboController(http.Controller):
    """Controllers to manage combo suggestions and discounts."""

    def _get_currency(self, order):
        return order.currency_id or request.website.currency_id

    def _format_currency(self, amount, currency):
        amount = f"{amount:.2f}"
        return (
            f"{currency.symbol}{amount}"
            if currency.position == "before"
            else f"{amount}{currency.symbol}"
        )

    def _get_cart_quantities(self, order):
        return {
            line.product_id.id: line.product_uom_qty
            for line in order.order_line
            if line.product_id.default_code != "SIMPLE_DISCOUNT"
        }

    def _combo_requirements(self, combo):
        return {
            item.product_id.id: item.quatity or 1
            for item in combo.combo_item_ids
        }

    def _count_applied_combos(self, order, requirements):
        lines = order.order_line.filtered(
            lambda l: l.product_id.id in requirements and l.discount > 0
        )
        if not lines:
            return 0

        counts = []
        for line in lines:
            req = requirements[line.product_id.id]
            counts.append(int(line.product_uom_qty // req))

        return min(counts) if counts else 0

    def _clear_discounts(self, order):
        for line in order.order_line:
            if line.product_id.default_code != "SIMPLE_DISCOUNT" and line.discount:
                line.discount = 0.0

    def _consolidate_duplicate_lines(self, order):
        groups = {}
        for line in order.order_line:
            if line.product_id.default_code == "SIMPLE_DISCOUNT":
                continue

            taxes = tuple(sorted(line.tax_id.ids)) if line.tax_id else ()
            key = (line.product_id.id, line.price_unit, line.discount, taxes, line.product_uom.id)
            groups.setdefault(key, []).append(line)

        for lines in groups.values():
            if len(lines) < 2:
                continue
            main = lines[0]
            main.product_uom_qty = sum(l.product_uom_qty for l in lines)
            for dup in lines[1:]:
                dup.unlink()

    def _apply_discount(self, order, combo):
        requirements = self._combo_requirements(combo)
        cart_qty = self._get_cart_quantities(order)
        max_times = min(cart_qty.get(pid, 0) // qty for pid, qty in requirements.items())

        if max_times <= 0:
            return {
                "success": False,
                "error_code": "not_enough_qty",
            }

        self._clear_discounts(order)

        lines_map = {
            pid: order.order_line.filtered(lambda l, pid=pid: l.product_id.id == pid)
            for pid in requirements
        }

        total_price = sum(lines_map[pid][0].price_unit * qty for pid, qty in requirements.items())
        discount_percent = (total_price - combo.base_price) / total_price * 100

        for pid, qty in requirements.items():
            qty_to_discount = qty * max_times
            for line in lines_map[pid]:
                if qty_to_discount <= 0:
                    break
                if line.product_uom_qty > qty_to_discount:
                    line.copy({
                        "order_id": order.id,
                        "order_partner_id": order.partner_id.id,
                        "product_uom_qty": line.product_uom_qty - qty_to_discount,
                        "discount": 0.0,
                    })
                    line.product_uom_qty = qty_to_discount

                line.discount = min(discount_percent, 100)
                qty_to_discount -= line.product_uom_qty

        self._consolidate_duplicate_lines(order)

        return {
            "success": True,
            "times_applied": max_times,
            "savings_total": (total_price - combo.base_price) * max_times,
            "combo_name": combo.name,
        }

    @http.route("/shop/check_combos", type="jsonrpc", auth="public", website=True)
    def check_combos(self):
        order = request.website.sale_get_order()
        if not order:
            return []

        currency = self._get_currency(order)
        cart_qty = self._get_cart_quantities(order)
        if not cart_qty:
            return []

        combos = request.env["product.combo"].search([])
        result = []

        for combo in combos:
            requirements = self._combo_requirements(combo)
            max_times = min(cart_qty.get(pid, 0) // qty for pid, qty in requirements.items())

            applied = self._count_applied_combos(order, requirements)
            available = max_times - applied
            if available <= 0:
                continue

            total_price = 0.0
            for pid, qty in requirements.items():
                line = order.order_line.filtered(lambda l, pid=pid: l.product_id.id == pid)[:1]
                if line:
                    total_price += line.price_unit * qty

            savings = total_price - combo.base_price
            result.append(
                {
                    "id": combo.id,
                    "name": combo.name,
                    "savings": savings,
                    "individual_total": total_price,
                    "combo_price": combo.base_price,
                    "times_available": available,
                    "currency_symbol": currency.symbol,
                    "currency_position": currency.position,
                    "translations": {
                        "pack_available": _("Pack Available"),
                        "savings": _("Savings"),
                        "apply_discount": _("Apply Discount"),
                        "times_available": _("times available"),
                        "from": _("From"),
                        "for": _("for"),
                    },
                }
            )

        return result

    @http.route("/shop/apply_discount/<int:combo_id>", type="jsonrpc", auth="public", website=True)
    def apply_discount(self, combo_id):
        order = request.website.sale_get_order()
        combo = request.env["product.combo"].browse(combo_id)

        if not order or not combo:
            currency = request.website.currency_id
            return {
                "success": False,
                "error": _("Cart or combo not found"),
                "currency_symbol": currency.symbol,
                "currency_position": currency.position,
            }

        result = self._apply_discount(order, combo)
        currency = self._get_currency(order)

        if not result["success"]:
            return {
                "success": False,
                "error": {
                    "not_enough_qty": _("Insufficient quantity to apply combo"),
                }.get(result.get("error_code"), _("Unknown error")),
                "currency_symbol": currency.symbol,
                "currency_position": currency.position,
            }

        return {
            "success": True,
            "message": _(
                "%(count)sx Pack \"%(name)s\" applied - Total savings: %(amount)s",
                {
                    "count": result["times_applied"],
                    "name": result["combo_name"],
                    "amount": self._format_currency(result["savings_total"], currency),
                }
            ),
            "currency_symbol": currency.symbol,
            "currency_position": currency.position,
            "translations": {
                "discount_applied": _("Discount Applied!"),
                "total_savings": _("Total savings"),
            },
        }

    @http.route("/shop/recalculate_combos", type="jsonrpc", auth="public", website=True)
    def recalculate_combos(self):
        order = request.website.sale_get_order()
        currency = (order.currency_id or request.website.currency_id) if order else request.website.currency_id

        if not order:
            return {
                "success": False,
                "error": _("Cart not found"),
                "currency_symbol": currency.symbol,
                "currency_position": currency.position,
            }

        self._clear_discounts(order)
        self._consolidate_duplicate_lines(order)

        return {
            "success": True,
            "message": _("Discounts cleared and lines consolidated"),
            "refresh": True,
            "currency_symbol": currency.symbol,
            "currency_position": currency.position,
            "translations": {
                "recalculating": _("Recalculating combos..."),
                "cleaning_discounts": _("Clearing discounts and optimizing available packs"),
            },
        }
