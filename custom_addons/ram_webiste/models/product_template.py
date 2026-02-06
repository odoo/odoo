from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

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

