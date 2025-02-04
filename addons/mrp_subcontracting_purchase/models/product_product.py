# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_monthly_demand_moves_location_domain(self):
        domain = super()._get_monthly_demand_moves_location_domain()
        domain = Domain.OR([
            domain,
            [('location_dest_id.is_subcontracting_location', '=', True)],
        ])
        domain = Domain.AND([
            domain,
            [('location_id.is_subcontracting_location', '!=', True)]
        ])
        return domain
