# -*- coding: utf-8 -*-
import logging

from openerp.osv import orm, fields
from openerp import SUPERUSER_ID
from openerp.addons import decimal_precision
from openerp.exceptions import ValidationError
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)


class delivery_carrier(orm.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.mixin']

    _columns = {
        'website_description': fields.related('product_id', 'description_sale', type="text", string='Description for Online Quotations'),
    }
    _defaults = {
        'website_published': False
    }


class SaleOrder(orm.Model):
    _inherit = 'sale.order'

    def _amount_delivery(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {}
            res[order.id]['amount_delivery'] = sum([line.price_subtotal for line in order.order_line if line.is_delivery])
        return res

    def _has_delivery(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, False)
        for so in self.browse(cr, uid, ids, context=context):
            for line in so.order_line:
                if line.is_delivery:
                    result[so.id] = True
                    break
        return result

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_delivery': fields.function(
            _amount_delivery, type='float', digits=0,
            string='Delivery Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'
        ),
        'has_delivery': fields.function(
            _has_delivery, type='boolean', string='Has delivery',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            help="Has an order line set for delivery"
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
        if all(line.product_id.type in ("service", "digital") for line in order.website_order_line):
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
                    carrier = carrier_obj.verify_carrier(cr, SUPERUSER_ID, [delivery_id], order.partner_shipping_id)
                    if carrier:
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
        carrier_ids = carrier_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True)], context=context)
        available_carrier_ids = []
        # Following loop is done to avoid displaying delivery methods who are not available for this order
        # This can surely be done in a more efficient way, but at the moment, it mimics the way it's
        # done in delivery_set method of sale.py, from delivery module

        new_context = dict(context, order_id=order.id)
        for carrier in carrier_ids:

            try:
                _logger.debug("Checking availability of carrier #%s" % carrier)
                available = carrier_obj.read(cr, SUPERUSER_ID, [carrier], fields=['available'], context=new_context)[0]['available']
                if available:
                    available_carrier_ids = available_carrier_ids + [carrier]
            except ValidationError as e:
                # RIM: hack to remove in master, because available field should not depend on a SOAP call to external shipping provider
                # The validation error is used in backend to display errors in fedex config, but should fail silently in frontend
                _logger.debug("Carrier #%s removed from e-commerce carrier list. %s" % (carrier, e))

        return available_carrier_ids

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

    def _get_shipping_country(self, cr, uid, values, context=None):
        country_ids = set()
        state_ids = set()
        values['shipping_countries'] = values['countries']
        values['shipping_states'] = values['states']

        DeliveryCarrier = self.pool['delivery.carrier']
        delivery_carrier_ids = DeliveryCarrier.search(cr, SUPERUSER_ID, [('website_published', '=', True)], context=context)
        for carrier in DeliveryCarrier.browse(cr, SUPERUSER_ID, delivery_carrier_ids, context):
            if not carrier.country_ids and not carrier.state_ids:
                return values
            # Authorized shipping countries
            country_ids = country_ids|set(carrier.country_ids.ids)
            # Authorized shipping countries without any state restriction
            state_country_ids = [country.id for country in carrier.country_ids if country.id not in carrier.state_ids.mapped('country_id.id')]
            # Authorized shipping states + all states from shipping countries without any state restriction
            state_ids = state_ids|set(carrier.state_ids.ids)|set(values['states'].filtered(lambda r: r.country_id.id in state_country_ids).ids)

        values['shipping_countries'] = values['countries'].filtered(lambda r: r.id in list(country_ids))
        values['shipping_states'] = values['states'].filtered(lambda r: r.id in list(state_ids))
        return values
