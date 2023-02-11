# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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

    @api.onchange("street_format")
    def onchange_street_format(self):
        # Prevent unexpected truncation with whitespaces in front of the street format
        self.street_format = self.street_format.strip()
