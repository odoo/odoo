# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method", check_company=True, help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_message = fields.Char(readonly=True, copy=False)
    delivery_rating_success = fields.Boolean(copy=False)
    delivery_set = fields.Boolean(compute='_compute_delivery_state')
    recompute_delivery_price = fields.Boolean('Delivery cost should be recomputed')
    is_all_service = fields.Boolean("Service Product", compute="_compute_is_service_products")
    shipping_weight = fields.Float("Shipping Weight", compute="_compute_shipping_weight", store=True, readonly=False)

    @api.depends('order_line')
    def _compute_is_service_products(self):
        for so in self:
            so.is_all_service = all(line.product_id.type == 'service' for line in so.order_line.filtered(lambda x: not x.display_type))

    def _compute_amount_total_without_delivery(self):
        self.ensure_one()
        delivery_cost = sum([l.price_total for l in self.order_line if l.is_delivery])
        return self.amount_total - delivery_cost

    @api.depends('order_line')
    def _compute_delivery_state(self):
        for order in self:
            order.delivery_set = any(line.is_delivery for line in order.order_line)

    @api.onchange('order_line', 'partner_id', 'partner_shipping_id')
    def onchange_order_line(self):
        self.ensure_one()
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.recompute_delivery_price = True

    def _get_update_prices_lines(self):
        """ Exclude delivery lines from price list recomputation based on product instead of carrier """
        lines = super()._get_update_prices_lines()
        return lines.filtered(lambda line: not line.is_delivery)

    def _remove_delivery_line(self):
        """Remove delivery products from the sales orders"""
        delivery_lines = self.order_line.filtered("is_delivery")
        if not delivery_lines:
            return
        to_delete = delivery_lines.filtered(lambda x: x.qty_invoiced == 0)
        if not to_delete:
            raise UserError(
                _('You can not update the shipping costs on an order where it was already invoiced!\n\nThe following delivery lines (product, invoiced quantity and price) have already been processed:\n\n')
                + '\n'.join(['- %s: %s x %s' % (line.product_id.with_context(display_default_code=False).display_name, line.qty_invoiced, line.price_unit) for line in delivery_lines])
            )
        to_delete.unlink()

    def set_delivery_line(self, carrier, amount):
        self._remove_delivery_line()
        for order in self:
            order.carrier_id = carrier.id
            order._create_delivery_line(carrier, amount)
        return True

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id
        if self.env.context.get('carrier_recompute'):
            name = _('Update shipping cost')
            carrier = self.carrier_id
        else:
            name = _('Add a shipping method')
            carrier = (
                self.with_company(self.company_id).partner_shipping_id.property_delivery_carrier_id
                or self.with_company(self.company_id).partner_shipping_id.commercial_partner_id.property_delivery_carrier_id
            )
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_carrier_id': carrier.id,
                'default_total_weight': self._get_estimated_weight()
            }
        }

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id._filter_taxes_by_company(self.company_id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Create the sales order line

        if carrier.product_id.description_sale:
            so_description = '%s: %s' % (carrier.name,
                                        carrier.product_id.description_sale)
        else:
            so_description = carrier.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'price_unit': price_unit,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if carrier.free_over and self.currency_id.is_zero(price_unit) :
            values['name'] += '\n' + _('Free Shipping')
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        del context
        return values

    def _create_delivery_line(self, carrier, price_unit):
        values = self._prepare_delivery_line_vals(carrier, price_unit)
        return self.env['sale.order.line'].sudo().create(values)

    @api.depends('order_line.product_uom_qty', 'order_line.product_uom')
    def _compute_shipping_weight(self):
        for order in self:
            order.shipping_weight = order._get_estimated_weight()

    def _get_estimated_weight(self):
        self.ensure_one()
        weight = 0.0
        for order_line in self.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not l.is_delivery and not l.display_type and l.product_uom_qty > 0):
            weight += order_line.product_qty * order_line.product_id.weight
        return weight

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Override of `sale` to recompute the delivery prices.

        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super()._update_order_line_info(product_id, quantity, **kwargs)
        if self:
            self.onchange_order_line()
        return price_unit
