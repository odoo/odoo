
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    wishlist_opt_products_design_classes = fields.Char(
        string="Wishlist Page Design Class",
        default=(
            'o_wsale_products_opt_layout_catalog o_wsale_products_opt_design_thumbs '
            'o_wsale_products_opt_name_color_regular o_wsale_products_opt_thumb_6_5 '
            'o_wsale_products_opt_thumb_cover o_wsale_products_opt_img_secondary_show '
            'o_wsale_products_opt_img_hover_zoom_out_light o_wsale_products_opt_has_cta '
            'o_wsale_products_opt_actions_inline o_wsale_products_opt_has_description '
            'o_wsale_products_opt_actions_promote o_wsale_products_opt_cc1 '
        ),
        help="CSS class for wishlist page design"
    )
