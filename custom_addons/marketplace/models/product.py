from odoo import models, fields, api

class SellerProduct(models.Model):
    _name = 'seller.product'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Seller Product'
    _order = 'date_added desc'

    seller_id = fields.Many2one(
        'marketplace.seller', string='Seller', required=True, tracking=True,
        help='Seller associated with this product.')
    date_added = fields.Datetime(
        string='Date Added', default=fields.Datetime.now, tracking=True,
        help='Date when the product was added by the seller.')
    product_name = fields.Char(
        string='Product Name', required=True, tracking=True,
        help='Name of the product.')
    product_price = fields.Monetary(
        string='Product Price', required=True, tracking=True,
        help='Price of the product.')
    description = fields.Text(string='Description',
        help='Description of the product.')
    product_image = fields.Binary(
        string='Product Image',
        help='Image of the product (supports any format).')
    product_video = fields.Binary(
        string='Product Video',
        help='Video of the product (supports any format).')
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        required=True, 
        default=lambda self: self.env.company.currency_id,
        help='Currency in which the product is priced.'
    )

    def action_add_product(self):
        """Handle Add button click."""
        # Logic for adding a product
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_edit_product(self):
        """Handle Edit button click."""
        # Logic for editing a product
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    


