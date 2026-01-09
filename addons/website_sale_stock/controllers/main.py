# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import LockNotAvailable
from werkzeug.exceptions import BadRequest

from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import email_re
from odoo.tools.misc import mute_logger
from odoo.tools.sql import SQL

from odoo.addons.website_sale.controllers import main as website_sale_controller


class WebsiteSale(website_sale_controller.WebsiteSale):
    @http.route(['/shop/add/stock_notification'], type="json", auth="public", website=True)
    def add_stock_email_notification(self, email, product_id):
        if not email_re.match(email):
            raise BadRequest(_("Invalid Email"))

        product = request.env['product.product'].browse(int(product_id))
        partners = request.env['res.partner'].sudo()._mail_find_partner_from_emails([email], force_create=True)
        partner = partners[0]

        if not product._has_stock_notification(partner):
            product.sudo().stock_notification_partner_ids += partner

        if request.website.is_public_user():
            request.session['product_with_stock_notification_enabled'] = request.session.get(
                'product_with_stock_notification_enabled',
                set()
            ) | {product_id}
            request.session['stock_notification_email'] = email

    def _prepare_product_values(self, product, category='', search='', **kwargs):
        values = super()._prepare_product_values(product, category, search, **kwargs)
        # We need the user mail to prefill the back of stock notification, so we put it in the value that will be sent
        values['user_email'] = request.env.user.email or request.session.get('stock_notification_email', '')
        return values

class CustomerPortal(website_sale_controller.CustomerPortal):
    def _sale_reorder_get_line_context(self):
        return {
            **super()._sale_reorder_get_line_context(),
            'website_sale_stock_get_quantity': True,
        }


class PaymentPortal(website_sale_controller.PaymentPortal):
    def _validate_transaction_for_order(self, transaction, sale_order_id):
        """
        Throws a ValidationError if the free quantity of a product in the cart
        is being updated to 0 by a concurrent transaction and allow_out_of_stock_order
        is set to False.
        """
        super()._validate_transaction_for_order(transaction, sale_order_id)
        sale_order = request.env['sale.order'].browse(sale_order_id).exists()
        website = sale_order.website_id
        restricted_products = request.env['product.product']
        for product in sale_order.order_line.product_id:
            if not product.allow_out_of_stock_order and (website._get_product_available_qty(product) - product._get_cart_qty(website) <= 0):
                restricted_products |= product
        if restricted_products:
            ctx = {**request.env.context, 'warehouse': website._get_warehouse_available()}
            quants_location_domain, __, __ = restricted_products.with_context(ctx)._get_domain_locations()
            quants_domain = expression.AND([[('product_id', 'in', restricted_products.ids)], quants_location_domain])
            query = request.env['stock.quant'].sudo()._search(quants_domain).select()
            # Try to acquire a lock on stock.quants, throw an error if lock not available.
            query = SQL('%s FOR NO KEY UPDATE NOWAIT', query)
            try:
                with mute_logger('odoo.sql_db'):
                    request.env.cr.execute(query)
            except LockNotAvailable:
                raise ValidationError(_("Cannot process payment: the cart contains products that are currently out of stock."))
