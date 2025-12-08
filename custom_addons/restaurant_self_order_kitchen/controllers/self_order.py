from odoo import http
from odoo.http import request


class SelfOrderController(http.Controller):
    """
    Controllers for customer self-order and kitchen screens.
    """

    @http.route(["/self_order"], type="http", auth="public", website=True)
    def self_order_form(self, table=None, **kwargs):
        table_rec = None
        if table:
            table_rec = request.env["pos.restaurant.table"].sudo().search(
                [("name", "=", table)], limit=1
            )

        products = request.env["product.product"].sudo().search(
            [("sale_ok", "=", True)]
        )

        values = {
            "table_code": table,
            "table": table_rec,
            "products": products,
        }
        return request.render(
            "restaurant_self_order_kitchen.self_order_page",
            values,
        )

    @http.route(
        ["/self_order/submit"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def self_order_submit(self, **post):
        table_code = post.get("table_code")
        table_rec = None
        if table_code:
            table_rec = request.env["pos.restaurant.table"].sudo().search(
                [("name", "=", table_code)], limit=1
            )

        order_lines = []
        for key, val in post.items():
            if key.startswith("product_"):
                try:
                    product_id = int(key.replace("product_", ""))
                    qty = float(val or 0)
                except Exception:
                    continue
                if qty <= 0:
                    continue
                order_lines.append((0, 0, {
                    "product_id": product_id,
                    "product_uom_qty": qty,
                }))

        so_vals = {
            "partner_id": request.website.user_id.partner_id.id,
            "table_id": table_rec.id if table_rec else False,
            "is_self_order": True,
            "order_line": order_lines,
            "client_order_ref": table_code or "",
        }
        order = request.env["sale.order"].sudo().create_from_self_order(so_vals)

        ticket_vals = {
            "order_id": order.id,
            "table_id": table_rec.id if table_rec else False,
            "note": post.get("global_note") or "",
            "line_ids": [],
        }
        line_commands = []
        for line in order.order_line:
            line_commands.append((0, 0, {
                "product_id": line.product_id.id,
                "qty": line.product_uom_qty,
                "note": line.name,
            }))
        ticket_vals["line_ids"] = line_commands

        request.env["restaurant.kitchen_ticket"].sudo().create(ticket_vals)

        return request.render(
            "restaurant_self_order_kitchen.self_order_thanks_page",
            {"order": order, "table": table_rec},
        )


class KitchenScreenController(http.Controller):

    @http.route(
        ["/kitchen/screen"],
        type="http",
        auth="user",
        website=True,
    )
    def kitchen_screen(self, **kwargs):
        KitchenTicket = request.env["restaurant.kitchen_ticket"].sudo()
        tickets_new = KitchenTicket.search([("state", "=", "new")])
        tickets_in_progress = KitchenTicket.search([("state", "=", "in_progress")])

        values = {
            "tickets_new": tickets_new,
            "tickets_in_progress": tickets_in_progress,
        }
        return request.render(
            "restaurant_self_order_kitchen.kitchen_screen_page",
            values,
        )

    @http.route(
        ["/kitchen/ticket/set_state"],
        type="json",
        auth="user",
    )
    def set_ticket_state(self, ticket_id, state):
        ticket = request.env["restaurant.kitchen_ticket"].sudo().browse(int(ticket_id))
        if ticket.exists() and state in ["new", "in_progress", "done"]:
            ticket.state = state
        return {"result": "ok", "state": ticket.state if ticket else None}
