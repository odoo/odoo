# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalProfile(CustomerPortal):

    def _validate_address_values(self, address_values, partner_sudo, *args, **kwargs):
        """Overide to hide email validated button if changed on current partner."""
        if (
            partner_sudo == self.env.user.partner_id
            and 'email' in address_values
            and address_values['email'] != partner_sudo.email
        ):
            request.session['validation_email_sent'] = False

        return super()._validate_address_values(address_values, partner_sudo, *args, **kwargs)
