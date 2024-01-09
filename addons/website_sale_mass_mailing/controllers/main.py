# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_mass_mailing.controllers.main import MassMailController
from odoo.addons.website_sale.controllers.main import WebsiteSale as WebsiteSaleController


class WebsiteSale(WebsiteSaleController):

    def _post_process_additional_values(self, address_values, form_values):
        super()._post_process_additional_values(
            address_values=address_values, form_values=form_values
        )

        if (
            form_values.get('newsletter')
            and address_values.get('email')
        ):
            MassMailController.subscribe_to_newsletter(
                subscription_type='email',
                value=address_values['email'],
                list_id=request.website.newsletter_id,
                fname='email',
                address_name=address_values['name'],
            )
