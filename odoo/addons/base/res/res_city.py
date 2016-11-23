# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class City(models.Model):
    _name = 'res.city'
    _description = 'City'
    _order = 'name'

    name = fields.Char(string='City Name', required=True, translate=True)
    zipcode = fields.Char(string='Zip')
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', 'State', domain="[('country_id', '=', country_id)]")
