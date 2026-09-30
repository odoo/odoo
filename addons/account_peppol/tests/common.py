import requests

from contextlib import contextmanager
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, quote_plus

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'


class PeppolConnectorCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

    @staticmethod
    def forge_id_client(company_id):
        id_str = str(company_id).rjust(len(ID_CLIENT.split('x')) - 1, '0')
        new_id_client_blocks = []
        index = 0
        for block in ID_CLIENT.split('-'):
            new_id_client_blocks.append(id_str[index:index + len(block)])
            index += len(block)
        return '-'.join(new_id_client_blocks)

    def _default_error_code(self):
        return {'error': {'code': "spoutch", 'message': "failure"}}

    def _empty_result_or_error(self, success=True):
        if success:
            return {'result': {}}
        else:
            return self._default_error_code()

    def _mock_can_connect(self, with_auth=False):
        def replacement_method(url, **kwargs):
            auth_vals = {
                'available_auths': {
                    'itsme': {'authorization_url': 'test_authorization_url'},
                },
            } if with_auth else {}
            return {
                'auth_required': with_auth,
                **auth_vals,
            }

        return (
            'https://peppol.test.odoo.com/api/peppol/2/can_connect',
            replacement_method,
        )

    def _mock_connect(self, success=True, peppol_state='smp_registration', id_client='test_id_client'):
        def replacement_method(url, **kwargs):
            if peppol_state == 'rejected':
                return {
                    'status_code': 403,
                    'code': 201,
                    'message': 'Unable to register, please contact our support team at peppol.support@odoo.com.'
                }
            if success:
                return {'id_client': id_client, 'refresh_token': 'test_refresh_token', 'peppol_state': peppol_state}
            else:
                return {
                    'status_code': 401,
                    'code': 208,
                    'message': 'The Authentication failed',
                }

        return (
            'https://peppol.test.odoo.com/api/peppol/2/connect',
            replacement_method,
        )

    def _mock_register_sender(self, success=True):
        return (
            'https://peppol.test.odoo.com/api/peppol/1/register_sender',
            lambda url, **kwargs: self._empty_result_or_error(success=success),
        )

    def _mock_register_sender_as_receiver(self, success=True):
        return (
            'https://peppol.test.odoo.com/api/peppol/1/register_sender_as_receiver',
            lambda url, **kwargs: self._empty_result_or_error(success=success),
        )

    def _mock_lookup_participant(self, already_exists=False):

        def replacement_method(url, **kwargs):
            if not already_exists:
                return {
                    'status_code': 404,
                    'error': {
                        'code': "NOT_FOUND",
                        'message': "no naptr record",
                        'retryable': False,
                    },
                }
            else:
                peppol_identifier = parse_qs(url.rsplit('?')[1])['peppol_identifier'][0]
                return {
                    'ok': True,
                    'result': {
                        "identifier": peppol_identifier,
                        "smp_base_url": "http://example.com/smp",
                        "ttl": 60,
                        "service_group_url": "http://example.com/smp/iso6523-actorid-upis%3A%3A" + quote_plus(peppol_identifier),
                        "services": [],
                    },
                }

        return (
            'https://peppol.test.odoo.com/api/peppol/1/lookup',
            replacement_method,
        )

    def _mock_participant_status(self, peppol_state, exists=True):

        def replacement_method(url, **kwargs):
            assert peppol_state
            if exists:
                return {
                    'result': {
                        'peppol_state': peppol_state,
                    },
                }
            else:
                return {
                    'result': {
                        'error': {
                            'code': "client_gone",
                            'message': "Your registration for this service is no longer valid. "
                                       "If you see this message, please update the related Odoo app. "
                                       "You will then be able to re-register if needed.",
                        }
                    },
                }

        return (
            'https://peppol.test.odoo.com/api/peppol/2/participant_status',
            replacement_method,
        )

    def _mock_cancel_peppol_registration(self, success=True):
        return (
            'https://peppol.test.odoo.com/api/peppol/1/cancel_peppol_registration',
            lambda url, **kwargs: self._empty_result_or_error(success=success),
        )

    def _mock_get_all_documents(self, success=True):
        return (
            'https://peppol.test.odoo.com/api/peppol/1/get_all_documents',
            lambda url, **kwargs: self._empty_result_or_error(success=success),
        )

    def _mock_update_user(self, success=True):
        return (
            'https://peppol.test.odoo.com/api/peppol/1/update_user',
            lambda url, **kwargs: self._empty_result_or_error(success=success),
        )

    @contextmanager
    def _mock_requests(self, mocks_methods):
        mocks = dict(mocks_methods)
        called_urls = set()
        mock_results = {'called': {}}

        def mock_request(url, **kwargs):
            for mocked_url, replacement_method in mocks.items():
                if url.startswith(mocked_url):
                    called_urls.add(mocked_url)
                    mock_results['called'][mocked_url] = {
                        'url': url,
                        'kwargs': kwargs,
                    }
                    results = replacement_method(url, **kwargs)
                    mocked_request = Mock()
                    mocked_request.status_code = results.get('status_code', 200)
                    results.pop('status_code', None)
                    if not (200 <= mocked_request.status_code < 300):
                        mocked_request.raise_for_status.side_effect = requests.exceptions.HTTPError()
                    mocked_request.json.return_value = results
                    return mocked_request
            self.assertFalse(url, "Missing mock!")

        def mock_request_2(method, url, **kwargs):
            return mock_request(url, **kwargs)

        with patch('requests.get', mock_request), patch('requests.post', mock_request), patch('requests.request', mock_request_2):
            yield mock_results

        self.assertFalse([url for url in mocks if url not in called_urls], "URLs mocked but not called")
