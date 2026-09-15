from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_mass_mailing.controllers.main import MassMailController
from odoo.addons.website_sale.controllers.main import (
    WebsiteSale as WebsiteSaleController,
)

_debug = DebugLog(__name__)


class WebsiteSale(WebsiteSaleController):
    def _handle_extra_form_data(self, extra_form_data, address_values):
        super()._handle_extra_form_data(extra_form_data, address_values)
        if extra_form_data.get("newsletter") and address_values.get("email"):
            _debug.lifecycle(
                "newsletter_opt_in_at_checkout",
                list_id=request.website.newsletter_id,
            )
            MassMailController.subscribe_to_newsletter(
                subscription_type="email",
                value=address_values["email"],
                list_id=request.website.newsletter_id,
                fname="email",
                address_name=address_values["name"],
            )
