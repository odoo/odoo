import logging

from markupsafe import Markup
from requests.exceptions import HTTPError

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools import LazyTranslate

from odoo.addons.iap import jsonrpc

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
    def _l10n_pk_edi_compose_error_response(self, error_code=None, message=None):
        """Prepare a standardized error response."""

        error_message = message or self.env._('An unexpected error occurred while processing the request.')
        error_response = {
            'error': {
                'code': error_code or 'INTERNAL_SERVER_ERROR',
                'message': error_message,
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
            if validation_res := error.get('validationResponse'):
                if validation_res.get('status') == 'Invalid':
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
            errors.append(invoice_status['error'])

        return {
            'status': 'rejected',
            'message': Markup('- ') + Markup('<br>- ').join(errors),
            'error_response': self._l10n_pk_edi_compose_error_response('VALIDATION_ERROR', errors),
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
        iap_endpoint = self.env.ref('l10n_pk_edi.l10n_pk_edi_iap_endpoint').value
        if iap_endpoint:
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
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise AccessError(_("Could not connect to the FBR service. Try Again Later")) from e
            raise AccessError(_("Could not connect to the FBR service: %s", e)) from e
        except AccessError:
            return self._l10n_pk_edi_compose_error_response(
                'CONNECTION_ERROR',
                (self.env._('Access denied while connecting to the E-invoice service. Please check your credentials or try again in a moment.')),
            )
