# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _


STREET_FIELDS = ('street_name', 'street_number', 'street_number2')


class ResCountry(models.Model):
    _inherit = 'res.country'

    street_format = fields.Text(help="""You can state here the usual format to use for the \
streets belonging to this country.\n\nYou can use the python-style string patern with all the field of the street \
(for example, use '%(street_name)s, %(street_number)s' if you want to display the street name, followed by a coma and the house number)
            \n%(street_name)s: the name of the street
            \n%(street_number)s: the house number
            \n%(street_number2)s: the door number""",
            default='%(street_number)s/%(street_number2)s %(street_name)s', required=True)


class Partner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    street_name = fields.Char('Street Name', compute='_split_street', inverse='_set_street', store=True)
    street_number = fields.Char('House Number', compute='_split_street', inverse='_set_street', store=True)
    street_number2 = fields.Char('Door Number', compute='_split_street', inverse='_set_street', store=True)


    def get_street_fields(self):
        """Returns the fields that can be used in a street format. Overwrite this function if you want to add your own fields."""
        return STREET_FIELDS

    @api.multi
    def _set_street(self):
        """Write the street field on the partners when one of the fields in STREET_FIELDS has been touched"""
        for partner in self:
            street_format = partner.country_id.street_format or '%(street_number)s/%(street_number2)s %(street_name)s'
            street_vals = {field: getattr(partner, field) for field in self.get_street_fields()}
            partner.street = street_format % street_vals

    @api.multi
    @api.depends('street', 'country_id.street_format')
    def _split_street(self):
        """Recompute the fields of STREET_FIELDS when a write is made on the street of a partner"""
        for partner in self:
            if not partner.street:
                partner.street_name = ''
                partner.street_number = ''
                partner.street_number2= ''
                continue

            street_format = partner.country_id.street_format or '%(street_number)s/%(street_number2)s %(street_name)s'
            vals = {}
            previous_pos = 0
            street_raw = partner.street
            field_name = None
            #iter on fields in street_format, detected as '%(' + <field_name> + ')s'
            for re_match in re.finditer('\\%\\(\w+\\)s', street_format):
                field_pos = re_match.start()
                #get the substring between 2 fields to split street_raw and isolate the value of a field
                splitting_string = street_format[previous_pos:field_pos]
                skip_field = False
                if splitting_string and field_name:
                    #maxsplit set to 1 to unpack only the first element and let the rest untouched
                    tmp = street_raw.split(splitting_string, 1)
                    if len(tmp) > 1:
                        field_value, street_raw = tmp
                        vals[field_name] = field_value
                    else:
                        #manage optional fields: if the field is not found, we skip it and the next value will
                        #be assigned to the previous field instead of this one.
                        skip_field = True
                if not skip_field:
                    #[2:-2] is used to remove the extra chars ['%', '(', ')', 's']
                    field_name = re_match.group()[2:-2]
                if field_name not in self.get_street_fields():
                    raise UserError(_("Unrecognized field %s in street format.") % (field_name))
                previous_pos = re_match.end()

            #the last field value is what remains in street_format minus eventual trailing chars in street_format
            vals[field_name] = street_raw.rstrip(street_format[previous_pos:])
            #assign the values to the fields. Note that a write(vals) would cause a recursion since it would bypass the cache
            for k, v in vals.items():
                setattr(partner, k, v)
