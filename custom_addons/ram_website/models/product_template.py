from odoo import fields, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = [
        "product.template",
        "website.published.mixin",
        "website.multi.mixin",
    ]

    website_sequence = fields.Integer(
        "Website Sequence",
        help="Gives the sequence order when displaying a list of product templates.",
        default=1,
    )

    ram_available_on_website_menu = fields.Boolean(
        string="Available on Website Menu",
        help="If enabled, this product can be shown in the restaurant menu section on the website.",
    )
    ram_spice_level = fields.Selection(
        selection=[
            ("none", "None"),
            ("mild", "Mild"),
            ("medium", "Medium"),
            ("hot", "Hot"),
            ("extra_hot", "Extra Hot"),
        ],
        string="Spice Level",
        default="none",
    )
    ram_is_recommended = fields.Boolean(
        string="Recommended",
        help="If enabled, this product will appear in the Featured Dishes section on the homepage.",
    )

    ram_website_price = fields.Float(
        string="Website Price (Tax Included)",
        compute="_compute_ram_website_price",
        help="Price displayed on the website, including taxes."
    )

    def _compute_ram_website_price(self):
        for product in self:
            # We use sudo() as public users might not have access to some tax/currency records
            website = self.env['website'].get_current_website()
            currency = website.currency_id or self.env.company.currency_id
            res = product.taxes_id.compute_all(product.list_price, currency=currency, product=product)
            product.ram_website_price = res['total_included']

