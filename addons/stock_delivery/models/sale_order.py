# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_on_delivery = fields.Monetary(
        help="The amount that needs to be collected on the next delivery."
        " Computed based on the delivered quantities.",
        compute='_compute_amount_on_delivery',
        compute_sudo=True,  # Needs access to `transaction_ids`
    )

    def _compute_show_ship_button(self):
        self.show_ship_button = False  # Revert to Delivery smart button for stock module

    @api.depends('amount_unpaid', 'order_line.qty_delivered', 'order_line.product_uom_qty')
    @api.depends_context('prevalidated_move_ids')
    def _compute_amount_on_delivery(self):
        """Compute the amount to collect on the next delivery.

        For orders with a pending pay-on-delivery transaction, this is computed as the remaining
        balance minus the value of products that are not delivered yet. If nothing is delivered,
        the amount to collect is 0.
        """
        orders_pending_delivery_payment = self.filtered(
            lambda order: order.transaction_ids._filtered_pending_delivery_payment()
        )
        (self - orders_pending_delivery_payment).amount_on_delivery = 0

        # Use `_prepare_qty_delivered` because `qty_delivered` is stored and cannot depend on the
        # context, whereas we need to compute the delivered amount for the moves of the pickings
        # about to be validated -> `prevalidated_move_ids`.
        deliverable_lines = orders_pending_delivery_payment._get_deliverable_lines()
        qty_delivered_by_line = deliverable_lines._prepare_qty_delivered()

        def get_qty_delivered(line_):
            return qty_delivered_by_line.get(line_) or line_.qty_delivered

        for order in orders_pending_delivery_payment:
            if not any(map(get_qty_delivered, order.order_line & deliverable_lines)):
                # If nothing was delivered yet, no payment should be collected.
                order.amount_on_delivery = 0
                continue

            undelivered_amount = sum(
                (1 - get_qty_delivered(line) / line.product_uom_qty) * line.price_total
                for line in order.order_line & deliverable_lines
            )

            order.amount_on_delivery = max(order.amount_unpaid - undelivered_amount, 0)

    def set_delivery_line(self, carrier, amount):
        res = super().set_delivery_line(carrier, amount)
        for order in self:
            if order.state != 'sale':
                continue
            pending_deliveries = order.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel')
                          and not any(m.origin_returned_move_id for m in p.move_ids)
            )
            pending_deliveries.carrier_id = carrier.id
        return res

    def _create_delivery_line(self, carrier, price_unit):
        sol = super()._create_delivery_line(carrier, price_unit)
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
        if carrier.invoice_policy == 'real':
            sol.update({
                'price_unit': 0,
                'name': _(
                    "%(name)s (Estimated Cost: %(cost)s)",
                    name=sol["name"],
                    cost=self.currency_id.format(price_unit),
                ),
            })
        del context
        return sol


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        if not values.get("route_ids") and self.order_id.carrier_id.route_ids:
            values['route_ids'] = self.order_id.carrier_id.route_ids
        return values

    def _get_protected_fields(self):
        fields = super()._get_protected_fields()
        if self.env.context.get('allow_delivery_cost_update') and all(self.mapped('is_delivery')):
            fields = [f for f in fields if f not in ('price_unit', 'name')]
        return fields
