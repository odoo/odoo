# -*- coding: utf-8 -*-

import logging
import phonenumbers

from odoo import api, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_mollie_address(self):
        self.ensure_one()
        name_split = self.name.split(' ')
        givenName = name_split[0]
        familyName = self.name.replace(name_split[0], '')
        phone = ''

        """
          Mollie only accepts E164 phone numbers. If the phone number is not in an E164 format Mollie will refuse
          the payment, resulting in Odoo doing a rollback and the user being 'kicked' to the homepage again.
          In this try/except we will do a check for it. If there is no valid phone number we'll give back '' which
          will be accepted by Mollie (no phone number).
        """
        try:
            raw_phone_number = self.phone
            result = phonenumbers.parse(raw_phone_number, None)
            if result:
                phone = phonenumbers.format_number(result, phonenumbers.PhoneNumberFormat.E164)
        except Exception as error:
            _logger.warning('The customer filled in an invalid phone number format. The phone number is not in the '
                            'E164 format which Mollie requires. We will not send it to Mollie.')
            phone = ''

        res = {
            'givenName': givenName,
            'familyName': familyName or givenName,
            'streetAndNumber': "%s %s" % ((self.street or ''), (
                self.street2 or '')),
            'city': self.city or '',
            'postalCode': self.zip or '',
            'country': (self.country_id and
                        self.country_id.code) or 'nl',
            'email': self.email,
            # Will set the phone if there is one, otherwise it gives back '' (no phone)
            'phone': phone or '',
        }
        return res

