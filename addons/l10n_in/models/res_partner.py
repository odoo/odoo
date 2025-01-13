import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME

_logger = logging.getLogger(__name__)

TEST_GST_NUMBER = "36AABCT1332L011"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment")

    l10n_in_pan = fields.Char(
        string="PAN",
        help="PAN enables the department to link all transactions of the person with the department.\n"
             "These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT,"
             " specified transactions, correspondence, and so on.\n"
             "Thus, PAN acts as an identifier for the person with the tax department."
    )

    display_pan_warning = fields.Boolean(string="Display pan warning", compute="_compute_display_pan_warning")
    l10n_in_gst_state_warning = fields.Char(compute="_compute_l10n_in_gst_state_warning")
    l10n_in_is_gst_registered_enabled = fields.Boolean(compute="_compute_l10n_in_gst_registered_and_status")

    # gstin_status related field
    l10n_in_gstin_verified_status = fields.Boolean(string="GST Status", tracking=True)
    l10n_in_gstin_verified_date = fields.Date(string="GSTIN Verified Date", tracking=True)
    l10n_in_gstin_status_feature_enabled = fields.Boolean(compute="_compute_l10n_in_gst_registered_and_status")

    @api.depends('vat', 'state_id', 'country_id', 'fiscal_country_codes')
    def _compute_l10n_in_gst_state_warning(self):
        for partner in self:
            if (
                "IN" in partner.fiscal_country_codes
                and partner.check_vat_in(partner.vat)
            ):
                if partner.vat[:2] == "99":
                    partner.l10n_in_gst_state_warning = _(
                        "As per GSTN the country should be other than India, so it's recommended to"
                    )
                else:
                    state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', partner.vat[:2])], limit=1)
                    if state_id and state_id != partner.state_id:
                        partner.l10n_in_gst_state_warning = _(
                            "As per GSTN the state should be %s, so it's recommended to", state_id.name
                        )
                    else:
                        partner.l10n_in_gst_state_warning = False
            else:
                partner.l10n_in_gst_state_warning = False

    @api.depends('l10n_in_pan')
    def _compute_display_pan_warning(self):
        for partner in self:
            partner.display_pan_warning = partner.vat and partner.l10n_in_pan and partner.l10n_in_pan != partner.vat[2:12]

    @api.depends('company_id.l10n_in_is_gst_registered', 'company_id.l10n_in_gstin_status_feature')
    def _compute_l10n_in_gst_registered_and_status(self):
        for record in self:
            company = record.company_id or self.env.company
            record.l10n_in_is_gst_registered_enabled = company.l10n_in_is_gst_registered
            record.l10n_in_gstin_status_feature_enabled = company.l10n_in_gstin_status_feature

    @api.onchange('vat')
    def _onchange_l10n_in_gst_status(self):
        """
        Reset GST Status Whenever the `vat` of partner changes
        """
        for partner in self:
            if partner.country_code == 'IN' and (partner.l10n_in_gstin_verified_status or partner.l10n_in_gstin_verified_date):
                partner.l10n_in_gstin_verified_status = False
                partner.l10n_in_gstin_verified_date = False

    def action_l10n_in_verify_gstin_status(self):
        self.ensure_one()
        self.check_access('write')
        if self.env.company.sudo().account_fiscal_country_id.code != 'IN':
            raise UserError(_('You must be logged in an Indian company to use this feature'))
        if not self.vat:
            raise ValidationError(_("Please enter the GSTIN"))
        if not self.env.company.l10n_in_gstin_status_feature:
            raise ValidationError(_("This feature is not activated. Go to Settings to activate this feature."))
        is_production = self.env.company.sudo().l10n_in_edi_production_env
        params = {
            "gstin_to_search": self.vat,
            "gstin": self.env.company.vat,
        }
        try:
            response = self.env['iap.account']._l10n_in_connect_to_server(
                is_production,
                params,
                '/iap/l10n_in_reports/1/public/search',
                "l10n_in.endpoint"
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

    @api.onchange('company_type')
    def onchange_company_type(self):
        res = super().onchange_company_type()
        if self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('country_id')
    def _onchange_country_id(self):
        res = super()._onchange_country_id()
        if self.country_id and self.country_id.code != 'IN':
            self.l10n_in_gst_treatment = 'overseas'
        elif self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat and self.check_vat_in(self.vat):
            self.vat = self.vat.upper()
            state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
            if state_id:
                self.state_id = state_id
            if self.vat[2].isalpha():
                self.l10n_in_pan = self.vat[2:12]

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['l10n_in_gst_treatment', 'l10n_in_pan']

    def check_vat_in(self, vat):
        """
            This TEST_GST_NUMBER is used as test credentials for EDI
            but this is not a valid number as per the regular expression
            so TEST_GST_NUMBER is considered always valid
        """
        if vat == TEST_GST_NUMBER:
            return True
        return super().check_vat_in(vat)

    @api.model
    def _l10n_in_get_partner_vals_by_vat(self, vat):
        partner_details = self.read_by_vat(vat)
        partner_data = partner_details[0] if partner_details else {}
        if partner_data:
            partner_gid = partner_data.get('partner_gid')
            if partner_gid:
                partner_data = self.enrich_company(company_domain=None, partner_gid=partner_gid, vat=partner_data.get('vat'))
                partner_data = self._iap_replace_logo(partner_data)
            return {
                'name': partner_data.get('name'),
                'company_type': 'company',
                'partner_gid': partner_gid,
                'vat': partner_data.get('vat'),
                'l10n_in_gst_treatment': 'regular',
                'image_1920': partner_data.get('image_1920'),
                'street': partner_data.get('street'),
                'street2': partner_data.get('street2'),
                'city': partner_data.get('city'),
                'state_id': partner_data.get('state_id', {}).get('id', False),
                'country_id': partner_data.get('country_id', {}).get('id', False),
                'zip': partner_data.get('zip'),
            }
        return {}

    def action_update_state_as_per_gstin(self):
        self.ensure_one()
        state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
        self.state_id = state_id
