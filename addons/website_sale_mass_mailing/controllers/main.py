# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_mass_mailing.controllers.main import MassMailController
from odoo.addons.website_sale.controllers.main import WebsiteSale as WebsiteSaleController


class WebsiteSale(WebsiteSaleController):

    def _handle_extra_form_data(self, extra_form_data, address_values):
        super()._handle_extra_form_data(extra_form_data, address_values)
        if extra_form_data.get('newsletter') and address_values.get('email'):
            MassMailController.subscribe_to_newsletter(
                subscription_type='email',
                value=address_values['email'],
                list_id=request.website.newsletter_id,
                fname='email',
                address_name=address_values['name'],
            )
