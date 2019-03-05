from odoo import api, fields, models


class MrpProduction(models.Model):
    """ Extension to display product customizations on manufacturing orders"""
    _inherit = 'mrp.production'

    product_customization = fields.Char(string="Description", compute='_compute_product_details', store=True)

    @api.depends("move_dest_ids")
    def _compute_product_details(self):
        """ Gets the product details from the Sale order line source """
        for production in self:
            product_details = ""
            product = production.product_id
            # If product can be customized (see sale/models/product_product.py)
            if product.is_customizable:
                # Find the stock move referencing the sale order delivery
                for move in production.move_dest_ids:
                    if move.sale_line_id and move.is_name_informative:
                        sol_description = move.name
                        # As product name is already displayed, we can remove its name
                        # from the description of the product customization
                        product_details = sol_description.replace(product.name, "")
                        break

            production.product_customization = product_details
