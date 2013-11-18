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

class sale_order(orm.Model):
    _inherit = 'sale.order'
    def _get_website_data(self, cr, uid, order, context=None):

        # We need a delivery only if we have stockable products
        todo = False
        for line in order.order_line:
            if line.product_id.type in ('consu','product'):
                todo = True
        if not todo: return {'deliveries': []}

        carrier_obj = self.pool.get('delivery.carrier')
        dids = carrier_obj.search(cr, uid, [], context=context)
        context['order_id'] = order.id
        deliveries = carrier_obj.browse(cr, uid, dids, context=context)

        # By default, select the first carrier
        if not order.carrier_id and dids:
            self.pool.get('sale.order').write(cr, uid, [order.id], {'carrier_id': dids[0]}, context=context)

        # recompute delivery costs
        self.pool.get('sale.order').delivery_set(cr, uid, [order.id], context=context)
        return {'deliveries': deliveries}
