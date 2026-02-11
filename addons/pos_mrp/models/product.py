from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    has_phantom_bom = fields.Boolean(
        string="Has Phantom BOM",
        compute="_compute_has_phantom_bom",
    )

    @api.depends("product_tmpl_id")
    def _compute_has_phantom_bom(self):
        Bom = self.env["mrp.bom"]
        for product in self:
            bom = Bom._bom_find(
                product,
                company_id=product.company_id.id,
                bom_type="phantom",
            ).get(product)
            product.has_phantom_bom = bool(bom)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['has_phantom_bom']
        return params
