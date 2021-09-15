from odoo import models, fields


class MarketplaceCompany(models.Model):
    _inherit = "res.company"
    _description = "this model represents the marketplace vendors"

    is_marketplace = fields.Boolean()
    marketplace_id = fields.Integer(Selection="get_dists")

    _sql_constraints = [
        ('marketplace_id_unique', 'unique(marketplace_id)', 'marketplace distributor already exist')
    ]



