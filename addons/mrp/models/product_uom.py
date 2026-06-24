from odoo import fields, models


class ProductUom(models.Model):
    _inherit = 'product.uom'

    # sudo : Added to compute allowed UoMs from BoMs/By-products regardless of user access rights.
    allowed_uom_ids = fields.Many2many(compute_sudo=True)

    def _compute_allowed_uom_ids(self):
        super()._compute_allowed_uom_ids()
        if self.env.context.get('active_model') == 'uom.uom':
            return

        has_byproducts = self.env.user.has_group('mrp.group_mrp_byproducts')
        if has_byproducts:
            byproducts_by_product = (
                self.env['mrp.bom.byproduct']
                .search([('product_id', 'in', self.product_id.ids)])
                .grouped('product_id')
            )

        for product_uom in self:
            product = product_uom.product_id
            bom_uoms = product.bom_ids.filtered(
                lambda b: not b.product_id or b.product_id == product
            ).uom_id
            if has_byproducts:
                bom_uoms |= byproducts_by_product.get(
                    product,
                    self.env['mrp.bom.byproduct'],
                ).uom_id
            product_uom.allowed_uom_ids |= bom_uoms
