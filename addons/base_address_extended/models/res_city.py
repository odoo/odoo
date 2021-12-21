# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression

class City(models.Model):
    _name = 'res.city'
    _description = 'City'
    _order = 'name'

    name = fields.Char("Name", required=True, translate=True)
    zipcode = fields.Char("Zip")
    country_id = fields.Many2one(comodel_name='res.country', string='Country', required=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string='State', domain="[('country_id', '=', country_id)]")

    def name_get(self):
        res = []
        for city in self:
            name = city.name if not city.zipcode else '%s (%s)' % (city.name, city.zipcode)
            res.append((city.id, name))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        ''' Enable searching by zipcode of a city
        '''
        args = list(args or [])
        domain = []
        if name:
            connector = '!' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('zipcode', 'ilike', name), (self._rec_name, operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
