# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_monthly_demand_moves_location_domain(self):
        domain = Domain.AND([
            Domain.OR([
                super()._get_monthly_demand_moves_location_domain(),
                [('location_dest_id', '=', self.env.company.subcontracting_location_id.id)],
            ]),
            [('location_id', '!=', self.env.company.subcontracting_location_id.id)],
        ])
        return domain
