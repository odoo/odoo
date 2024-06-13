# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_edi_username = fields.Char("E-invoice (IN) Username", groups="base.group_system")
    l10n_in_edi_password = fields.Char("E-invoice (IN) Password", groups="base.group_system")
    l10n_in_edi_token = fields.Char("E-invoice (IN) Token", groups="base.group_system")
    l10n_in_edi_token_validity = fields.Datetime("E-invoice (IN) Valid Until", groups="base.group_system")

    def _l10n_in_edi_token_is_valid(self):
        self.ensure_one()
        if self.l10n_in_edi_token and self.l10n_in_edi_token_validity > fields.Datetime.now():
            return True
        return False

    def _l10n_in_edi_get_token(self):
        """Override"""
        sudo_company = self.sudo()
        if sudo_company.l10n_in_edi_username and sudo_company._l10n_in_edi_token_is_valid():
            return sudo_company.l10n_in_edi_token
        elif sudo_company.l10n_in_edi_username and sudo_company.l10n_in_edi_password:
            self._l10n_in_edi_authenticate()
            return sudo_company.l10n_in_edi_token
        return False

    def _l10n_in_edi_authenticate(self):
        """Override"""
        params = {"password": self.sudo().l10n_in_edi_password}
        response = self.env['account.edi.format']._l10n_in_edi_connect_to_server(
            self,
            url_path="/iap/l10n_in_edi/1/authenticate",
            params=params
        )
        # validity data-time in Indian standard time(UTC+05:30) convert IST to UTC
        if "data" in response:
            tz = pytz.timezone("Asia/Kolkata")
            local_time = tz.localize(fields.Datetime.to_datetime(response["data"]["TokenExpiry"]))
            utc_time = local_time.astimezone(pytz.utc)
            self.sudo().l10n_in_edi_token_validity = fields.Datetime.to_string(utc_time)
            self.sudo().l10n_in_edi_token = response["data"]["AuthToken"]
        return response
