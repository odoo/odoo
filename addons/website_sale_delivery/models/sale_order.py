# -*- coding: utf-8 -*-

from openerp.osv import orm, fields
from openerp import SUPERUSER_ID
from openerp.addons import decimal_precision
from openerp.tools.translate import _


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

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = super(SaleOrder, self)._amount_all(cr, uid, ids, field_name, arg, context=context)
        currency_pool = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            line_amount = sum([line.price_subtotal for line in order.order_line if line.is_delivery])
            currency = order.pricelist_id.currency_id
            res[order.id]['amount_delivery'] = currency_pool.round(cr, uid, currency, line_amount)
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_delivery': fields.function(
            _amount_all_wrapper, type='float', digits_compute=decimal_precision.get_precision('Account'),
            string='Delivery Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'
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
            errors.append(
                (_('Sorry, we are unable to ship your order'),
                 _('No shipping method is available for your current order and shipping address. '
                   'Please contact us for more information.')))
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

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """ Override to update carrier quotation if quantity changed """

        values = super(SaleOrder, self)._cart_update(
            cr, uid, ids, product_id, line_id, add_qty, set_qty, context, **kwargs)

        if add_qty or set_qty is not None:
            for sale_order in self.browse(cr, uid, ids, context=context):
                self._check_carrier_quotation(cr, uid, sale_order, context=context)

        return values
