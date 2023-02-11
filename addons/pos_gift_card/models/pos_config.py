# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    use_gift_card = fields.Boolean(string="Gift Card")

    gift_card_product_id = fields.Many2one(
        "product.product",
        string="Gift Card Product",
        help="This product is used as reference on customer receipts.",
    )

    gift_card_settings = fields.Selection(
        [
            ("create_set", "Generate a new barcode and set a price"),
            ("scan_set", "Scan an existing barcode and set a price"),
            ("scan_use", "Scan an existing barcode with an existing price"),
        ],
        string="Gift Cards settings",
        default="create_set",
        help="Defines the way you want to set your gift cards.",
    )

    @api.onchange("use_gift_card")
    def _onchange_giftproduct(self):
        if self.use_gift_card:
            self.gift_card_product_id = self.env.ref(
                "gift_card.pay_with_gift_card_product", False
            )
        else:
            self.gift_card_product_id = False
