# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models
from odoo.addons.phone_validation.tools import phone_validation


class Base(models.AbstractModel):
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

        - The country field of the target record (self) based on
          :meth:`_phone_get_country_field`;
        - The country of any mail partner (e.g. ``self.partner_ids[2].phone``),
          considering we are going to contact the customer(s) of the record.
          Done using generic :meth:`_mail_get_partner_fields` method allowing
          to find record customers;
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
        automatically using :meth:`_phone_get_number_fields`.

        :param str fname: if number is not given, fname indicates the field to
          use to find the number; otherwise use :meth:`_phone_get_number_fields`.;
        :param str number: number to format (in which case fields-based computation
          is skipped);
        :param <res.country> country: country used for formatting number; otherwise
          it is fetched based on record, using :meth:`_phone_get_number_fields`.;
        :param str force_format: stringified version of format globals; should be
          one of ``'E164'``, ``'INTERNATIONAL'``, ``'NATIONAL'`` or ``'RFC3966'``;
        :param bool raise_exception: raise if formatting is not possible (notably
          wrong formatting, invalid country information, ...). Otherwise ``False``
          is returned;

        :return: formatted number. If formatting is not possible ``False`` is
          returned.
        :rtype: str | Literal[False]
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
        mainly a small helper around :func:`phone_validation.phone_format`."""
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

    # ------------------------------------------------------------
    # RECIPIENT HELPERS
    # ------------------------------------------------------------

    def _phone_get_recipients_info(self, force_field=False, partner_fallback=True):
        """ Get recipient phone related information on current record set. This method
        checks for numbers and sanitation in order to centralize computation.

        Example of use cases

          * click on a field -> number is actually forced from field, find customer
            linked to record, force its number to field or fallback on customer fields;
          * contact -> find numbers from all possible phone fields on record, find
            customer, force its number to found field number or fallback on customer fields;

        :param force_field: either give a specific field to find phone number, either
            generic heuristic is used to find one based on :meth:`_phone_get_number_fields`;
        :param partner_fallback: if no value found in the record, check its customer
            values based on :meth:`_mail_get_partners`;

        :rtype: dict[int, dict[str, Any]]
        :return: a dictionnary with the following structure:

            .. code-block:: python

                {
                    record.id: {
                        # a res.partner recordset that is the customer (void or
                        # singleton) linked to the recipient.
                        # See _mail_get_partners;
                        'partner': ...,

                        # sanitized number to use (coming from record's field
                        # or partner's phone fields). Set to False if number
                        # impossible to parse and format;
                        'sanitized': ...,

                        # original number before sanitation;
                        'number': ...,

                        # whether the number comes from the customer phone
                        # fields. If False it means number comes from the
                        # record itself, even if linked to a customer;
                        'partner_store': ...,

                        # field in which the number has been found (generally
                        # mobile or phone, see _phone_get_number_fields);
                        'field_store': ...,
                    }
                    for record in self
                }

        """
        result = dict.fromkeys(self.ids, False)
        tocheck_fields = [force_field] if force_field else self._phone_get_number_fields()
        all_partners_by_record = self._mail_get_partners()
        for record in self:
            all_numbers = [record[fname] for fname in tocheck_fields if fname in record]
            all_partners = all_partners_by_record[record.id]

            valid_number, fname = False, False
            for fname in [f for f in tocheck_fields if f in record]:
                valid_number = record._phone_format(fname=fname)
                if valid_number:
                    break

            if valid_number:
                result[record.id] = {
                    'partner': all_partners[0] if all_partners else self.env['res.partner'],
                    'sanitized': valid_number,
                    'number': record[fname],
                    'partner_store': False,
                    'field_store': fname,
                }
            elif all_partners and partner_fallback:
                partner = self.env['res.partner']
                for partner in all_partners:
                    for fname in self.env['res.partner']._phone_get_number_fields():
                        valid_number = partner._phone_format(fname=fname)
                        if valid_number:
                            break
                    if valid_number:
                        break

                if not valid_number:
                    fname = 'phone'

                result[record.id] = {
                    'partner': partner,
                    'sanitized': valid_number if valid_number else False,
                    'number': partner[fname],
                    'partner_store': True,
                    'field_store': fname,
                }
            else:
                # did not find any sanitized number -> take first set value as fallback;
                # if none, just assign False to the first available number field
                value, fname = next(
                    ((value, fname) for value, fname in zip(all_numbers, tocheck_fields) if value),
                    (False, tocheck_fields[0] if tocheck_fields else False)
                )
                result[record.id] = {
                    'partner': self.env['res.partner'],
                    'sanitized': False,
                    'number': value,
                    'partner_store': False,
                    'field_store': fname,
                }
        return result
