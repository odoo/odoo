# -*- coding: utf-8 -*-

from openerp.osv import orm, fields
from openerp import SUPERUSER_ID
from openerp.addons import decimal_precision


class delivery_carrier(orm.Model):
    _inherit = 'delivery.carrier'
    _columns = {
        'website_published': fields.boolean('Available in the website', copy=False),
        'website_description': fields.text('Description for the website'),
    }
    _defaults = {
        'website_published': True
    }


class SaleOrder(orm.Model):
    _inherit = 'sale.order'

    def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
        """ Wrapper because of direct method passing as parameter for function fields """
        return self._amount_all(cr, uid, ids, field_name, arg, context=context)

    def _calculate_line_amount(self, cr, uid, order):
        tax_ob = self.pool['account.tax']
        precision_ob = self.pool['decimal.precision']
        precision = precision_ob.precision_get(cr, uid, 'Account')
        total = 0.0

        for line in order.order_line:
            if not line.is_delivery:
                continue
            price = line.price_unit
            product = line.product_id.id
            quantity = line.product_uom_qty

            tax_compute_precision = precision
            if line.tax_id and \
                    line.tax_id[0].company_id.tax_calculation_rounding_method \
                    == 'round_globally':
                tax_compute_precision += 5

            # *ex =  tax excluded
            # *in = tax included
            totalin = totalex = round(price * quantity, precision)
            tax_in = []
            tax_ex = []
            for tax in line.tax_id:
                if not tax.price_include:
                    tax_ex.append(tax)
                else:
                    tax_in.append(tax)
            tin = tax_ob.compute_inv(cr, uid,
                                     tax_in, price, quantity,
                                     product=product,
                                     precision=tax_compute_precision)
            for r in tin:
                totalex -= r.get('amount', 0.0)
            totlex_qty = 0.0
            try:
                totlex_qty = totalex / quantity
            except:
                pass
            tex = tax_ob._compute(cr, uid,
                                  tax_ex, totlex_qty, quantity,
                                  product=product,
                                  precision=tax_compute_precision)
            for r in tex:
                totalin += r.get('amount', 0.0)
            if tax_in:
                total += totalin
            if tax_ex:
                total += totalex
        return total

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(SaleOrder, self)._amount_all(
            cr, uid, ids, field_name, arg, context=context)
        currency_pool = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            line_amount = self._calculate_line_amount(cr, uid, order)
            # line_amount = sum([line.price_subtotal
            #                    for line in order.order_line
            #                    if line.is_delivery])
            currency = order.pricelist_id.currency_id
            res[order.id]['amount_delivery'] = currency_pool.round(
                cr, uid, currency, line_amount)
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids,
                                                            context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_delivery': fields.function(
            _amount_all_wrapper, type='float',
            digits_compute=decimal_precision.get_precision('Account'),
            string='Delivery Amount',
            store={
                'sale.order': (
                    lambda self, cr, uid, ids, c={}: ids,
                    ['order_line'],
                    10),
                'sale.order.line': (
                    _get_order,
                    ['price_unit', 'tax_id', 'discount', 'product_uom_qty'],
                    10),
            },
            multi='sums',
            help="The amount without tax.",
            track_visibility='always'
        ),
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            domain=[('is_delivery', '=', False)],
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
    }

    def _check_carrier_quotation(self, cr, uid, order, force_carrier_id=None, context=None):
        carrier_obj = self.pool.get('delivery.carrier')

        # check to add or remove carrier_id
        if not order:
            return False
        if all(line.product_id.type == "service" for line in order.website_order_line):
            order.write({'carrier_id': None})
            self.pool['sale.order']._delivery_unset(cr, SUPERUSER_ID, [order.id], context=context)
            return True
        else:
            carrier_id = force_carrier_id or order.carrier_id.id
            carrier_ids = self._get_delivery_methods(cr, uid, order, context=context)
            if carrier_id:
                if carrier_id not in carrier_ids:
                    carrier_id = False
                else:
                    carrier_ids.remove(carrier_id)
                    carrier_ids.insert(0, carrier_id)
            if force_carrier_id or not carrier_id or not carrier_id in carrier_ids:
                for delivery_id in carrier_ids:
                    grid_id = carrier_obj.grid_get(cr, SUPERUSER_ID, [delivery_id], order.partner_shipping_id.id)
                    if grid_id:
                        carrier_id = delivery_id
                        break
                order.write({'carrier_id': carrier_id})
            if carrier_id:
                order.delivery_set()
            else:
                order._delivery_unset()

        return bool(carrier_id)

    def _get_delivery_methods(self, cr, uid, order, context=None):
        carrier_obj = self.pool.get('delivery.carrier')
        delivery_ids = carrier_obj.search(cr, uid, [('website_published','=',True)], context=context)
        # Following loop is done to avoid displaying delivery methods who are not available for this order
        # This can surely be done in a more efficient way, but at the moment, it mimics the way it's
        # done in delivery_set method of sale.py, from delivery module
        for delivery_id in carrier_obj.browse(cr, SUPERUSER_ID, delivery_ids, context=dict(context, order_id=order.id)):
            if not delivery_id.available:
                delivery_ids.remove(delivery_id.id)
        return delivery_ids

    def _get_errors(self, cr, uid, order, context=None):
        errors = super(SaleOrder, self)._get_errors(cr, uid, order, context=context)
        if not self._get_delivery_methods(cr, uid, order, context=context):
            errors.append(('No delivery method available', 'There is no available delivery method for your order'))
        return errors

    def _get_website_data(self, cr, uid, order, context=None):
        """ Override to add delivery-related website data. """
        values = super(SaleOrder, self)._get_website_data(cr, uid, order, context=context)
        # We need a delivery only if we have stockable products
        has_stockable_products = False
        for line in order.order_line:
            if line.product_id.type in ('consu', 'product'):
                has_stockable_products = True
        if not has_stockable_products:
            return values

        delivery_ctx = dict(context, order_id=order.id)
        DeliveryCarrier = self.pool.get('delivery.carrier')
        delivery_ids = self._get_delivery_methods(cr, uid, order, context=context)

        values['deliveries'] = DeliveryCarrier.browse(cr, SUPERUSER_ID, delivery_ids, context=delivery_ctx)
        return values
