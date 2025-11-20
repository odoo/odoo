from odoo.http import request

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):

    def _cart_line_data(self, line):
        slug = request.env['ir.http']._slug
        line_data = super()._cart_line_data(line)

        # If the sale order line concerns an event, we want the "product" link to point to
        # the event itself and not to the product on the ecommerce
        if line.event_id:
            line_data['website_url'] = '/event/%s/register' % slug(line.event_id)

        return line_data
