from odoo import fields, models


class ProductRibbon(models.Model):
    _inherit = "product.ribbon"

    assign = fields.Selection(
        selection_add=[("out_of_stock", "when out of stock")],
        ondelete={"out_of_stock": "cascade"},
        help="Defines how this ribbon is assigned to products:\n"
        "- Manually: You assign the ribbon manually to products.\n"
        "- Sale: Applied when the product is visibly on sale.\n"
        "- New: Applied based on the New period you will define.\n"
        "- Out Of Stock: Applied when the product is out of stock.",
    )

    def _is_applicable_for(self, product, price_data):
        return super()._is_applicable_for(product, price_data) or (
            product
            and self.assign == "out_of_stock"
            and not product.product_tmpl_id.allow_out_of_stock_order
            and product._is_sold_out()
        )
