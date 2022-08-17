# coding: utf-8

from odoo import fields, models
from odoo.http import request


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    website_id = fields.Many2one(
        "website",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )

    def get_base_url(self):
        # Give priority to url_root to handle multi-website cases
        if request and request.httprequest.url_root:
            return request.httprequest.url_root
        return super().get_base_url()
