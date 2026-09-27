# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.iap import jsonrpc


DEFAULT_IAP_TEST_ENDPOINT = "https://iap-services-test.odoo.com/"
IAP_SERVICE_NAME = "l10n_id_pajakio_proxy"


class IapAccount(models.Model):
    _inherit = "iap.account"

    @api.model
    def _l10n_id_pajakio_iap_connect(self, params, url_path, timeout=30):
        """ Helper method to do jsonrpc connection to IAP server """
        user_token = self.get(IAP_SERVICE_NAME)
        # always include dbuuid, client_id and account token for authorizatino
        mode = self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.mode")
        client_id = self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.test_client_id") if mode == "test" \
            else self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.client_id")

        params.update({
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "account_token": user_token.account_token,
            "mode": mode,
            "client_id": client_id,
        })
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.endpoint", DEFAULT_IAP_TEST_ENDPOINT)

        url = "%s%s" % (endpoint, url_path)
        return jsonrpc(url, params=params, timeout=timeout)
