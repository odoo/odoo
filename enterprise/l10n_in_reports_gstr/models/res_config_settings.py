# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import models, fields, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_gstr_gst_username = fields.Char(
        "GST username", related="company_id.l10n_in_gstr_gst_username", readonly=False
    )
    l10n_in_gstr_gst_auto_refresh_token = fields.Boolean(
        string="Is auto refresh token",
        related="company_id.l10n_in_gstr_gst_auto_refresh_token",
        readonly=False)
    l10n_in_gstr_activate_einvoice_fetch = fields.Selection(
        related="company_id.l10n_in_gstr_activate_einvoice_fetch",
        readonly=False)

    def l10n_in_gstr_gst_send_otp(self):
        otp_validation_wizard = self.env['l10n_in.gst.otp.validation'].create({
            'company_id': self.company_id.id,
        })
        return otp_validation_wizard.gst_send_otp()

    def _l10n_in_gsp_provider_changed(self):
        """
            This change should effect all Indian companies so we search for them and
            Invalidate existing tokens if GSP provider changed
        """
        self.env['res.company'].sudo().search([('account_fiscal_country_id.code', '=', 'IN')]).write({
            'l10n_in_gstr_gst_token': False,
            'l10n_in_gstr_gst_token_validity': False,
        })
        super()._l10n_in_gsp_provider_changed()
