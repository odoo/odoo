from odoo import http
from odoo.http import request

class WebsiteSort(http.Controller):
    @http.route('/', type='http', auth='public', website=True)
    def index(self, **kw):
        products = request.env['product.template'].sudo().search([], order='sales_count desc', limit=6)
        return request.render('website.homepage', {'website_product_ids': products})