import logging

import requests


E_INVOO_API_URL = 'https://e-invoo.com/aade/api'
E_INVOO_TEST_API_URL = 'https://test.e-invoo.com/aade/api'
E_INVOO_TIMEOUT = (5, 30)

_logger = logging.getLogger(__name__)


class EInvooRequestError(Exception):
    pass


class EInvooAuthenticationError(EInvooRequestError):
    pass


def _prepare_response(response):
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


def _post(api_token, endpoint, test_env, **request_kwargs):
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
            **request_kwargs,
        )
    except requests.RequestException as error:
        _logger.warning("e-invoo request to %s failed", endpoint)
        raise EInvooRequestError from error

    result = _prepare_response(response)
    provider_response = result.get('response')
    if (
        isinstance(provider_response, dict)
        and provider_response.get('success') is False
        and provider_response.get('error') == 'Invalid API token'
    ):
        _logger.warning("e-invoo rejected the API token on %s", endpoint)
        raise EInvooAuthenticationError

    return result


def issue_invoice(
    api_token,
    *,
    test_env,
    xml,
    invoice_name,
    invoice_amount_total,
    invoice_datetime,
    invoice_id,
    invoice_currency=None,
    issue_date=None,
):
    form_values = {
        'send_action': 'post_invoices',
        'xml': xml,
        'invoice_name': invoice_name,
        'invoice_amount_total': invoice_amount_total,
        'invoice_datetime': invoice_datetime,
        'move_id': invoice_id,
    }
    if invoice_currency:
        form_values['invoice_currency'] = invoice_currency
    if issue_date:
        form_values['issue_date'] = issue_date

    return _post(
        api_token,
        endpoint='send_invoice',
        test_env=test_env,
        files={key: (None, str(value)) for key, value in form_values.items()},
    )


def upload_final_pdf(api_token, *, test_env, invoice_id, parent_token, pdf_b64):
    return _post(
        api_token,
        endpoint='save_invoice_fpdf',
        test_env=test_env,
        json={
            'invoice_id': invoice_id,
            'parent_token': parent_token,
            'pdf_b64': pdf_b64,
        },
    )
