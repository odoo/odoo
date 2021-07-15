# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = ['res.partner']

    street_name = fields.Char(
        'Street Name', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number = fields.Char(
        'House', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number2 = fields.Char(
        'Door', compute='_compute_street_data', inverse='_inverse_street_data', store=True)

    def _inverse_street_data(self):
        """Updates the street field.
        Writes the `street` field on the partners when one of the sub-fields in STREET_FIELDS
        has been touched"""
        street_fields = self._get_street_fields()
        for partner in self:
            street_format = (partner.country_id.street_format or
                '%(street_number)s/%(street_number2)s %(street_name)s')
            previous_field = None
            previous_pos = 0
            street_value = ""
            separator = ""
            # iter on fields in street_format, detected as '%(<field_name>)s'
            for re_match in re.finditer(r'%\(\w+\)s', street_format):
                # [2:-2] is used to remove the extra chars '%(' and ')s'
                field_name = re_match.group()[2:-2]
                field_pos = re_match.start()
                if field_name not in street_fields:
                    raise UserError(_("Unrecognized field %s in street format.", field_name))
                if not previous_field:
                    # first iteration: add heading chars in street_format
                    if partner[field_name]:
                        street_value += street_format[0:field_pos] + partner[field_name]
                else:
                    # get the substring between 2 fields, to be used as separator
                    separator = street_format[previous_pos:field_pos]
                    if street_value and partner[field_name]:
                        street_value += separator
                    if partner[field_name]:
                        street_value += partner[field_name]
                previous_field = field_name
                previous_pos = re_match.end()

            # add trailing chars in street_format
            street_value += street_format[previous_pos:]
            partner.street = street_value

    @api.depends('street')
    def _compute_street_data(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a partner is updated"""
        street_fields = self._get_street_fields()
        for partner in self:
            if not partner.street:
                for field in street_fields:
                    partner[field] = None
                continue

            street_format = (partner.country_id.street_format or
                '%(street_number)s/%(street_number2)s %(street_name)s')
            street_raw = partner.street
            vals = self._split_street_with_params(street_raw, street_format)
            # assign the values to the fields
            for k, v in vals.items():
                partner[k] = v
            for k in set(street_fields) - set(vals):
                partner[k] = None

    def _split_street_with_params(self, street_raw, street_format):
        street_fields = self._get_street_fields()
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

    def write(self, vals):
        res = super(Partner, self).write(vals)
        if 'country_id' in vals and 'street' not in vals:
            self._inverse_street_data()
        return res

    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super(Partner, self)._formatting_address_fields() + self._get_street_fields()

    def _get_street_fields(self):
        """Returns the fields that can be used in a street format.
        Overwrite this function if you want to add your own fields."""
        return ['street_name', 'street_number', 'street_number2']
