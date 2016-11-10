# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models

#address_pattern = re.compile('^(.*?),? ([0-9]+[a-zA-Z]*)([ -]+([0-9]+[a-zA-Z]*))?[ ]*$')
#
#
#class ResCountryStateCity(models.Model):
#    _name = 'res.country.state.city'
#    _order = 'name'
#
#    name = fields.Char('City Name', required=True)
#    state_id = fields.Many2one('res.country.state', 'State')
#    country_id = fields.Many2one('res.country', 'Country', related='state_id.country_id', store=True, readonly=True)
#    code = fields.Char('Code')


class PartnerAddress(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    street_name = fields.Char('Street Name', compute='_split_street', inverse='_compute_street', store=True)
    street_number = fields.Char('House Number', compute='_split_street', inverse='_compute_street', store=True)
    street_number2 = fields.Char('Door Number', compute='_split_street', inverse='_compute_street', store=True)

    #city_id = fields.Many2one('res.country.state.city', 'City')
    #city = fields.Char('City', related='city_id.name', store=True)

    @api.multi
    def _compute_street(self):
        for partner in self:
            adr = partner.street_name or ''
            if partner.street_number:
                if adr:
                    adr += ', '
                adr += partner.street_number
            if partner.street_number2:
                if adr:
                    adr += '-'
                adr += partner.street_number2
            partner.street = adr

    #@api.model
    #def _address_fields(self):
    #    return super(PartnerAddress, self)._address_fields() + ['street_raw', 'street_number1', 'street_number2', 'city_id']

    @api.multi
    @api.depends('street', 'name')
    def _split_street(self):
        for partner in self:
            if not partner.street:
                partner.street_name = ''
                partner.street_number = ''
                partner.street_number2= ''
                continue
            street_number = street_number2 = ''
            adr = partner.street.split(',')
            partner.street_name = adr[:1][0]
            if len(adr) > 1:
                numbers = adr[1].strip().split('-')
                street_number = numbers[:1][0]
                street_number2 = len(numbers) > 1 and numbers[1:][0] or ''
            partner.street_number = street_number
            partner.street_number2 = street_number2


