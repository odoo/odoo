from odoo import http
from odoo.http import request

class EstateWebsite(http.Controller):
    @http.route('/properties', auth='public', website=True)
    def list_properties(self, **kwargs):
        properties = request.env['estate.property'].sudo().search([])
        return request.render('estate.estate_property_website_template', {
            'properties': properties
        })
