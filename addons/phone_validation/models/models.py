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

    def _phone_get_country(self):
        """Get a country likely to match the phone of the record.

        By default we get it from:
        - The country field of the target record (self) based on `_phone_get_country_field`
        - The country of any mail partner (e.g. self.partner_ids[2].phone), considering we are
          going to contact the customer(s) of the record. Done using generic
          `_mail_get_partner_fields` method allowing to find record customers;
        """
        country_by_record = {}
        record_country_fname = self._phone_get_country_field()
        for record in self:
            if record_country_fname and (record_country := record[record_country_fname]):
                country_by_record[record.id] = record_country
                continue
            for partner_field in self.env[self._name]._mail_get_partner_fields():
                partner_records = record[partner_field]
                if countries := partner_records.country_id:
                    country_by_record[record.id] = countries[0]
        return country_by_record

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
            country = self._phone_get_country().get(self.id)
        if not country:
            country = self.env.company.country_id

        return self._phone_format_number(
            number,
            country=country, force_format=force_format,
            raise_exception=raise_exception,
        )

    def _phone_format_number(self, number, country, force_format='E164', raise_exception=False):
        """ Format and return number according to the asked format. This is
        mainly a small helper around 'phone_validation.phone_format'."""
        if not number:
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
