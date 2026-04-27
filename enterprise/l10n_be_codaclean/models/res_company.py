import re

from odoo import api, fields, models
from odoo.addons.l10n_be_codaclean.tools.iap_api import contact


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_be_codaclean_iap_token = fields.Char(
        string="Codaclean IAP Access Token",
        readonly=True,
        groups="base.group_system",
    )
    l10n_be_codaclean_is_connected = fields.Boolean(
        string="Codaclean Is Connected",
        compute="_compute_l10n_be_codaclean_is_connected",
        store=True,
    )

    @api.depends("l10n_be_codaclean_iap_token")
    def _compute_l10n_be_codaclean_is_connected(self):
        # We just set the field to `False` in case there is no iap token.
        # Setting it to `True` is handled by the API calls
        for company in self:
            if not company.l10n_be_codaclean_iap_token:
                company.l10n_be_codaclean_is_connected = False

    def _l10n_be_codaclean_connect(self, username, password):
        self.ensure_one()
        params = {
            "username": username,
            "password": password,
        }
        result = contact(self.env, "connect", params)

        iap_token = result.get("iap_token")
        self.write({
            'l10n_be_codaclean_iap_token': iap_token,
            'l10n_be_codaclean_is_connected': bool(iap_token),
        })

        return result

    def _l10n_be_codaclean_change_credentials(self, username, password):
        self.ensure_one()
        params = {
            "iap_token": self.sudo().l10n_be_codaclean_iap_token,
            "new_username": username,
            "new_password": password,
        }
        result = contact(self.env, "change_credentials", params)

        self.l10n_be_codaclean_is_connected = result.get("authenticated")

        return result

    def _l10n_be_codaclean_disconnect(self):
        self.ensure_one()
        params = {"iap_token": self.sudo().l10n_be_codaclean_iap_token}
        result = contact(self.env, "disconnect", params)

        if not result.get("error"):
            self.l10n_be_codaclean_iap_token = False

        return result

    def _l10n_be_codaclean_get_formatted_vat(self):
        if self.vat and self.vat != "/":
            vat = self.vat
        else:
            vat = self.company_registry
        digits = re.sub(r"[^0-9]", "", vat or "")
        return re.sub(r"(\d{4})(\d{3})(\d{3})", r"\1.\2.\3", digits)

    def _l10n_be_codaclean_check_status(self):
        self.ensure_one()
        params = {"iap_token": self.sudo().l10n_be_codaclean_iap_token}
        if not params['iap_token']:
            return {}
        result = contact(self.env, "check_status", params)

        # We only update the values on a "successful" connection (so i.e. not on connection errors / timout)
        error = result.get("error", {})
        if not error or error.get("type") in {'codaclean_error_auth', "iap_error_connection_not_found"}:
            result['success'] = True  # The errors give use the definitive information about the status
            if not result.get("connection_exists"):
                self.l10n_be_codaclean_iap_token = False
            self.l10n_be_codaclean_is_connected = result.get("authenticated")

        return result

    def _l10n_be_codaclean_fetch_coda_files(self, date_from, ibans):
        params = {
            "iap_token": self.sudo().l10n_be_codaclean_iap_token,
            "enterprise_number": self._l10n_be_codaclean_get_formatted_vat(),
            "from_date": date_from,
            "ibans": ibans,  # dict: iban → date_from
        }
        result = contact(self.env, "get_coda_files", params, timeout=(10, 900))

        if result.get("error", {}).get("type") == "iap_error_connection_not_found":
            self.l10n_be_codaclean_iap_token = False

        return result
