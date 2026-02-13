# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCity(models.Model):
    _name = 'res.city'
    _description = 'City'
    _order = 'name'
    _rec_names_search = ['name', 'zipcode']

    name = fields.Char("Name", required=True, translate=True)
    zipcode = fields.Char("Zip")
    country_id = fields.Many2one(comodel_name='res.country', string='Country', required=True)
    country_code = fields.Char(related='country_id.code')
    state_id = fields.Many2one(comodel_name='res.country.state', string='State', domain="[('country_id', '=', country_id)]")

    @api.depends_context('formatted_display_name')
    @api.depends('zipcode', 'state_id')
    def _compute_display_name(self):
        for city in self:
            name = city.name if not city.zipcode else f'{city.name} ({city.zipcode})'
            if self.env.context.get('formatted_display_name') and city.state_id:
                city.display_name = f"{name} \v--{city.state_id.name}--"
            else:
                city.display_name = name
