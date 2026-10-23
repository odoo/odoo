from odoo import api, models
from odoo.addons.iap import jsonrpc
from odoo.exceptions import AccessError

# TODO: Switch to the production endpoint once IAP server is deployed to production.
DEFAULT_IAP_ENDPOINT = 'https://iap-services-test.odoo.com'


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model
    def _l10n_pk_connect_to_server(self, is_production, params, url_path, timeout=30):
        """Connect to Pakistan E-Invoice IAP service.

        Args:
            is_production (bool): Whether to use the production endpoint.
            params (dict): Parameters to send in the request.
            url_path (str): Endpoint path to append to the base URL.
            timeout (int, optional): Timeout in seconds. Defaults to 30.

        Returns:
            dict: Response payload from the IAP service, or an error dict.
        """

        # Ensure params is always a dict
        params = dict(params or {})
        params['is_production'] = is_production
        params['dbuuid'] = self.env['ir.config_parameter'].get_param('database.uuid')

        # Full request URL
        request_url = f'{DEFAULT_IAP_ENDPOINT}{url_path}'

        try:
            # Call IAP service
            return jsonrpc(request_url, params=params, timeout=timeout)
        except AccessError:
            # Return error response
            return self.env['account.move']._l10n_pk_edi_compose_error_response(
                'CONNECTION_ERROR',
                (self.env._(
                    "Access denied while connecting to the E-invoice service. "
                    "Please check your credentials or try again in a moment."
                )),
            )
