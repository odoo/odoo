import datetime
import requests

from base64 import b64encode
from freezegun import freeze_time
from unittest import mock
from urllib.parse import quote_plus

from odoo import Command
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']
FILE_PATH = 'l10n_fr_pdp/tests/test_files/assets'


class TestL10nFrPdpCommon(TestUblCiiCommon, TestAccountMoveSendCommon):

    @classmethod
    @TestUblCiiCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        cls.env['ir.config_parameter'].sudo().set_param('l10n_fr_pdp.edi.mode', 'test')

        # To avoid blocked requests in the logs
        if cls.env['ir.module.module']._get('account_peppol').state == 'installed':
            not_valid_peppol_verification_state = mock.patch('odoo.addons.account_peppol.models.res_partner.ResPartner._get_peppol_verification_state', return_value='not_valid')
            cls.startClassPatcher(not_valid_peppol_verification_state)

        cls.company_data['company'].write({
            'street': 'Rue Abbé Huet',
            'city': 'Rennes',
            'zip': '35043',
            'vat': 'FR91746948785',
            'siret': '96851575905899',
            'phone': '+33612345678',
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'FR5000400440116243',
            'allow_out_payment': True,
        })

        cls.company_data['company'].partner_id.update({
            'peppol_endpoint': False,
        })

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

        cls.partner_a = cls.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '96851575905823',
            'invoice_edi_format': 'ubl_21_fr',
            'pdp_identifier': '96851575905823',
        })
        cls.partner_b.write({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'phone': '061928374',
            'vat': 'BE0897223670',
            'invoice_edi_format': 'ubl_bis3',
            'peppol_eas': '0208',
            'peppol_endpoint': '0239843188',
            'pdp_identifier': False,

        })

    # -------------------------------------------------------------------------
    # REQUEST HANDLING
    # -------------------------------------------------------------------------

    # We block all requests by default.
    @classmethod
    def _request_handler(cls, s: requests.Session, r: requests.PreparedRequest, /, **kw):
        response = requests.Response()
        response.status_code = 200
        json = {}
        if r.path_url.startswith('/api/peppol/1/lookup') or r.path_url.startswith('/api/pdp/1/peppol_lookup'):
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

    def _create_french_invoice(self, move_type='out_invoice'):
        tax_1 = self.env['account.chart.template'].ref('tva_acq_normale')
        tax_2 = self.env['account.chart.template'].ref('tva_acq_specifique')
        return self.env["account.move"].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_1.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_2.ids)],
                }),
            ],
        })

    def _create_belgian_invoice(self, move_type='out_invoice'):
        # TODO:
        raise NotImplementedError

    @classmethod
    def _send_patched(cls, invoice):
        valid_pdp_verification_state = mock.patch('odoo.addons.l10n_fr_pdp.models.res_partner.ResPartner._get_pdp_verification_state', return_value='valid')
        with valid_pdp_verification_state:
            # The successful verification sets the `invoice_sending_method` to `pdp` on the partner
            wizard = cls.env['account.move.send.wizard'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({})
            wizard.action_send_and_print()
