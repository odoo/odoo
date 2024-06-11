# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
                'name': sol['name']+ _(
                    ' (Estimated Cost: %s )',
                    self._format_currency_amount(price_unit)
                ),
            })
        del context
        return sol

    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.currency_id.symbol or '')
        return u' {pre}{0}{post}'.format(amount, pre=pre, post=post)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_values(self, group_id):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        if not values.get("route_ids") and self.order_id.carrier_id.route_ids:
            values['route_ids'] = self.order_id.carrier_id.route_ids
        return values
