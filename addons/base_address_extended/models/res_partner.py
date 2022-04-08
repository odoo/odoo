# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class Partner(models.Model):
    _inherit = ['res.partner']

    street_name = fields.Char(
        'Street Name', compute='_compute_street_data', store=True, readonly=False)
    street_number = fields.Char(
        'House', compute='_compute_street_data', store=True, readonly=False)
    street_number2 = fields.Char(
        'Door', compute='_compute_street_data', store=True, readonly=False)

    city_id = fields.Many2one(comodel_name='res.city', string='City ID')
    country_enforce_cities = fields.Boolean(related='country_id.enforce_cities')

    @api.depends('street_name', 'street_number', 'street_number2')
    def _compute_street(self):
        super()._compute_street()
        for partner in self:
            street = ((partner.street_name or '') + " " + (partner.street_number or '')).strip()
            if partner.street_number2:
                street = street + " - " + partner.street_number2
            partner.street = street

    @api.depends('street')
    def _compute_street_data(self):
        """Splits street value into sub-fields.
        Recomputes the fields of STREET_FIELDS when `street` of a partner is updated"""
        for partner in self:
            partner.update(tools.street_split(partner.street))

    def _get_street_split(self):
        self.ensure_one()
        return {
            'street_name': self.street_name,
            'street_number': self.street_number,
            'street_number2': self.street_number2
        }

    @api.depends('city_id')
    def _compute_city(self):
        # override
        super()._compute_city()
        for partner in self.filtered(lambda rec: rec.city_id):
            partner.city = partner.city_id.name

    @api.depends('city_id')
    def _compute_zip(self):
        # override
        super()._compute_zip()
        for partner in self.filtered(lambda rec: rec.city_id and rec.city_id.zip):
            partner.zip = partner.city_id.zip

    @api.depends('city_id')
    def _compute_state_id(self):
        # override
        super()._compute_state_id()
        for partner in self.filtered(lambda rec: rec.city_id and rec.city_id.country_id):
            partner.state_id = partner.city_id.state_id
