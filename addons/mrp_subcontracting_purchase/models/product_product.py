from odoo import api, models
from odoo.fields import Domain


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _get_domain_monthly_demand_moves_location(self):
        subcontracting_location_ids = self.env.companies.mrp_subcontracting_config_id.subcontracting_location_id.child_internal_location_ids.ids
        return Domain.AND(
            [
                Domain.OR(
                    [
                        super()._get_domain_monthly_demand_moves_location(),
                        [("location_dest_id", "in", subcontracting_location_ids)],
                    ]
                ),
                [("location_id", "not in", subcontracting_location_ids)],
            ]
        )
