from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class l10nFRWebsiteSale(WebsiteSale):

    def _validate_address_values(self, address_values, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, *args, **kwargs
        )

        ResPartnerSudo = request.env['res.partner'].sudo()
        if (
            address_values.get('company_registry') and hasattr(ResPartnerSudo, 'check_vat')
            and 'company_registry' not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new({
                fname: address_values[fname]
                for fname in self._get_vat_validation_fields()
                if fname in address_values
            })
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                invalid_fields.add('company_registry')
                error_messages.append(exception.args[0])

        return invalid_fields, missing_fields, error_messages
