import uuid

import requests

from odoo import api, fields, models


class PosBancontactSticker(models.Model):
    _name = "pos.bancontact.sticker"
    _description = "Bancontact Pay Sticker"
    _order = "product_id, id"

    name = fields.Char(required=True)
    product_id = fields.Many2one("pos.bancontact.product", string="Bancontact Product", required=True, index=True, ondelete="cascade")
    identifier = fields.Char(required=True, readonly=True, copy=False, default=lambda self: self._generate_identifier())
    url = fields.Char("URL", compute="_compute_url")
    payment_method_ids = fields.One2many("pos.payment.method", "bancontact_sticker_id", context={"active_test": False})
    payment_method_id = fields.Many2one("pos.payment.method", string="Payment Method", compute="_compute_payment_method_id", store=True)
    payment_method_active = fields.Boolean(related="payment_method_id.active")

    _identifier_unique = models.Constraint(
        "unique (identifier)",
        "A sticker with this identifier already exists.",
    )

    @api.model
    def _generate_identifier(self):
        return uuid.uuid4().hex[:8]

    @api.depends("payment_method_ids")
    def _compute_payment_method_id(self):
        for sticker in self:
            sticker.payment_method_id = sticker.payment_method_ids[:1]

    @api.depends("product_id.ppid", "identifier")
    def _compute_url(self):
        for sticker in self:
            sticker.url = f"https://pay.bancontact.net/l/1/{sticker.product_id.ppid}/{sticker.identifier}"

    def download_sticker(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/bancontact_pay/sticker/{self.identifier}",
            "target": "new",
        }

    def _fetch_sticker_image(self):
        self.ensure_one()
        response = requests.get(self.product_id._get_bancontact_api_url("qrcode"), params={
            'f': 'PNG',
            's': 'XL',
            'c': self.url,
        }, timeout=10)
        response.raise_for_status()
        return response.content
