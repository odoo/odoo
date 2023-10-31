# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    street_name = fields.Char('Street Name', compute='_compute_address',
                              inverse='_inverse_street_name')
    street_number = fields.Char('House Number', compute='_compute_address',
                                inverse='_inverse_street_number')
    street_number2 = fields.Char('Door Number', compute='_compute_address',
                                 inverse='_inverse_street_number2')

    def _get_company_address_field_names(self):
        fields_matching = super(Company, self)._get_company_address_field_names()
        return list(set(fields_matching + ['street_name', 'street_number', 'street_number2']))

    def _inverse_street_name(self):
        for company in self:
            company.partner_id.street_name = company.street_name

    def _inverse_street_number(self):
        for company in self:
            company.partner_id.street_number = company.street_number

    def _inverse_street_number2(self):
        for company in self:
            company.partner_id.street_number2 = company.street_number2
