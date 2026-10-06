import base64
import json
import uuid
from datetime import UTC, datetime

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.pos_bancontact_pay import const


class PosBancontactProduct(models.Model):
    _name = "pos.bancontact.product"
    _description = "Bancontact Pay Product"

    name = fields.Char(required=True)
    ppid = fields.Char("Product ID", required=True, copy=False, help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a shop > Read the product ID from the card")
    api_key = fields.Char("API Key", required=True, copy=False, groups="point_of_sale.group_pos_manager", help="Bancontact Pro Portal > Admin Centre > Shops and products > Select a product > Manage API keys > View API key")
    preprod = fields.Boolean("Preprod", help="Run transactions in Bancontact's preprod environment.")
    usage = fields.Selection(
        selection=[
            ("display", "Display"),
            ("sticker", "Static QR"),
        ],
        string="QR Usage",
        default="display",
        required=True,
    )
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    payment_method_ids = fields.One2many("pos.payment.method", "bancontact_product_id", string="Payment Methods", context={"active_test": False})
    sticker_ids = fields.One2many("pos.bancontact.sticker", "product_id", string="Stickers")

    def _get_bancontact_api_url(self, target):
        """Return the Bancontact endpoint URL for the product's environment."""
        environment = "preprod" if self.preprod else "production"
        return const.API_URLS[environment][target]

    def write(self, vals):
        used_products = self.filtered("payment_method_ids")
        if "usage" in vals and any(product.usage != vals["usage"] for product in used_products):
            raise UserError(_("The QR usage of a Bancontact product can't be changed while it is used by a payment method."))
        return super().write(vals)
