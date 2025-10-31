from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request


class L10nMAPortalAccount(PortalAccount):

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(address_values, partner_sudo, address_type, *args, **kwargs)
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        if country and country.code == 'MA':
            ice_number = address_values.get('company_registry')
            if ice_number and (len(ice_number) != 15 or not ice_number.isdigit()):
                invalid_fields.update({'company_registry'})
                error_messages.append(request.env._("ICE number should consist of 15 digits."))
        return invalid_fields, missing_fields, error_messages
