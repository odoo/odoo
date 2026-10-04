import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.urls import urljoin

from odoo.addons.iap import jsonrpc

IAP_SERVICE_NAME = "l10n_id_pajakio_proxy"
DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

# errors returned by the proxy's subscription gate (iap_tools._check_subscription)
SUBSCRIPTION_ERRORS = {
    'error_subscription': "Unable to verify your Odoo subscription. Please try again later.",
    'dbuuid_not_exist': "This database is not linked to any Odoo subscription.",
    'not_enterprise': "Pajak.io requires an Odoo Enterprise subscription.",
    'not_prod_env': "Pajak.io cannot be used from a staging, test or duplicated database.",
    'not_active_db': "Your Odoo subscription is not active. Please renew it to keep using Pajak.io.",
}

_logger = logging.getLogger(__name__)


class IapAccount(models.Model):
    _inherit = "iap.account"

    @api.model
    def _l10n_id_pajakio_iap_connect(self, params, url_path, timeout=30, include_key_identifier=True, include_account_token=False):
        """ Helper method for jsonrpc connection to IAP server """
        user_token = self.sudo().get(IAP_SERVICE_NAME)
        mode, key_identifier, _ = self.env.company._l10n_id_pajakio_get_data()

        # Parameters that has to always be passed for identity verification on IAP side
        params.update({
           "mode": mode,
           "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
        })
        if include_key_identifier:
            params["key_identifier"] = key_identifier
        if include_account_token:
            params["account_token"] = user_token.account_token

        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_id_pajakio.endpoint", DEFAULT_ENDPOINT)
        url = urljoin(endpoint, url_path)

        result = jsonrpc(url, params=params, timeout=timeout)
        _logger.debug("Response from IAP for %s: %s", url_path, result)

        if isinstance(result, dict) and (message := SUBSCRIPTION_ERRORS.get(result.get('error'))):
            raise UserError(message)

        return result
