# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp.addons import decimal_precision


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.mixin']

    website_description = fields.Text('Description for Online Quotations')
    website_published = fields.Boolean('Visible in Website', default=True, copy=False)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_delivery = fields.Float(
        compute="_amount_all_wrapper", digits_compute=decimal_precision.get_precision('Account'),
        string='Delivery Amount', help="The amount without tax.", track_visibility='always'
    )

    @api.multi
    @api.depends('order_line', 'order_line.price_unit', 'order_line.tax_id', 'order_line.discount', 'order_line.product_uom_qty')
    def _amount_all_wrapper(self):
        """ Wrapper because of direct method passing as parameter for function fields """
        for order in self:
            line_amount = sum([line.price_subtotal for line in order.order_line if line.is_delivery])
            currency = order.pricelist_id.currency_id
            self.amount_delivery = currency.round(line_amount)

    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        domain=[('is_delivery', '=', False)],
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )

    def _check_carrier_quotation(self, force_carrier_id=None):
        self.ensure_one()
        # check to add or remove carrier_id
        if all(line.product_id.type == "service" for line in self.website_order_line):
            self.write({'carrier_id': None})
            self.sudo()._delivery_unset()
            return True
        else:
            carrier_id = force_carrier_id or self.carrier_id.id
            carrier_ids = self._get_delivery_methods().ids
            if carrier_id:
                if carrier_id not in carrier_ids:
                    carrier_id = False
                else:
                    carrier_ids.remove(carrier_id)
                    carrier_ids.insert(0, carrier_id)
            if force_carrier_id or not carrier_id or not carrier_id in carrier_ids:
                for delivery_id in carrier_ids:
                    grid_id = self.env['delivery.carrier'].sudo().browse(delivery_id).grid_get(self.partner_shipping_id.id)
                    if grid_id:
                        carrier_id = delivery_id
                        break
                self.write({'carrier_id': carrier_id})
            if carrier_id:
                self.delivery_set()
            else:
                self._delivery_unset()

        return bool(carrier_id)

    def _get_delivery_methods(self):
        self.ensure_one()
        deliveries = self.env['delivery.carrier'].with_context(order_id=self.id).search([('website_published', '=', True)])
        # Following loop is done to avoid displaying delivery methods who are not available for this order
        # This can surely be done in a more efficient way, but at the moment, it mimics the way it's
        # done in delivery_set method of sale.py, from delivery module
        return deliveries.filtered("available")

    def _get_errors(self):
        self.ensure_one()
        errors = super(SaleOrder, self)._get_errors()
        if not self._get_delivery_methods():
            errors.append(('No delivery method available', 'There is no available delivery method for your order'))
        return errors

    def _get_website_data(self):
        """ Override to add delivery-related website data. """
        values = super(SaleOrder, self)._get_website_data()
        # We need a delivery only if we have stockable products
        has_stockable_products = False
        for line in self.order_line:
            if line.product_id.type in ('consu', 'product'):
                has_stockable_products = True
        if not has_stockable_products:
            return values

        values['deliveries'] = self.sudo().with_context(order_id=self.id)._get_delivery_methods()
        return values
