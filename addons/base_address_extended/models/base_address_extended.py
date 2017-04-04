# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


STREET_FIELDS = ('street_name', 'street_number', 'street_number2')


class ResCountry(models.Model):
    _inherit = 'res.country'

    street_format = fields.Text(
        help="Format to use for streets belonging to this country.\n\n"
             "You can use the python-style string pattern with all the fields of the street "
             "(for example, use '%(street_name)s, %(street_number)s' if you want to display "
             "the street name, followed by a comma and the house number)"
             "\n%(street_name)s: the name of the street"
             "\n%(street_number)s: the house number"
             "\n%(street_number2)s: the door number",
        default='%(street_number)s/%(street_number2)s %(street_name)s', required=True)

class Partner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    street_name = fields.Char('Street Name', compute='_split_street',
                              inverse='_set_street', store=True)
    street_number = fields.Char('House Number', compute='_split_street',
                                inverse='_set_street', store=True)
    street_number2 = fields.Char('Door Number', compute='_split_street',
                                 inverse='_set_street', store=True)

    def get_street_fields(self):
        """Returns the fields that can be used in a street format.
        Overwrite this function if you want to add your own fields."""
        return STREET_FIELDS

    @api.multi
    def _set_street(self):
        """Updates the street field.
        Writes the `street` field on the partners when one of the sub-fields in STREET_FIELDS
        has been touched"""
        street_fields = self.get_street_fields()
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
                    raise UserError(_("Unrecognized field %s in street format.") % field_name)
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

            # /!\ Note that we must use a sql query to bypass the orm as it would call _split_street()
            # that would try to set the fields we just modified.
            self._cr.execute('UPDATE res_partner SET street = %s WHERE ID = %s', (street_value, partner.id))
            #invalidate the cache for the field we manually set
            self.invalidate_cache(['street'], [partner.id])

    @api.multi
    @api.depends('street')
    def _split_street(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a partner is updated"""
        street_fields = self.get_street_fields()
        for partner in self:
            if not partner.street:
                for field in street_fields:
                    partner[field] = ''
                continue

            street_format = (partner.country_id.street_format or
                '%(street_number)s/%(street_number2)s %(street_name)s')
            vals = {}
            previous_pos = 0
            street_raw = partner.street
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
                    if len(tmp) == 2:
                        field_value, street_raw = tmp
                        vals[field_name] = field_value
                if field_value or not field_name:
                    # select next field to find (first pass OR field found)
                    # [2:-2] is used to remove the extra chars '%(' and ')s'
                    field_name = re_match.group()[2:-2]
                else:
                    # value not found: keep looking for the same field
                    pass
                if field_name not in street_fields:
                    raise UserError(_("Unrecognized field %s in street format.") % field_name)
                previous_pos = re_match.end()

            # last field value is what remains in street_raw minus trailing chars in street_format
            trailing_chars = street_format[previous_pos:]
            if trailing_chars and street_raw.endswith(trailing_chars):
                vals[field_name] = street_raw[:-len(trailing_chars)]
            else:
                vals[field_name] = street_raw
            # assign the values to the fields
            # /!\ Note that a write(vals) would cause a recursion since it would bypass the cache
            for k, v in vals.items():
                partner[k] = v


class Company(models.Model):
    _inherit = 'res.company'

    street_name = fields.Char('Street Name', compute='_compute_address',
                              inverse='_inverse_street_name')
    street_number = fields.Char('House Number', compute='_compute_address',
                                inverse='_inverse_street_number')
    street_number2 = fields.Char('Door Number', compute='_compute_address',
                                 inverse='_inverse_street_number2')

    def _get_company_address_fields(self, partner):
        address_fields = super(Company, self)._get_company_address_fields(partner)
        address_fields.update({
            'street_name': partner.street_name,
            'street_number': partner.street_number,
            'street_number2': partner.street_number2,
        })
        return address_fields

    def _inverse_street_name(self):
        for company in self:
            company.partner_id.street_name = company.street_name

    def _inverse_street_number(self):
        for company in self:
            company.partner_id.street_number = company.street_number

    def _inverse_street_number2(self):
        for company in self:
            company.partner_id.street_number2 = company.street_number2
