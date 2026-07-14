# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME

_logger = logging.getLogger(__name__)


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

    @api.onchange('vat')
    def _onchange_l10n_in_gst_status(self):
        """
        Reset GST Status Whenever the `vat` of partner changes
        """
        for partner in self:
            if partner.country_code == 'IN':
                partner.l10n_in_gstin_verified_status = False
                partner.l10n_in_gstin_verified_date = False

    def action_l10n_in_verify_gstin_status(self):
        self.ensure_one()
        self.check_access('write')
        if self.env.company.sudo().account_fiscal_country_id.code != 'IN':
            raise UserError(_('You must be logged in an Indian company to use this feature'))
        if not self.vat:
            raise ValidationError(_("Please enter the GSTIN"))
        is_production = self.env.company.sudo().l10n_in_edi_production_env
        params = {
            "gstin_to_search": self.vat,
        }
        try:
            response = self.env['iap.account']._l10n_in_connect_to_server(
                is_production,
                params,
                '/iap/l10n_in_reports/1/public/search',
                "l10n_in_gstin_status.endpoint"
            )
        except AccessError:
            raise UserError(_("Unable to connect with GST network"))
        if response.get('error') and any(e.get('code') == 'no-credit' for e in response['error']):
            return self.env["bus.bus"]._sendone(self.env.user.partner_id, "iap_notification",
                {
                    "type": "no_credit",
                    "title": _("Not enough credits to check GSTIN status"),
                    "get_credits_url": self.env["iap.account"].get_credits_url(service_name=IAP_SERVICE_NAME),
                },
            )
        gst_status = response.get('data', {}).get('sts', "")
        if gst_status.casefold() == 'active':
            l10n_in_gstin_verified_status = True
        elif gst_status:
            l10n_in_gstin_verified_status = False
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
        else:
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
        self.write({
            "l10n_in_gstin_verified_status": l10n_in_gstin_verified_status,
            "l10n_in_gstin_verified_date": fields.Date.today(),
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "info",
                "message": _("GSTIN Status Updated Successfully"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
