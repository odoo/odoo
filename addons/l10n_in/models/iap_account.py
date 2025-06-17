from odoo import api, models
from odoo.addons.iap import jsonrpc

DEFAULT_IAP_ENDPOINT = "https://l10n-in-edi.api.odoo.com"
DEFAULT_IAP_TEST_ENDPOINT = "https://l10n-in-edi-demo.api.odoo.com"
IAP_SERVICE_NAME = 'l10n_in_edi'
TEST_GST_NUMBER = '24FANCY1234AAZA'


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model
    def _l10n_in_connect_to_server(self, is_production, params, url_path, config_parameter, timeout=25):
        user_token = self.get(IAP_SERVICE_NAME)
        params.update({
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "account_token": user_token.sudo().account_token,
        })
        if params.get('gstin') == TEST_GST_NUMBER:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_ENDPOINT if is_production else DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param(config_parameter, default_endpoint)
        url = "%s%s" % (endpoint, url_path)
        return jsonrpc(url, params=params, timeout=timeout)
