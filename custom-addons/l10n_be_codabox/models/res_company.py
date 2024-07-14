# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import requests

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg, raise_deprecated


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_be_codabox_fiduciary_vat = fields.Char(string="Accounting Firm VAT", compute="_compute_l10n_be_codabox_fiduciary_vat")
    l10n_be_codabox_iap_token = fields.Char(string="IAP Access Token")
    l10n_be_codabox_is_connected = fields.Boolean(string="CodaBox Is Connected")
    l10n_be_codabox_soda_journal = fields.Many2one("account.journal", string="Journal in which SODA's will be imported", domain="[('type', '=', 'bank')]")

    def _compute_l10n_be_codabox_fiduciary_vat(self):
        for company in self:
            if "account_representative_id" in self.env['res.company']._fields:
                company.l10n_be_codabox_fiduciary_vat = re.sub("[^0-9]", "", company.account_representative_id.vat or "")
            else:
                company.l10n_be_codabox_fiduciary_vat = False

    @api.model
    def _l10_be_codabox_call_iap(self, url, params):
        response = requests.post(url, json={"params": params}, timeout=10)
        result = response.json().get("result", {})
        error = result.get("error")
        if error:
            raise UserError(get_error_msg(error))
        return result

    def _l10n_be_codabox_verify_prerequisites(self):
        self.check_access_rule('write')
        self.check_access_rights('write')
        self.ensure_one()
        if not self.vat:
            raise UserError(_("The company VAT number is not set."))
        if not self.l10n_be_codabox_fiduciary_vat:
            raise UserError(_("The fiduciary VAT number is not set."))

    def _l10n_be_codabox_connect(self):
        raise_deprecated(self.env)

    def _l10n_be_codabox_revoke(self):
        raise_deprecated(self.env)
