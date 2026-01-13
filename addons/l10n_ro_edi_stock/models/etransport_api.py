from json import JSONDecodeError
import requests
import re

from odoo import _


SCHEMATRON_ERROR_ID_PATTERN = r'BR-(?:CL-)?\d{3}'

ETRANSPORT_URLS = {
    'test': 'https://api.anaf.ro/test/ETRANSPORT/ws/v1',
    'prod': 'https://api.anaf.ro/prod/ETRANSPORT/ws/v1'
}


def _cleanup_errors(errors: list[str]) -> list[str]:
    def _cleanup_schematron_error(error: str) -> str:
        for part in error.split('; '):
            key, value = part.split('=', maxsplit=1)
            if key == 'textEroare':
                return value.strip()

    return [_cleanup_schematron_error(err) if re.search(SCHEMATRON_ERROR_ID_PATTERN, err) else err.strip() for err in errors]


class ETransportAPI:
    def get_status(self, company_id, document_load_id, session=None):
        return self._make_etransport_request(
            company=company_id,
            endpoint=f'stareMesaj/{document_load_id}',
            method='get',
            session=session,
        )

    def upload_data(self, company_id, data):
        cif = company_id.vat.replace('RO', '')
        return self._make_etransport_request(
            company=company_id,
            endpoint=f'upload/ETRANSP/{cif}/2',
            method='post',
            data=data,
        )

    def _make_etransport_request(self, company, endpoint: str, method: str, session=None, data=None) -> dict:
        api_env = 'test' if company.l10n_ro_edi_test_env else 'prod'
        url = f"{ETRANSPORT_URLS[api_env]}/{endpoint}"
        headers = {
            'Content-Type': 'application/xml',
            'Authorization': f'Bearer {company.l10n_ro_edi_access_token}',
        }

        # encode data to utf-8 because it could contain some Romanian characters that are not part of latin-1
        if data:
            data = data.encode()

        if not session:
            session = requests.Session()

        response = session.request(method=method, url=url, data=data, headers=headers, timeout=10)

        match response.status_code:
            case 404:
                return {'error': response.json()['message']}
            case 403:
                return {'error': _("Access token is forbidden.")}
            case 204:
                return {'error': _("You reached the limit of requests. Please try again later.")}

        try:
            response_data = response.json()
        except JSONDecodeError as e:
            return {'error': str(e)}

        if response_data['ExecutionStatus'] == 1:
            errors = _cleanup_errors([error['errorMessage'] for error in response_data['Errors']])
            return {'error': '\n'.join(errors)}

        return {'content': response_data}
