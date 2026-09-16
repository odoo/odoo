from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        price = super()._get_bom_price(bom, boms_to_recompute, byproduct_bom)
        if bom and bom.type == "subcontract":
            seller = self._select_seller(
                quantity=bom.product_qty,
                uom_id=bom.product_uom_id,
                params={"subcontractor_ids": bom.subcontractor_ids},
            )
            if seller:
                seller_price = seller.currency_id._convert(
                    seller.price,
                    self.env.company.currency_id,
                    (bom.company_id or self.env.company),
                    fields.Date.today(),
                )
                price += seller.product_uom_id._get_price_in_unit(
                    seller_price, self.uom_id
                )
        return price
