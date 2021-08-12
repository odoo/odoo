# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Country(models.Model):
    _inherit = 'res.country'

    @api.model_create_multi
    def create(self, vals_list):
        self.env['account.fiscal.position'].clear_caches()
        return super(Country, self).create(vals_list)

    def write(self, vals):
        self.env['account.fiscal.position'].clear_caches()
        return super(Country, self).write(vals)
