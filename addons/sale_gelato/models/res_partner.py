# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.sale_gelato import const


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _gelato_validate_address(self):
        """Check that all required address fields are set and of correct length.

        :rtype: None
        :raise ValidationError: If the address is incomplete or too long.
        """
        self._gelato_ensure_address_is_complete()
        self._gelato_check_address_length_limit()

    def _gelato_ensure_address_is_complete(self):
        """Ensure that all address fields required by Gelato are set.

        :rtype: None
        :raise ValidationError: If the address is incomplete.
        """
        required_address_fields = ['city', 'country_id', 'email', 'name', 'street']
        if self.country_id.code not in const.COUNTRIES_WITHOUT_ZIPCODE:
            required_address_fields.append('zip')
        missing_fields = [
            self._fields[field_name]
            for field_name in required_address_fields
            if not self[field_name]
        ]
        if missing_fields:
            translated_field_names = [f._description_string(self.env) for f in missing_fields]
            raise ValidationError(_(
                "The following required address fields are missing: %s",
                ", ".join(translated_field_names),
            ))

    def _gelato_check_address_length_limit(self):
        """Check that the address fields are compliant with Gelato maximum character limit.

        :rtype: None
        :raise ValidationError: If the address fields are too long.
        """
        max_address_lengths = {'street': 35, 'street2': 35, 'city': 30, 'zip': 15, 'phone': 25}
        exceeding_fields = {}
        for field, limit in max_address_lengths.items():
            if self[field] and len(self[field]) > limit:
                field_name = self._fields[field]._description_string(self.env)
                exceeding_fields[field_name] = limit
        if exceeding_fields:
            message = ", ".join([
                f"{field_name} (max {limit} characters)"
                for field_name, limit in exceeding_fields.items()
            ])
            raise ValidationError(_("The following address fields are too long: %s", message))

    def _gelato_prepare_address_payload(self):
        """Prepare the address payload with the partner details.

        The fields that are not strictly required to be unchanged for the delivery are trimmed to
        their maximum length allowed by Gelato.

        :return: The address payload with the partner details.
        :rtype: dict
        """
        first_name, last_name = payment_utils.split_partner_name(self.name)
        return {
            'companyName': (self.commercial_company_name or '')[:60],
            'firstName': (first_name or last_name)[:25],  # Gelato requires a first name.
            'lastName': last_name[:25],
            'addressLine1': self.street,
            'addressLine2': self.street2,
            'state': self.state_id.code,
            'city': self.city,
            'postCode': self.zip,
            'country': self.country_id.code,
            'email': self.email,
            'phone': self.phone or ''
        }
