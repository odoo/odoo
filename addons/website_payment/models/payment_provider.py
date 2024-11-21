# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import iri_to_uri

from odoo import api, fields, models
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    website_id = fields.Many2one(
        "website",
        check_company=True,
        ondelete="restrict",
    )

    @api.model
    def _get_compatible_providers(self, *args, website_id=None, report=None, **kwargs):
        """ Override of `payment` to only return providers matching website-specific criteria.

        In addition to the base criteria, the website must either not be set or be the same as the
        one provided in the kwargs.

        :param int website_id: The provided website, as a `website` id.
        :param dict report: The availability report.
        :return: The compatible providers.
        :rtype: payment.provider
        """
        providers = super()._get_compatible_providers(
            *args, website_id=website_id, report=report, **kwargs
        )
        if website_id:
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: not p.website_id or p.website_id.id == website_id
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=REPORT_REASONS_MAPPING['incompatible_website'],
            )
        return providers

    def get_base_url(self):
        # Give priority to url_root to handle multi-website cases
        if request and request.httprequest.url_root:
            # Some domain names can use non-Latin script or alphabet or the Latin
            # alphabet-based characters with diacritics or ligatures. They are
            # stored as ASCII strings using Punycode transcription in the DNS
            # system and need to be converted to send to external APIs.
            return iri_to_uri(request.httprequest.url_root)
        return super().get_base_url()

    def copy(self, default=None):
        res = super().copy(default=default)
        if self._context.get('stripe_connect_onboarding'):
            res.website_id = False
        return res
