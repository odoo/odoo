# coding: utf-8

from odoo import fields, models
from odoo.http import request


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    website_id = fields.Many2one(
        "website",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )

    def _get_base_url(self):
        """ Override of payment to take multi-website feature into account.

        Note: self.ensure_one()

        :return: The website base url
        :rtype: str
        """
        self.ensure_one()
        url = ''
        if request:  # Give priority to url_root to handle multi-website cases
            url = request.httprequest.url_root
        if not url and self.website_id:  # Secondly, use the website set on the acquirer
            url = self.website_id._get_http_domain()
        if not url:  # Fallback to web.base.url
            url = super()._get_base_url()
        return url
