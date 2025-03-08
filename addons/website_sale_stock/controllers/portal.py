# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal


class WebsiteSaleStockCustomerPortal(CustomerPortal):

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        """
            Extends address validation to prevent modifications
            if the partner has delivery notes in certain states.

            Args:
                address_values (dict): Address values.
                partner_sudo (recordset): Partner with elevated permissions.
                address_type (str): Address type.
                *args, **kwargs: Additional arguments.

            Returns:
                tuple: (invalid_fields, missing_fields, error_messages).
        """
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        if partner_sudo and not partner_sudo._can_edit_address():
            error_messages.append(_('Address cannot be edited because there are pending stock operations. '
                                    'Please contact us directly for this operation.'))

        return invalid_fields, missing_fields, error_messages
