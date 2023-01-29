# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        """Check if there is another sale order line which already contains the requested event_booth_pending_ids
        to overwrite it with the newly requested booths to avoid having multiple so_line related to the same booths"""
        self.ensure_one()
        lines = super(SaleOrder, self)._cart_find_product_line(product_id, line_id, **kwargs)
        if line_id:
            return lines
        event_booth_pending_ids = kwargs.get('event_booth_pending_ids')
        if event_booth_pending_ids:
            lines = lines.filtered(
                lambda line: any(booth.id in event_booth_pending_ids for booth in line.event_booth_pending_ids)
            )
        return lines

    def _website_product_id_change(self, order_id, product_id, qty=0, **kwargs):
        values = super(SaleOrder, self)._website_product_id_change(order_id, product_id, qty=qty, **kwargs)
        event_booth_pending_ids = kwargs.get('event_booth_pending_ids')
        if event_booth_pending_ids:
            order_line = self.env['sale.order.line'].sudo().search([
                ('id', 'in', self.order_line.ids),
                ('event_booth_pending_ids', 'in', event_booth_pending_ids)])
            booths = self.env['event.booth'].browse(event_booth_pending_ids).with_context(pricelist=self.pricelist_id.id)
            if order_line.event_booth_pending_ids.ids != event_booth_pending_ids:
                new_registrations_commands = [Command.create({
                                            'event_booth_id': booth.id,
                                            **kwargs.get('registration_values'),
                                        }) for booth in booths]
                if order_line:
                    event_booth_registrations_command = [Command.delete(reg.id) for reg in
                                                         order_line.event_booth_registration_ids] + new_registrations_commands
                else:
                    event_booth_registrations_command = new_registrations_commands
                values['event_booth_registration_ids'] = event_booth_registrations_command

            discount = 0
            order = self.env['sale.order'].sudo().browse(order_id)
            booth_currency = booths.product_id.currency_id
            pricelist_currency = order.pricelist_id.currency_id
            price_reduce = sum(booth.booth_category_id.price_reduce for booth in booths)
            if booth_currency != pricelist_currency:
                price_reduce = booth_currency._convert(
                    price_reduce,
                    pricelist_currency,
                    order.company_id,
                    order.date_order or fields.Datetime.now()
                )
            if order.pricelist_id.discount_policy == 'without_discount':
                price = sum(booth.booth_category_id.price for booth in booths)
                if price != 0:
                    if booth_currency != pricelist_currency:
                        price = booth_currency._convert(
                            price,
                            pricelist_currency,
                            order.company_id,
                            order.date_order or fields.Datetime.now()
                        )
                    discount = (price - price_reduce) / price * 100
                    price_unit = price
                    if discount < 0:
                        discount = 0
                        price_unit = price_reduce
                else:
                    price_unit = price_reduce

            else:
                price_unit = price_reduce

            if order.pricelist_id and order.partner_id:
                order_line = order._cart_find_product_line(booths.product_id.id)
                if order_line:
                    price_unit = self.env['account.tax']._fix_tax_included_price_company(price_unit, booths.product_id.taxes_id, order_line[0].tax_id, self.company_id)

            values.update(
                event_id=booths.event_id.id,
                discount=discount,
                price_unit=price_unit,
                name=booths._get_booth_multiline_description(),
            )

        return values

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = {}
        product = self.env['product.product'].browse(product_id)
        if product.detailed_type == 'event_booth' and line_id:
            if set_qty > 1:
                set_qty = 1
                values['warning'] = _('You cannot manually change the quantity of an Event Booth product.')
            if add_qty == 0 and not kwargs.get('event_booth_pending_ids'):
                # when updating the pricelist, the website_sale module call this method without the 'event.booth' ids
                # -> we manually set the argument to make sure the price is updated in '_website_product_id_change'
                kwargs['event_booth_pending_ids'] = self.env['sale.order.line'].browse(line_id).event_booth_pending_ids.ids
        values.update(super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs))
        return values
