import logging
from odoo import api, models
from urllib.parse import urljoin
from odoo.addons.iap import jsonrpc

IAP_SERVICE_NAME = "l10n_id_pajakio_proxy"
DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

_logger = logging.getLogger(__name__)
class IapAccount(models.Model):
    _inherit = "iap.account"

    @api.model
    def _l10n_id_pajakio_iap_connect(self, params, url_path, timeout=30):
        """ Helper method for jsonrpc connection to IAP server """
        user_token = self.sudo().get(IAP_SERVICE_NAME)
        mode, client_id, _ = self.env.company._l10n_id_pajakio_get_data()

        # Parameters that has to always be passed for identity verification on IAP side
        params.update({
           "account_token": user_token.account_token,
           "mode": mode,
           "client_id": client_id,
           "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
        })

        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.endpoint", DEFAULT_ENDPOINT)
        url = urljoin(endpoint, url_path)

        result = jsonrpc(url, params=params, timeout=timeout)
        _logger.info("Response from IAP for %s: %s", url_path, result)

        return result
