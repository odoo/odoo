# -*- coding: utf-8 -*-

from openerp.osv import orm, fields
from openerp import SUPERUSER_ID
from openerp.addons import decimal_precision


class delivery_carrier(orm.Model):
    _inherit = 'delivery.carrier'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
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
        delivery_ids = DeliveryCarrier.search(cr, uid, [('website_published','=',True)], context=context)
        values['deliveries'] = DeliveryCarrier.browse(cr, SUPERUSER_ID, delivery_ids, context=delivery_ctx)
        return values
