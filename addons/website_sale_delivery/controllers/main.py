# -*- coding: utf-8 -*-
import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
import openerp.addons.website_sale.controllers.main


class website_sale(openerp.addons.website_sale.controllers.main.website_sale):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        order = request.website.sale_get_order(context=context)
        carrier_id = post.get('carrier_id')
        if carrier_id:
            carrier_id = int(carrier_id)
        if order:
            request.registry['sale.order']._check_carrier_quotation(cr, uid, order, force_carrier_id=carrier_id, context=context)
            if carrier_id:
                return request.redirect("/shop/payment")

        res = super(website_sale, self).payment(**post)
        return res

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        order_lines_not_delivery = [line for line in order_lines if not line.is_delivery]
        return super(website_sale, self).order_lines_2_google_api(order_lines_not_delivery)

    def checkout_values(self, data=None):
        cr, uid, context = request.cr, request.uid, request.context
        values = super(website_sale, self).checkout_values(data)

        delivery_carrier_obj = request.registry['delivery.carrier']
        delivery_carrier_ids = delivery_carrier_obj.search(cr, SUPERUSER_ID, [], context=context)
        delivery_carrier = delivery_carrier_obj.browse(cr, SUPERUSER_ID, delivery_carrier_ids, context)

        delivery_grid_obj = request.registry['delivery.grid']
        delivery_grid_ids = delivery_grid_obj.search(cr, SUPERUSER_ID, [], context=context)
        delivery_grid = delivery_grid_obj.browse(cr, SUPERUSER_ID, delivery_grid_ids, context)

        with_pricelist = False
        without_pricelist = False

        for carrier in delivery_carrier:
            if carrier.use_detailed_pricelist and delivery_grid.mapped('country_ids'):
               with_pricelist = True
            if not carrier.use_detailed_pricelist and delivery_carrier.mapped('country_ids'):
                without_pricelist = True

        if with_pricelist or without_pricelist:
            values.update({'countries': list(set(delivery_carrier.mapped('country_ids') + delivery_grid.mapped('country_ids')))})

        return values
