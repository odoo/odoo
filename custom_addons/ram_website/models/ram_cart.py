from odoo import models, fields, api
import json

class RamWebsiteCart(models.Model):
    _name = "ram.website.cart"
    _description = "RAM Website Persistent Cart"

    partner_id = fields.Many2one("res.partner", string="Customer", required=True, ondelete="cascade", index=True)
    line_ids = fields.One2many("ram.website.cart.line", "cart_id", string="Cart Lines")
    
    _partner_unique = models.Constraint('unique(partner_id)', 'A partner can only have one active cart.')

    @api.model
    def get_cart_for_partner(self, partner_id):
        return self.search([('partner_id', '=', partner_id)], limit=1)

class RamWebsiteCartLine(models.Model):
    _name = "ram.website.cart.line"
    _description = "RAM Website Cart Line"

    cart_id = fields.Many2one("ram.website.cart", string="Cart", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    qty = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Float(string="Unit Price")
    
    # Store variations (combos/attributes) as JSON for flexibility
    # This avoids complex many2many structures for simple cart persistence
    variation_data = fields.Text(string="Variation Data (JSON)")
    variation_summary = fields.Text(string="Variation Summary")
    
    image_url = fields.Char(string="Thumbnail URL")
    customer_note = fields.Text(string="Customer Instructions")
