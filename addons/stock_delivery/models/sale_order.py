# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipping_weight = fields.Float("Shipping Weight", compute="_compute_shipping_weight", store=True, readonly=False)

    def action_open_delivery_wizard(self):
        context_values = super().action_open_delivery_wizard()
        context_values['context'].update(default_total_weight=self._get_estimated_weight())
        return context_values

    def _create_delivery_line(self, carrier, price_unit):
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
        sol = super()._create_delivery_line(carrier, price_unit)
        if carrier.invoice_policy == 'real':
            sol.update({
                'price_unit': 0,
                'name': sol['name']+ _(
                    ' (Estimated Cost: %s )', self._format_currency_amount(price_unit)
                ),
            })
        del context
        return sol

    @api.depends('order_line.product_uom_qty', 'order_line.product_uom')
    def _compute_shipping_weight(self):
        for order in self:
            order.shipping_weight = order._get_estimated_weight()

    def _get_estimated_weight(self):
        self.ensure_one()
        if self.delivery_set:
            return self.shipping_weight
        weight = 0.0
        for order_line in self.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not l.is_delivery and not l.display_type):
            weight += order_line.product_qty * order_line.product_id.weight
        return weight
