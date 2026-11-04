import logging
import requests

from odoo import models
from odoo.tools import LazyTranslate
from odoo.addons.l10n_gr_edi_e_invoo_bridge.exceptions import EInvooAuthenticationError, EInvooRequestError

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

E_INVOO_API_URL = 'https://e-invoo.com/aade/api'
E_INVOO_TEST_API_URL = 'https://test.e-invoo.com/aade/api'
E_INVOO_TIMEOUT = (5, 30)

E_INVOO_TOKEN_NOT_SET = _lt("The Methodoos API token is not configured.")


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_gr_edi_get_pre_error_dict(self):
        # EXTENDS 'l10n_gr_edi'
        errors = super()._l10n_gr_edi_get_pre_error_dict()
        if self.is_sale_document(include_receipts=True) and not self.company_id.sudo().l10n_gr_edi_methodoos_api_token:
            errors['l10n_gr_edi_missing_methodoos_token'] = {
                'message': str(E_INVOO_TOKEN_NOT_SET),
                'action_text': self.env._("View Settings"),
                'action': {
                    'name': self.env._("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#l10n_gr_edi_aade_settings',
                },
            }
        return errors

    def _l10n_gr_edi_format_e_invoo_response(self, response):
        result = {
            'upstream_status': response.status_code,
            'response': None,
        }

        if not response.content:
            return result
        try:
            result['response'] = response.json()
        except ValueError:
            pass

        return result

    def _l10n_gr_edi_post_e_invoo(self, api_token, endpoint, test_env, json=None, files=None):
        base_url = E_INVOO_TEST_API_URL if test_env else E_INVOO_API_URL
        try:
            response = requests.post(
                f'{base_url}/{endpoint}',
                headers={
                    'Authorization': f'Bearer {api_token}',
                    'Accept': 'application/json',
                },
                timeout=E_INVOO_TIMEOUT,
                allow_redirects=False,
                json=json,
                files=files,
            )
        except requests.RequestException as error:
            _logger.warning("e-invoo request to %s failed - %s", endpoint, error)
            raise EInvooRequestError from error

        result = self._l10n_gr_edi_format_e_invoo_response(response)
        provider_response = result.get('response')
        if (
            isinstance(provider_response, dict)
            and provider_response.get('success') is False
            and 'invalid api token' in (error_message := provider_response.get('error') or '').lower()
        ):
            _logger.warning("e-invoo rejected the API token on %s - %s", endpoint, error_message)
            raise EInvooAuthenticationError

        return result

    def _l10n_gr_edi_issue_invoice(self, api_token, test_env, request_values):
        form_values = {
            'send_action': 'post_invoices',
            'xml': request_values['xml'],
            'invoice_name': request_values['invoice_name'],
            'invoice_amount_total': request_values['invoice_amount_total'],
            'invoice_datetime': request_values['invoice_datetime'],
            'move_id': request_values['invoice_id'],
        }
        if invoice_currency := request_values.get('invoice_currency'):
            form_values['invoice_currency'] = invoice_currency
        if issue_date := request_values.get('issue_date'):
            form_values['issue_date'] = issue_date

        return self._l10n_gr_edi_post_e_invoo(
            api_token,
            endpoint='send_invoice',
            test_env=test_env,
            files={key: (None, str(value)) for key, value in form_values.items()},
        )

    def _l10n_gr_edi_send_invoices(self):
        # OVERRIDE 'l10n_gr_edi_e_invoo'
        """Send customer invoices individually through Methodoos."""
        for company, invoices in self.grouped('company_id').items():
            api_token = company.sudo().l10n_gr_edi_methodoos_api_token
            if not api_token:
                error_message = str(E_INVOO_TOKEN_NOT_SET)
                for invoice in invoices:
                    invoice._l10n_gr_edi_create_error_document({'error': error_message})
                continue

            for invoice in invoices:
                submission = invoice._l10n_gr_edi_prepare_invoice_submission()
                if not submission:
                    continue

                document, request_values = submission
                try:
                    result = self._l10n_gr_edi_issue_invoice(
                        api_token,
                        test_env=company.l10n_gr_edi_test_env,
                        request_values=request_values,
                    )
                except EInvooAuthenticationError as e:
                    document.write({
                        'state': 'invoice_error',
                        'message': str(e),
                    })
                except EInvooRequestError as e:
                    document.message = str(e)
                else:
                    invoice._l10n_gr_edi_handle_invoice_proxy_result(document, result)

                if self._can_commit():
                    self.env.cr.commit()
