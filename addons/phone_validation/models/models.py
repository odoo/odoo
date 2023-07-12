# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models
from odoo.addons.phone_validation.tools import phone_validation


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------
    # FIELDS HELPERS
    # ------------------------------------------------------------

    @api.model
    def _phone_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return [
            number_fname for number_fname in ('mobile', 'phone') if number_fname in self
        ]

    @api.model
    def _phone_get_country_field(self):
        if 'country_id' in self:
            return 'country_id'
        return False

    def _phone_format(self, fname=False, number=False, country=False, force_format='E164', raise_exception=False):
        """ Format and return number. This number can be found using a field
        (in which case self should be a singleton recordet), or directly given
        if the formatting itself is what matter. Field name can be found
        automatically using '_phone_get_number_fields'

        :param str fname: if number is not given, fname indicates the field to
          use to find the number; otherwise use '_phone_get_number_fields';
        :param str number: number to format (in which case fields-based computation
          is skipped);
        :param <res.country> country: country used for formatting number; otherwise
          it is fetched based on record, using '_phone_get_country_field';
        :param str force_format: stringified version of format globals; should be
          one of 'E164', 'INTERNATIONAL', 'NATIONAL' or 'RFC3966';
        :param bool raise_exception: raise if formatting is not possible (notably
          wrong formatting, invalid country information, ...). Otherwise False
          is returned;

        :return str: formatted number. If formatting is not possible False is
          returned.
        """
        if not number:
            # if no number is given, having a singletong recordset is mandatory to
            # always have a number as input
            self.ensure_one()
            fnames = self._phone_get_number_fields() if not fname else [fname]
            number = next((self[fname] for fname in fnames if fname in self and self[fname]), False)
        if not number:
            return False

        # fetch country info only if self is a singleton recordset allowing to
        # effectively try to find a country
        if not country and self:
            self.ensure_one()
            country_fname = self._phone_get_country_field()
            country = self[country_fname] if country_fname and country_fname in self else self.env['res.country']
        if not country:
            country = self.env.company.country_id
        if not country:
            return number

        return self._phone_format_number(number, country=country, force_format=force_format, raise_exception=raise_exception)

    def _phone_format_number(self, number, country, force_format='E164', raise_exception=False):
        """ Format and return number according to the asked format. This is
        mainly a small helper around 'phone_validation.phone_format'."""
        if not number or not country:
            return False

        try:
            number = phone_validation.phone_format(
                number,
                country.code,
                country.phone_code,
                force_format=force_format,
                raise_exception=True,  # do not get original number returned
            )
        except exceptions.UserError:
            if raise_exception:
                raise
            number = False
        return number
