# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models

address_pattern = re.compile('^(.*?),? ([0-9]+[a-zA-Z]*)([ -]+([0-9]+[a-zA-Z]*))?[ ]*$')


class ResCountryStateCity(models.Model):
    _name = 'res.country.state.city'
    _order = 'name'

    name = fields.Char('City Name', required=True)
    state_id = fields.Many2one('res.country.state', 'State', required=True)
    country_id = fields.Many2one('res.country', 'Country', related='state_id.country_id', store=True, readonly=True)
    code = fields.Char('Code')


class PartnerAddress(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    street_raw = fields.Char('Street')
    street_number1 = fields.Char('Street Number')
    street_number2 = fields.Char('Door Number')
    street = fields.Char('Street', compute='_compute_street', inverse='_compute_street_inverse', store=True)

    city_id = fields.Many2one('res.country.state.city', 'City')
    city = fields.Char('City', related='city_id.name', store=True)

    @api.multi
    def _compute_street_inverse(self):
        for partner in self:
            result = address_pattern.match(partner.street)
            if result and not (partner.street_raw or partner.street_number1 or partner.street_number2):
                partner.street_raw = result.group(1)
                partner.street_number1 = result.group(2)
                partner.street_number2 = result.group(4)

    @api.model
    def _address_fields(self):
        return super(PartnerAddress, self)._address_fields() + ['street_raw', 'street_number1', 'street_number2', 'city_id']

    @api.multi
    @api.depends('street_raw', 'street_number1', 'street_number2')
    def _compute_street(self):
        for partner in self:
            adr = partner.street_raw or ''
            if partner.street_number1:
                adr += ' '+partner.street_number1
            if partner.street_number2:
                adr += ' - '+partner.street_number2
            partner.street = adr

