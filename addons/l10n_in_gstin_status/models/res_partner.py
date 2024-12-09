# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME

_logger = logging.getLogger(__name__)

L10N_IN_GST_TREATMENT_MAPPING = {
    "Regular": "regular",
    "SEZ Unit": "special_economic_zone",
    "SEZ Developer": "special_economic_zone",
    "Composition": "composition",
    "Consulate or Embassy of Foreign Country": "uin_holders",
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gstin_verified_status = fields.Boolean(
        string="GST Status",
        tracking=True,
    )
    l10n_in_gstin_verified_date = fields.Date(
        string="GSTIN Verified Date",
        tracking=True,
    )

    @api.model
    def _fetch_l10n_in_gstin_details(self, is_production, params):
        try:
            response = self.env['iap.account']._l10n_in_connect_to_server(
                is_production,
                params,
                '/iap/l10n_in_reports/1/public/search',
                'l10n_in_gstin_status.endpoint'
            )
        except AccessError:
            raise UserError(_("Unable to connect with GST network"))
        return response

    @api.onchange('vat')
    def _onchange_l10n_in_gst_status(self):
        """
        Reset GST Status Whenever the `vat` of partner changes
        """
        for partner in self:
            if partner.country_code == 'IN':
                partner.l10n_in_gstin_verified_status = False
                partner.l10n_in_gstin_verified_date = False

    def action_l10n_in_verify_gstin_status(self, vat=None, ignore_errors=False):
        """ Fetches the GSTIN details by making an API call to IAP.
        :param ignore_errors: If set to True, supresses exceptions.
                              This is particularly useful when the method is called from the website, 
                              ensuring that portal users do not encounter any IAP-related errors.
        """
        self.ensure_one()
        if not self.vat and not ignore_errors:
            raise ValidationError(_("Please enter the GSTIN"))
        is_production = self.env.company.sudo().l10n_in_edi_production_env
        params = {
            "gstin_to_search": vat or self.vat,
        }
        response = self._fetch_l10n_in_gstin_details(is_production, params)
        if response.get('error') and any(e.get('code') == 'no-credit' for e in response['error']) and not ignore_errors:
            return self.env["bus.bus"]._sendone(self.env.user.partner_id, "iap_notification",
                {
                    "type": "no_credit",
                    "title": _("Not enough credits to check GSTIN status"),
                    "get_credits_url": self.env["iap.account"].get_credits_url(service_name=IAP_SERVICE_NAME),
                },
            )
        gst_status = response.get('data', {}).get('sts', "")
        values = {}
        if gst_status.casefold() == 'active':
            l10n_in_gstin_verified_status = True
            gst_treatment = L10N_IN_GST_TREATMENT_MAPPING.get(response.get('data', {}).get('dty'), 'regular')
            fiscal_position = (
                gst_treatment == 'special_economic_zone'
                and self.env['account.chart.template'].ref(
                    'fiscal_position_in_export_sez_in', raise_if_not_found=False
                )
            )
            values['l10n_in_gst_treatment'] = gst_treatment
            if fiscal_position:
                values['property_account_position_id'] = fiscal_position.id
            elif gst_treatment != 'special_economic_zone':
                values['property_account_position_id'] = False
        elif gst_status:
            l10n_in_gstin_verified_status = False
            values.update({
                'l10n_in_gst_treatment': 'unregistered',
                'property_account_position_id': False
            })
            date_from = response.get("data", {}).get("cxdt", '')
            if date_from and re.search(r'\d', date_from):
                message = _(
                    "GSTIN %(vat)s is %(status)s and Effective from %(date_from)s.",
                    vat=self.vat,
                    status=gst_status,
                    date_from=date_from,
                )
            else:
                message = _(
                    "GSTIN %(vat)s is %(status)s, effective date is not available.",
                    vat=self.vat,
                    status=gst_status
                )
            if not is_production:
                message += _(" Warning: You are currently in a test environment. The result is a dummy.")
            self.message_post(body=message)
        elif not ignore_errors:
            _logger.info("GST status check error %s", response)
            if response.get('error') and any(e.get('code') == 'SWEB_9035' for e in response['error']):
                raise UserError(
                    _("The provided GSTIN is invalid. Please check the GSTIN and try again.")
                )
            default_error_message = _(
                "Something went wrong while fetching the GST status."
                "Please Contact Support if the error persists with"
                "Response: %(response)s",
                response=response
            )
            error_messages = [
                f"[{error.get('code') or _('Unknown')}] {error.get('message') or default_error_message}"
                for error in response.get('error')
            ]
            raise UserError(
                error_messages
                and '\n'.join(error_messages)
                or default_error_message
            )
        values.update({
            'l10n_in_gstin_verified_status': l10n_in_gstin_verified_status,
            'l10n_in_gstin_verified_date': fields.Date.today(),
        })
        self.write(values)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "message": _("GSTIN Status Updated Successfully"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
