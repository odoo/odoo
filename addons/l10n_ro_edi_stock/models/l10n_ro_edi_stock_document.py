import markupsafe
import requests
import re

from odoo import api, fields, models, _

DOCUMENT_STATES = [
    ('etransport_sending', "Sending"),
    ('etransport_sending_failed', "Error"),
    ('etransport_sent', 'Sent'),
]

SCHEMATRON_ERROR_ID_PATTERN = r'BR-(?:CL-)?\d{3}'

ETRANSPORT_URLS = {
    'test': 'https://api.anaf.ro/test/ETRANSPORT/ws/v1',
    'prod': 'https://api.anaf.ro/prod/ETRANSPORT/ws/v1'
}


def _cleanup_errors(errors: list[str]):
    def _cleanup_schematron_error(error: str) -> str:
        for part in error.split('; '):
            key, value = part.split('=', maxsplit=1)
            if key == 'textEroare':
                return value.strip()

    return [_cleanup_schematron_error(err) if re.search(SCHEMATRON_ERROR_ID_PATTERN, err) else err.strip() for err in errors]


def _make_etransport_request(company, endpoint: str, method: str, session, data=None):
    api_env = 'test' if company.l10n_ro_edi_test_env else 'prod'
    url = f"{ETRANSPORT_URLS[api_env]}/{endpoint}"
    headers = {
        'Content-Type': 'application/xml',
        'Authorization': f'Bearer {company.l10n_ro_edi_access_token}',
    }

    # encode data to utf-8 because it could contain some Romanian characters that are not part of latin-1
    if data:
        data = data.encode()

    try:
        response = session.request(method=method, url=url, data=data, headers=headers, timeout=10)
    except requests.HTTPError as e:
        return {'error': str(e)}

    match response.status_code:
        case 404:
            return {'error': response.json()['message']}
        case 403:
            return {'error': _("Access token is forbidden.")}
        case 204:
            return {'error': _("You reached the limit of requests. Please try again later.")}

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # For all other possible status_codes, just return the HTTPError
        return {'error': str(e)}

    response_data = response.json()

    if response_data['ExecutionStatus'] == 1:
        errors = _cleanup_errors([error['errorMessage'] for error in response_data['Errors']])
        return {'error': '\n'.join(errors)}

    return {'content': response_data}


class L10nRoEdiStockDocument(models.Model):
    _name = 'l10n_ro.edi.stock.document'
    _description = "Romanian eTransport document"
    _order = 'create_date DESC, id DESC'

    interface_id = fields.Many2one(comodel_name='l10n_ro.edi.stock.etransport.interface')

    state = fields.Selection(selection=DOCUMENT_STATES, string="eTransport Status", required=True, copy=False)
    message = fields.Char(string="Message", copy=False)
    uit = fields.Char(help="UIT of this eTransport document.", copy=False)
    load_id = fields.Char(help="Id of this document used for interacting with the anaf api.", copy=False)

    @api.model
    def _send_etransport_document(self, company, template_data):
        template = self.env['ir.ui.view']._render_template('l10n_ro_edi_stock.l10n_ro_template_etransport', values=template_data)

        cif = company.vat.replace('RO', '')

        return _make_etransport_request(
            company=company,
            endpoint=f'upload/ETRANSP/{cif}/2',
            method='post',
            session=requests,
            data=markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>\n") + template
        )

    @api.model
    def _fetch_etransport_document(self, company, load_id, session):
        return _make_etransport_request(
            company=company,
            endpoint=f'stareMesaj/{load_id}',
            method='get',
            session=session,
        )
