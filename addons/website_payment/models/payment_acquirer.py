# coding: utf-8

from odoo import api, fields, models
from odoo.http import request
from odoo.osv import expression


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    website_id = fields.Many2one("website")

    @api.model
    def _get_available_acquirers(self, partner=None, company=None, extra_domain=None):
        """ Override to include website filtering for acquirers.
        """
        website_domain = [
            "|",
            ("website_id", "=", False),
            ("website_id", "=", request.website.id),
        ]
        extra_domain = (
            extra_domain and expression.AND([extra_domain, website_domain]) or website_domain
        )
        return super()._get_available_acquirers(
            partner=partner, company=company, extra_domain=extra_domain
        )
