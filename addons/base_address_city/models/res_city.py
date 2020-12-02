# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class City(models.Model):
    _name = 'res.city'
    _description = 'City'
    _order = 'name, zipcode, state_id, country_id, id'

    name = fields.Char("Name", required=True, translate=True)
    zipcode = fields.Char("Zip")
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one(
        'res.country.state', 'State', domain="[('country_id', '=', country_id)]")
    
    def name_get(self):
        if not self.env.context.get('helper_search_city'):
            return super().name_get()
        res = []
        for city in self:
            name = [city.name]
            if city.zipcode:
                name.append(city.zipcode)
            if city.state_id:
                name.append(city.state_id.name)
            if city.country_id:
                name.append(city.country_id.name)
            res.append((city.id, ', '.join(name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        self = self.with_context(helper_search_city=True)
        if args is None:
            args = []
        if name and operator == 'ilike':
            recs = self.search(
                [('zipcode', 'ilike', name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super(City, self).name_search(name=name, args=args, operator=operator, limit=limit)
