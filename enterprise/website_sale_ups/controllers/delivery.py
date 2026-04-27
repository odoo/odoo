from odoo.http import request

from odoo.addons.website_sale.controllers import delivery


class Delivery(delivery.Delivery):

    def _get_additional_delivery_context(self):
        return {'order': request.website.sale_get_order()}
