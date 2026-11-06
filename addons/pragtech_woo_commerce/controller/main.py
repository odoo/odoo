# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WoocommerceController(http.Controller):

    @http.route(['/woocommerce_order_create'], type='json', auth='public', csrf=False)
    def woocommerce_order_create(self, **kwargs):
        data = request.get_json_data()
        request.env['sale.order'].sudo().woo_order_create(data)

    @http.route(['/woocommerce_order_update'], type='json', auth='public', csrf=False)
    def woocommerce_order_update(self, **kwargs):
        data = request.get_json_data()
        request.env['sale.order'].sudo().woo_order_update(data)

    @http.route(['/woocommerce_product_create'], type='json', auth='public', csrf=False, )
    def woocommerce_product_create(self, **kwargs):
        product_data = request.get_json_data()
        request.env['product.template'].sudo().woo_import_product(product_data)

    @http.route(['/woocommerce_customer_create'], type='json', auth='public', csrf=False, )
    def woocommerce_customer_create(self, **kwargs):
        customer_data = request.get_json_data()
        request.env['res.partner'].sudo().woo_import_customer(customer_data)
