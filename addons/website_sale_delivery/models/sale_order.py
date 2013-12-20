# -*- coding: utf-8 -*-

from openerp.osv import orm, fields


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

    _columns = {
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            domain=[('is_delivery', '=', False)],
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
    }

    def _add_delivery(self, cr, uid, order, context=None):
        pass

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
        delivery_ids = DeliveryCarrier.search(cr, uid, [], context=context)
        values['deliveries'] = DeliveryCarrier.browse(cr, uid, delivery_ids, context=delivery_ctx)
        return values
