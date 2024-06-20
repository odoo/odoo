import logging
from odoo.addons.l10n_in.models.res_partner import L10N_IN_GST_TREATMENTS_TYPE
from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.http import request
from odoo import _

_logger = logging.getLogger(__name__)


class L10nInCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        portal_layout_values = super()._prepare_portal_layout_values()
        portal_layout_values['l10n_in_gst_treatments'] = L10N_IN_GST_TREATMENTS_TYPE
        return portal_layout_values

    def _get_optional_fields(self):
        optional_fields = super()._get_optional_fields()
        optional_fields += [
            'property_account_position_id',
            'l10n_in_gst_treatment'
        ]
        return optional_fields

    def details_form_validate(self, data, partner_creation=False):
        error, error_message = super().details_form_validate(data, partner_creation)
        country = request.env['res.country'].search([('id', '=', request.params['country_id'])], limit=1)
        if request.env.company.account_fiscal_country_id.code == "IN":
            partner_gst_treatment = data.get('l10n_in_gst_treatment') or (country.code != "IN" and 'overseas') or 'consumer'
            if partner_gst_treatment == 'special_economic_zone':
                fiscal_position = request.env["account.chart.template"].ref(
                    "fiscal_position_in_export_sez_in", raise_if_not_found=False
                )
                if not fiscal_position:
                    _logger.info("l10n_in Export SEZ Fiscal Position not found")
                    return super().details_form_validate(data, partner_creation)
                data.update({
                    'property_account_position_id': fiscal_position.id,
                    'l10n_in_gst_treatment': 'special_economic_zone',
                })
            elif partner_gst_treatment == 'consumer' and len(data.get('vat') or ''):
                error["l10n_in_gst_treatment"] = 'error'
                error_message.append(_('If you have a GSTIN, you cannot choose GST Treatment as Consumer.'))
            else:
                data.update({
                    'property_account_position_id': False,
                    'l10n_in_gst_treatment': partner_gst_treatment,
                })
        return error, error_message
