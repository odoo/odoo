from werkzeug.urls import iri_to_uri

from odoo import api, fields, models
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    website_id = fields.Many2one(
        comodel_name="website",
        copy=False,
        ondelete="restrict",
        check_company=True,
    )

    @api.model
    def _get_compatible_providers(self, *args, website_id=None, report=None, **kwargs):
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
                reason=REPORT_REASONS_MAPPING["incompatible_website"],
            )
        return providers

    def get_base_url(self):
        if request and request.httprequest.url_root:
            return iri_to_uri(request.httprequest.url_root)
        return super().get_base_url()

    def copy(self, default=None):
        res = super().copy(default=default)
        if not default or "website_id" not in default:
            for src, copy in zip(self, res, strict=True):
                if src.website_id and src.company_id in copy.company_id.parent_ids:
                    copy.website_id = src.website_id
        return res
