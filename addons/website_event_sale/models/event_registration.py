# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_website_registration_allowed_fields(self):
        # values are validated against the ticket options by the controller
        return super()._get_website_registration_allowed_fields() | {'ticket_option_product_ids'}
