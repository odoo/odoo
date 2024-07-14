# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation


def wa_phone_format(record, fname=False, number=False, country=None,
                    force_format="INTERNATIONAL", raise_exception=True):
    """ Format and return number. This number can be found using a field
    (in which case self should be a singleton recordet), or directly given
    if the formatting itself is what matter.

    :param <Model> record: linked record on which number formatting is
      performed, used to find number and/or country;
    :param str fname: if number is not given, fname indicates the field to
      use to find the number;
    :param str number: number to format (in which case fields-based computation
      is skipped);
    :param <res.country> country: country used for formatting number; otherwise
      it is fetched based on record or company;
    :param str force_format: stringified version of format globals; should be
      one of 'E164', 'INTERNATIONAL', 'NATIONAL' or 'RFC3966';

    :return str: formatted number. Return False is no nmber. If formatting
      fails an exception is raised;
    """
    if not number and record and fname:
        # if no number is given, having a singleton recordset is mandatory to
        # always have a number as input
        record.ensure_one()
        number = record[fname]
    if not number:
        return False

    # fetch country info only if record is a singleton recordset allowing to
    # effectively try to find a country
    if not country and record and 'country_id' in record:
        record.ensure_one()
        country = record.country_id
    if not country:
        country = record.env.company.country_id

    # as 'phone_format' returns original number if parsing fails, we have to
    # let it raise and handle the exception manually to deal with non formatted
    try:
        formatted = phone_validation.phone_format(
            number,
            country.code,
            country.phone_code,
            force_format=force_format if force_format != "WHATSAPP" else "E164",
            raise_exception=True,
        )
    except Exception:  # noqa: BLE001
        if raise_exception:
            raise
        formatted = False

    if formatted and force_format == "WHATSAPP":
        try:
            parsed = phone_validation.phone_parse(formatted, country.code)
        except Exception:  # noqa: BLE001
            if raise_exception:
                raise
            return False
        return f'{parsed.country_code}{parsed.national_number}'
    return formatted
