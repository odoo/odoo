# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)
_phonenumbers_lib_warning = False


try:
    import phonenumbers

    def phone_parse(number, country_code):
        try:
            phone_nbr = phonenumbers.parse(number, region=country_code or None, keep_raw_input=True)
        except phonenumbers.phonenumberutil.NumberParseException as e:
            raise UserError(
                _('Unable to parse %(phone)s: %(error)s', phone=number, error=str(e))
            ) from e

        if not phonenumbers.is_possible_number(phone_nbr):
            raise UserError(_('Impossible number %s: probably invalid number of digits.', number))
        if not phonenumbers.is_valid_number(phone_nbr):
            raise UserError(_('Invalid number %s: probably incorrect prefix.', number))

        return phone_nbr

    def phone_format(number, country_code, country_phone_code, force_format='INTERNATIONAL', raise_exception=True):
        """ Format the given phone number according to the localisation and international options.
        :param number: number to convert
        :param country_code: the ISO country code in two chars
        :type country_code: str
        :param country_phone_code: country dial in codes, defined by the ITU-T (Ex: 32 for Belgium)
        :type country_phone_code: int
        :param force_format: stringified version of format globals (see
          https://github.com/daviddrysdale/python-phonenumbers/blob/dev/python/phonenumbers/phonenumberutil.py)
            'E164' = 0
            'INTERNATIONAL' = 1
            'NATIONAL' = 2
            'RFC3966' = 3
        :type force_format: str
        :rtype: str
        """
        try:
            phone_nbr = phone_parse(number, country_code)
        except UserError:
            if raise_exception:
                raise
            return number
        if force_format == 'E164':
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
        elif force_format == 'RFC3966':
            phone_fmt = phonenumbers.PhoneNumberFormat.RFC3966
        elif force_format == 'INTERNATIONAL' or phone_nbr.country_code != country_phone_code:
            phone_fmt = phonenumbers.PhoneNumberFormat.INTERNATIONAL
        else:
            phone_fmt = phonenumbers.PhoneNumberFormat.NATIONAL
        return phonenumbers.format_number(phone_nbr, phone_fmt)

except ImportError:

    def phone_parse(number, country_code):
        return False

    def phone_format(number, country_code, country_phone_code, force_format='INTERNATIONAL', raise_exception=True):
        global _phonenumbers_lib_warning
        if not _phonenumbers_lib_warning:
            _logger.info(
                "The `phonenumbers` Python module is not installed, contact numbers will not be "
                "verified. Please install the `phonenumbers` Python module."
            )
            _phonenumbers_lib_warning = True
        return number
