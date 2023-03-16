# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

    def set_delivery_line(self, carrier, amount):
        for order in self:
            if order.state in ('sale', 'done'):
                pending_deliverys = order.picking_ids.filtered(
                    lambda p: p.state not in ('done', 'cancel') and p.location_id == p.picking_type_id.warehouse_id.lot_stock_id)
                pending_deliverys.carrier_id = carrier.id
        return super().set_delivery_line(carrier, amount)
