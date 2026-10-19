# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_last_po_fallback_applicable(self, params=False):
        # the vendor of a past purchase is not necessarily one of the subcontractors
        if params and params.get('subcontractor_ids'):
            return False
        return super()._is_last_po_fallback_applicable(params)

    @api.model
    def _get_monthly_demand_moves_location_domain(self, warehouse_id=False):
        subcontracting_location_ids = self.env.companies.subcontracting_location_id.child_internal_location_ids.ids
        domain = Domain.AND([
            Domain.OR([
                super()._get_monthly_demand_moves_location_domain(warehouse_id),
                [('location_dest_id', 'in', subcontracting_location_ids)],
            ]),
            [('location_id', 'not in', subcontracting_location_ids)],
        ])
        return domain
