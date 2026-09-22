from odoo import api, fields, models


class EventEvent(models.Model):
    _inherit = "event.event"

    sale_order_lines_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="event_id",
        string="All sale order lines pointing to this event",
        groups="sale.group_sale_salesman",
    )
    sale_price_total = fields.Monetary(
        string="Sales (Tax Included)",
        compute="_compute_sale_price_total",
        groups="sale.group_sale_salesman",
    )

    @api.depends(
        "company_id.currency_id",
        "sale_order_lines_ids.price_total",
        "sale_order_lines_ids.currency_id",
        "sale_order_lines_ids.company_id",
        "sale_order_lines_ids.order_id.date_order",
        # the _read_group below filters on it, so cancelling an order has to
        # drop its lines back out of the total
        "sale_order_lines_ids.state",
    )
    def _compute_sale_price_total(self):
        """Sum confirmed sale.order.line amounts, converted to the event company's currency."""
        # Conversion rates are taken as of 'today' rather than each sale.order's own date,
        # to avoid one currency-conversion request per sale.order (one is created per
        # event ticket sold).
        date_now = fields.Datetime.now()
        event_subtotals = self.env["sale.order.line"]._read_group(
            [
                ("event_id", "in", self.ids),
                ("price_total", "!=", 0),
                ("state", "=", "done"),
            ],
            ["event_id", "currency_id"],
            ["price_total:sum"],
        )
        event_subtotals_mapping = dict.fromkeys(self._origin, 0)
        for event, currency, sum_price_total in event_subtotals:
            event_subtotals_mapping[event] += currency._convert(
                sum_price_total,
                event.currency_id,
                event.company_id or self.env.company,
                date_now,
            )

        for event in self:
            event.sale_price_total = event_subtotals_mapping.get(event._origin, 0)

    def action_view_linked_orders(self):
        """Redirects to only the confirmed orders linked to the current events"""
        sale_order_action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "sale.action_sale_order"
        )
        sale_order_action.update(
            {
                "domain": [
                    ("state", "=", "done"),
                    ("line_ids.event_id", "in", self.ids),
                ],
                "context": {"create": 0},
            }
        )
        return sale_order_action
