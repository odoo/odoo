from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import parse_qs, quote_plus

from odoo.tools import DotDict

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'


class PeppolConnectorCommon(AccountTestInvoicingCommon):

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

    def _mock_create_user(self, success=True):

        def replacement_method(url, **kwargs):
            if success:
                company_id = kwargs['json']['params']['company_id']
                return {
                    'result': {
                        'id_client': PeppolConnectorCommon.forge_id_client(company_id),
                        'refresh_token': 'test_refresh_token'
                    },
                }
            else:
                return self._default_error_code()

        return (
            'https://peppol.test.odoo.com/iap/account_edi/2/create_user',
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

    def _mock_lookup_participant(self, already_exist=False):

        def replacement_method(url, **kwargs):
            if already_exist:
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
            else:
                return {
                    'status_code': 404,
                    'error': {
                        'code': "NOT_FOUND",
                        'message': "no naptr record",
                        'retryable': False,
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
                    return DotDict({**results, 'json': lambda: results, 'raise_for_status': lambda: None})
            self.assertFalse(url, "Missing mock!")

        with patch('requests.get', mock_request), patch('requests.post', mock_request):
            yield mock_results

        self.assertFalse([url for url in mocks if url not in called_urls], "Some mocks defined are not called at all.")
