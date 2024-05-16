# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_mass_mailing.controllers.main import MassMailController
from odoo.addons.website_sale.controllers.main import WebsiteSale as WebsiteSaleController


class WebsiteSale(WebsiteSaleController):

    @route()
    def address(self, **kw):
        if 'submitted' in kw and kw.get('newsletter') and request.httprequest.method == 'POST':
            MassMailController.subscribe_to_newsletter(
                subscription_type='email',
                value=kw['email'],
                list_id=request.website.newsletter_id,
                fname='email',
            )
        return super().address(**kw)
