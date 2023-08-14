import re

from odoo import _
from odoo.exceptions import UserError


def format_partner_address(partner):
    """ Format the partner address to comply with the payload structure of the API request.
    :param res.partner partner: The partner making the payment.
    :return: The formatted partner address.
    :rtype: dict
    """
    STREET_FORMAT = '%(street_number)s/%(street_number2)s %(street_name)s'
    street_data = split_street_with_params(partner.street, STREET_FORMAT)
    return {
        'city': partner.city,
        'country': partner.country_id.code or 'ZZ',  # 'ZZ' if the country is not known.
        'stateOrProvince': partner.state_id.code,
        'postalCode': partner.zip,
        'street': street_data['street_name'],
        'houseNumberOrName': street_data['street_number'],
    }


# The method is copy-pasted from `base_address_extended` with small modifications.
def split_street_with_params(street_raw, street_format):
    street_fields = ['street_name', 'street_number', 'street_number2']
    vals = {}
    previous_pos = 0
    field_name = None
    # iter on fields in street_format, detected as '%(<field_name>)s'
    for re_match in re.finditer(r'%\(\w+\)s', street_format):
        field_pos = re_match.start()
        if not field_name:
            #first iteration: remove the heading chars
            street_raw = street_raw[field_pos:]

        # get the substring between 2 fields, to be used as separator
        separator = street_format[previous_pos:field_pos]
        field_value = None
        if separator and field_name:
            #maxsplit set to 1 to unpack only the first element and let the rest untouched
            tmp = street_raw.split(separator, 1)
            if previous_greedy in vals:
                # attach part before space to preceding greedy field
                append_previous, sep, tmp[0] = tmp[0].rpartition(' ')
                street_raw = separator.join(tmp)
                vals[previous_greedy] += sep + append_previous
            if len(tmp) == 2:
                field_value, street_raw = tmp
                vals[field_name] = field_value
        if field_value or not field_name:
            previous_greedy = None
            if field_name == 'street_name' and separator == ' ':
                previous_greedy = field_name
            # select next field to find (first pass OR field found)
            # [2:-2] is used to remove the extra chars '%(' and ')s'
            field_name = re_match.group()[2:-2]
        else:
            # value not found: keep looking for the same field
            pass
        if field_name not in street_fields:
            raise UserError(_("Unrecognized field %s in street format.", field_name))
        previous_pos = re_match.end()

    # last field value is what remains in street_raw minus trailing chars in street_format
    trailing_chars = street_format[previous_pos:]
    if trailing_chars and street_raw.endswith(trailing_chars):
        vals[field_name] = street_raw[:-len(trailing_chars)]
    else:
        vals[field_name] = street_raw
    return vals
