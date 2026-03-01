import logging

from markupsafe import Markup
from requests.exceptions import RequestException

from odoo import api, models
from odoo.tools import LazyTranslate

from odoo.addons.iap import jsonrpc
from odoo.addons.iap.tools.iap_tools import IAPServerError

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

IAP_ERROR_MESSAGE = {
    'error_subscription': _lt("An error has occurred when trying to verify your subscription."),
    'dbuuid_not_exist': _lt("Your database UUID does not exist."),
    'not_enterprise': _lt("You do not have an Odoo Enterprise subscription."),
    'not_prod_env': _lt("Your database is not used for a production environment."),
    'not_active_db': _lt("Your database is not yet activated."),
    'limit_call_reached': _lt("You reached the call limit. Please try again in a moment."),
}


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model
    def _l10n_pk_edi_compose_error_response(self, error_code, message):
        """Prepare a standardized error response."""
        error_response = {
            'error': {
                'code': error_code,
                'message': str(message),
            },
        }

        _logger.error('PK EDI error response: %s', error_response)

        return error_response

    @api.model
    def _l10n_pk_edi_parse_response(self, response):
        """Parse FBR response. Returns dict with status/message/error_response, or None if valid."""

        # Server or connection error
        if error := response.get('error'):
            error_msg = error.get('message', '')
            if authentication_error := error.get('fault'):
                error_msg = authentication_error.get('description')
            if (validation_res := error.get('validationResponse')) and validation_res.get('status') == 'Invalid':
                errors = [validation_res['error']] if validation_res.get('error') else []
                for item in (validation_res.get('invoiceStatuses') or []):
                    if item.get('error'):
                        errors.append(f"- Line {item.get('itemSNo')} {item['error']}")
                error_msg = '<br/>'.join(errors) or error_msg
            return {'status': 'failed', 'message': error_msg, 'error_response': response}

        # Business validation error
        validation = response.get('validationResponse')
        if not validation or validation.get('status') == 'Valid':
            return None

        errors = []
        if validation.get('errorCode') or validation.get('error'):
            errors.append(validation.get('error') or validation.get('errorCode', ''))
        for invoice_status in validation.get('invoiceStatuses') or []:
            if error := invoice_status.get('error'):
                errors.append(error)
        if not errors:
            errors.append(self.env._("The FBR service rejected the invoice without giving a reason."))

        return {
            'status': 'failed',
            'message': Markup('- ') + Markup('<br>- ').join(errors),
            'error_response': self._l10n_pk_edi_compose_error_response(
                'VALIDATION_ERROR', '\n'.join(errors),
            ),
        }

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
        params['dbuuid'] = self.env['ir.config_parameter'].sudo().get_str('database.uuid')
        # get_str() only falls back to the default when the parameter is absent, so an
        # existing-but-empty parameter must be defaulted here too.
        iap_endpoint = (
            self.env['ir.config_parameter'].sudo().get_str('l10n_pk_edi.iap_endpoint')
            or 'https://iap-services.odoo.com'
        )
        request_url = "%s%s" % (iap_endpoint, url_path)
        try:
            result = jsonrpc(request_url, params=params, timeout=timeout)
            raw_error = (result or {}).get('error', {})
            error = raw_error if isinstance(raw_error, dict) else {'message': str(raw_error)}
            code = error.get('code') or error.get('message', '')
            if code in IAP_ERROR_MESSAGE:
                return self._l10n_pk_edi_compose_error_response(
                    code.upper(),
                    IAP_ERROR_MESSAGE[code],
                )
            return result
        except (RequestException, IAPServerError) as e:
            _logger.warning("l10n_pk_edi: could not reach %s: %s", url_path, e)
            return self._l10n_pk_edi_compose_error_response(
                'CONNECTION_ERROR',
                self.env._("Could not connect to the E-invoice service. Please try again in a moment."),
            )
