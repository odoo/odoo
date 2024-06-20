import logging
from odoo.addons.l10n_in.models.res_partner import L10N_IN_GST_TREATMENTS_TYPE
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo import _

_logger = logging.getLogger(__name__)


class WebsiteSaleInherit(WebsiteSale):

    def _prepare_address_form_values(self, *args, **_kwargs):
        address_form_values = super()._prepare_address_form_values(*args, **_kwargs)
        if request.env.company.country_code == "IN":
            address_form_values.update({
                'l10n_in_gst_treatments': L10N_IN_GST_TREATMENTS_TYPE,
                'vat_label': 'GSTIN',
            })
        return address_form_values

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)
        if request.env.company.account_fiscal_country_id.code == "IN":
            country = request.env['res.country'].search([('id', '=', request.params.get('country_id'))], limit=1)
            partner_gst_treatment = (
                extra_form_data.get('l10n_in_gst_treatment')
                or (country.code != "IN" and 'overseas')
                or 'consumer'
            )
            if partner_gst_treatment == 'special_economic_zone':
                fiscal_position = request.env["account.chart.template"].ref(
                    "fiscal_position_in_export_sez_in", raise_if_not_found=False
                )
                if not fiscal_position:
                    _logger.info(
                        "l10n_in Export SEZ Fiscal Position not found for company(%s)", request.env.company.name
                    )
                    return address_values, extra_form_data
                address_values.update({
                    'property_account_position_id': fiscal_position.id,
                    'l10n_in_gst_treatment': 'special_economic_zone',
                })
            else:
                address_values.update({
                    'property_account_position_id': False,
                    'l10n_in_gst_treatment': partner_gst_treatment,
                })

        return address_values, extra_form_data

    def _validate_address_values(self, address_values, *args, **_kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, *args, **_kwargs
        )
        if request.env.company.account_fiscal_country_id.code == "IN":
            if (
                address_values.get("l10n_in_gst_treatment") == "consumer"
                and len(address_values.get("vat") or "") > 0
            ):
                error_messages.append(_("If you have a GSTIN, you cannot choose GST Treatment as Consumer."))
        return invalid_fields, missing_fields, error_messages
