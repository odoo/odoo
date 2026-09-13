from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    wishlist_opt_products_design_classes = fields.Char(
        string="Wishlist Page Design Class",
        help="CSS class for wishlist page design",
        default="o_wsale_products_opt_layout_catalog o_wsale_products_opt_design_thumbs "
        "o_wsale_products_opt_name_color_regular "
        "o_wsale_products_opt_thumb_cover o_wsale_products_opt_img_secondary_show "
        "o_wsale_products_opt_img_hover_zoom_out_light o_wsale_products_opt_has_cta "
        "o_wsale_products_opt_actions_inline o_wsale_products_opt_has_description "
        "o_wsale_products_opt_actions_promote o_wsale_products_opt_cc1 ",
    )

    wishlist_grid_columns = fields.Integer(
        help="Number of columns to display on the wishlist page",
        default=5,
    )

    wishlist_mobile_columns = fields.Integer(
        help="Number of columns to display on mobile for the wishlist page (1 or 2)",
        default=2,
    )

    wishlist_gap = fields.Char(
        string="Wishlist Grid Gap",
        help="Gap between products on the wishlist page",
        default="16px",
    )
