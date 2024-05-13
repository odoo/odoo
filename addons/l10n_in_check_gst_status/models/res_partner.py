# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models, _
from odoo.addons.iap import jsonrpc
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons.l10n_in_edi.models.account_edi_format import DEFAULT_IAP_ENDPOINT, DEFAULT_IAP_TEST_ENDPOINT

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gstin_verified_status = fields.Boolean(
        string="GST Status",
        compute="_compute_l10n_in_gst_status",
        store=True,
        tracking=True,
    )
    l10n_in_gstin_verified_date = fields.Date(
        string="GSTIN Verified Date",
        compute="_compute_l10n_in_gst_status",
        store=True,
        tracking=True,
    )

    @api.depends('vat')
    def _compute_l10n_in_gst_status(self):
        """
        Reset GST Status Whenever the `vat` of partner changes
        """
        for partner in self:
            if partner.country_code == 'IN':
                partner.l10n_in_gstin_verified_status = False
                partner.l10n_in_gstin_verified_date = False

    def _l10n_in_gstin_status_get_url(self, company):
        if company.sudo().l10n_in_edi_production_env:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_check_gst_status.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, '/iap/l10n_in_reports/1/public/search')
        return url

    def get_l10n_in_gstin_verified_status(self):
        self.ensure_one()
        if not self.vat:
            raise ValidationError(_("Please enter the GSTIN"))
        url = self._l10n_in_gstin_status_get_url(self.env.company)
        params = {
            "account_token": self.env["iap.account"].get("l10n_in_edi").account_token,
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "gstin_to_search": self.vat,
        }
        try:
            response = jsonrpc(url, params=params, timeout=25)
        except AccessError:
            raise UserError(_("Unable to connect with GST network"))
        if response.get('error') and any(e.get('code') == 'no-credit' for e in response['error']):
            return self.env["bus.bus"]._sendone(self.env.user.partner_id, "iap_notification",
                {
                    "type": "no_credit",
                    "title": "Not enough credits to check GSTIN status",
                    "get_credits_url": self.env["iap.account"].get_credits_url(service_name="l10n_in_edi"),
                },
            )
        gst_status = response.get('data', {}).get('sts', "")
        if gst_status.casefold() == 'active':
            l10n_in_gstin_verified_status = True
        elif gst_status:
            l10n_in_gstin_verified_status = False
            self.message_post(
                body=_(
                    "GSTIN %(vat)s is %(status)s and Effective from %(date_from)s",
                    vat=self.vat,
                    status=gst_status,
                    date_from=response.get("data", {}).get("cxdt", ""),
                )
            )
        else:
            _logger.info("GST status check error %s", response)
            raise UserError(_("Error in getting GST status. please try again"))
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
