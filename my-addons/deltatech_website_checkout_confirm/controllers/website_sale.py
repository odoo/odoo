from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleCheckout(WebsiteSale):
    @http.route(["/shop/confirmation"], type="http", auth="public", website=True, sitemap=False)
    def payment_confirmation(self, **post):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            order = request.env["sale.order"].sudo().browse(sale_order_id)
            order.action_confirm()
        return super(WebsiteSaleCheckout, self).payment_confirmation(**post)

    # @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    # def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
    #     if sale_order_id is None:
    #         order = request.website.sale_get_order()
    #     else:
    #         order = request.env['sale.order'].sudo().browse(sale_order_id)
    #         assert order.id == request.session.get('sale_last_order_id')
    #     order.action_confirm()
    #     return super(WebsiteSaleCheckout, self).payment_validate(**post)
