# -*- coding: utf-8 -*-
from openerp.osv import orm


class Website(orm.Model):
    _inherit = 'website'

    def _ecommerce_get_quotation_values(self, cr, uid, context=None):
        """ Override the quotation values generation to add carrier_id data """
        values = super(Website, self)._ecommerce_get_quotation_values(cr, uid, context=context)
        DeliveryCarrier = self.pool.get('delivery.carrier')
        carrier_ids = DeliveryCarrier.search(cr, uid, [], context=context, limit=1)
        # By default, select the first carrier
        if carrier_ids:
            values['carrier_id'] = carrier_ids[0]
        return values

    def _ecommerce_create_quotation(self, cr, uid, context=None):
        order_id = super(Website, self)._ecommerce_create_quotation(cr, uid, context=context)
        self.pool['sale.order'].delivery_set(cr, uid, [order_id], context=context)
        return order_id
