# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class AddressMixin(models.Model):
    _inherit = ['address.mixin']

    street_name = fields.Char(
        'Street Name', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number = fields.Char(
        'House', compute='_compute_street_data', inverse='_inverse_street_data', store=True)
    street_number2 = fields.Char(
        'Door', compute='_compute_street_data', inverse='_inverse_street_data', store=True)

    country_extended_address = fields.Boolean(related='country_id.extended_address')

    # todo: use _inverse_street and _compute_street
    def _inverse_street_data(self):
        """ update self.street based on street_name, street_number and street_number2 """
        for address in self:
            street = ((address.street_name or '') + " " + (address.street_number or '')).strip()
            if address.street_number2:
                street = street + " - " + address.street_number2
            address.street = street

    @api.depends('street')
    def _compute_street_data(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a address is updated"""
        for address in self:
            address.update(tools.street_split(address.street))

    def _get_street_split(self):
        self.ensure_one()
        return {
            'street_name': self.street_name,
            'street_number': self.street_number,
            'street_number2': self.street_number2
        }
