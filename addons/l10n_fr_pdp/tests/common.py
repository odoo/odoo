import requests

from base64 import b64encode
from unittest import mock
from unittest.mock import patch
from urllib.parse import quote_plus

from odoo.tools.misc import file_open

from odoo.addons.l10n_fr_account_ubl_cii.tests.common import TestL10nFrAccountUblCiiCommon


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = [
    'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
    'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz',
    'aaaaaaaa-bbbb-cccc-dddd-dddddddddddd',
]
FILE_PATH = 'l10n_fr_pdp/tests/test_files/assets'


class TestL10nFrPdpCommon(TestL10nFrAccountUblCiiCommon):
    @classmethod
    @TestL10nFrAccountUblCiiCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.totp_secret = 'test'

        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'pdp')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key PDP',
            'content': b64encode(file_open(f'{FILE_PATH}/private_key.pem', 'rb').read()),
        })
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': FAKE_UUID[0],
        })

        cls.startClassPatcher(patch(
            'odoo.addons.l10n_fr_pdp.models.pdp_flow.PdpFlow._get_pdp_proxy_user',
            return_value=False,
        ))

    # -------------------------------------------------------------------------
    # REQUEST HANDLING
    # -------------------------------------------------------------------------

    # We block all requests by default.
    @classmethod
    def _request_handler(cls, s: requests.Session, r: requests.PreparedRequest, /, **kw):
        response = requests.Response()
        response.status_code = 200
        json = {}
        if r.path_url.startswith('/api/peppol/1/lookup') or r.path_url.startswith('/api/pdp/1/lookup'):
            json = {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Blocked Request",
                },
            }
        elif r.path_url.startswith('/api/pdp/1/annuaire_lookup'):
            json = {'in_annuaire': False}
        response.json = lambda: json
        return response

    @classmethod
    def _get_annuaire_lookup_response(cls, peppol_identifier, expected_peppol_identifier):
        response = requests.Response()
        response.status_code = 200
        response.json = lambda: {
            "result": {
                "in_annuaire": peppol_identifier == expected_peppol_identifier,
            }
        }
        return response

    @classmethod
    def _get_peppol_lookup_response(cls, peppol_identifier, expected_peppol_identifier, ubl3_services=True):
        response = requests.Response()
        if peppol_identifier == expected_peppol_identifier:
            url_quoted_peppol_identifier = quote_plus(peppol_identifier)
            response.status_code = 200
            response.json = lambda: {
                "result": {
                    "identifier": peppol_identifier,
                    "smp_base_url": "http://example.com/smp",
                    "ttl": 60,
                    "service_group_url": f"http://example.com/smp/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}",
                    "services": [
                            {
                                "href": f"http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1",
                                "document_id": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
                            },
                        ] if ubl3_services else [],
                }
            }
        else:
            response.status_code = 404
            response.json = lambda: {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "no naptr record",
                    "retryable": False,
                },
            }
        return response

    # -------------------------------------------------------------------------
    # ACCOUNTING HELPERS
    # -------------------------------------------------------------------------
    @classmethod
    def _send_patched(cls, invoice):
        valid_peppol_verification_state = mock.patch('odoo.addons.l10n_fr_pdp.models.res_partner.ResPartner._get_peppol_verification_state', return_value='valid')
        with valid_peppol_verification_state:
            # The successful verification sets the `invoice_sending_method` to `peppol` on the partner
            wizard = cls.env['account.move.send.wizard'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({})
            wizard.action_send_and_print()
