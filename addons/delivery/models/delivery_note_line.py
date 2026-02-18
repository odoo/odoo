# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class DeliveryNoteLine(models.Model):
    _name = "delivery.note.line"
    _description = "Product Moves (Delivery Move Line)"
    _rec_name = "product_id"

    description = fields.Text(string="Description Of Picking", compute="_compute_line_description")
    note_id = fields.Many2one(
        string="Delivery Note Reference",
        comodel_name="delivery.note",
        index=True,
    )
    product_image = fields.Image(related="product_id.image_128")
    product_id = fields.Many2one(
        string="Product",
        comodel_name="product.product",
        ondelete="cascade",
    )
    product_uom_id = fields.Many2one(string="Unit", comodel_name='uom.uom', required=True)
    product_uom_qty = fields.Float('Quantity', digits='Product Unit', copy=False)
    quantity_ordered = fields.Float('Quantity Ordered', digits='Product Unit', copy=False)
    sale_order_line_id = fields.Many2one(
        string="Source Sale Order Line",
        comodel_name='sale.order.line',
    )

    @api.depends('product_id')
    def _compute_line_description(self):
        for move in self:
            if move.product_id:
                product = move.product_id.with_context(lang=move._get_lang())
                move.description = product.description_sale or ""
            else:
                move.description = ""

    def _get_aggregated_properties(self):
        line_key = f"{self.product_id.id}_{self.product_id.display_name}_{self.description or ''}_{
            self.product_uom_id.id
        }"
        return {
            "line_key": line_key,
            "name": self.product_id.display_name,
            "description": self.description,
            "product": self.product_id,
            "product_uom": self.product_uom_id,
            "quantity": self.product_uom_qty,
            "qty_ordered": self.quantity_ordered,
        }

    def _get_aggregated_product_quantities(self):
        """Return a dictionary of products (key = id+name+description+uom) and corresponding values
        of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected
        to be useful in things such as delivery reports. Dict key is made as a combination of values
        we expect to want to group the products by (i.e. so data is not lost). This function
        purposely ignores lots/SNs because these are expected to already be properly grouped by
        line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, quantity,
                            product_uom}, ...}
        """
        aggregated_move_lines = {}

        for move_line in self:
            properties = move_line._get_aggregated_properties()
            if properties["quantity"]:
                line_key = properties["line_key"]
                if line_key not in aggregated_move_lines:
                    aggregated_move_lines[line_key] = {**properties}
                else:
                    aggregated_move_lines[line_key]["qty_ordered"] += properties["qty_ordered"]
                    aggregated_move_lines[line_key]["quantity"] += properties["quantity"]

        return aggregated_move_lines

    def _get_lang(self):
        """Determine language to use for translated description."""
        return self.note_id.partner_id.lang or self.env.user.lang
