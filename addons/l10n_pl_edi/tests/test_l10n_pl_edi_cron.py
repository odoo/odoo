import secrets
import textwrap
from base64 import b64encode
from datetime import date, datetime

from odoo import fields
from odoo.tests import freeze_time, patch, tagged
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdi
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiCron(TestL10nPlEdi, CronMixinCase):

    @classmethod
    @freeze_time('2026-06-07')
    def setUpClass(cls):
        super().setUpClass()
        cls.historic_date_param_name = f'l10n_pl_edi.last_historic_date_{cls.company.id}'
        cls._ksef_set_bills_date_param('2026-06-07')
        cls.cron = cls.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')
        tb = lambda n: b64encode(secrets.token_bytes(n))
        cls.company.write({'l10n_pl_edi_session_key': tb(32), 'l10n_pl_edi_session_iv': tb(16)})
        cls.company_2.write({
            'l10n_pl_edi_session_key': False,
            'l10n_pl_edi_session_iv': False,
            'l10n_pl_edi_access_token': False,
        })

        service = cls.service = KsefApiService(cls.company)
        cls.batch_number = '10000009'
        cls.content_map = {cls.batch_number: {}}
        parts_content = (b'test1', b'test2')
        for idx, part in enumerate(parts_content, 1):
            filename = f'{cls.batch_number}_part_{idx:03}.aes.zip'
            encrypted_content = service.aes_cbc_content(part, service.raw_symmetric_key, service.raw_iv)
            zipped_content = service.zip_content(encrypted_content, filename)
            cls.content_map[cls.batch_number][filename] = {'content': part, 'zipped_content': zipped_content}

    @classmethod
    def _ksef_set_bills_date_param(cls, date_param):
        if isinstance(date_param, date | datetime):
            date_param = fields.Datetime.to_string(date_param)
        Parameter = cls.env['ir.config_parameter'].sudo()
        Parameter.set_param(cls.historic_date_param_name, date_param)

    @classmethod
    @property
    def _ksef_bills_date_param(cls):
        Parameter = cls.env['ir.config_parameter'].sudo()
        return Parameter.get_param(cls.historic_date_param_name)

    @freeze_time('2026-01-01')
    def test_ksef_download_01_first_pass_status_100(self):
        test = self

        def mock_get_public_keys(self):
            return {
                'token': textwrap.dedent("""\
                    -----BEGIN PUBLIC KEY-----
                    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxsyeiYiWB2+KFxEpQGoN
                    Qa6W8Pc4kWGl8V+sBMdW3Fqh0lhKiqKfpH5RWLDmZ30EzkKJ5+IdaWYFoijhYxDB
                    IBhINVQKlBZvEVd6CfPJUJypa94eRO5cc6IPNI35aMhfKP/Kc4A/OiT2J4nyCz6B
                    V98xOXCAlyDPD73XM6O2ormL6gUb673zvjOIakf39tAPPVgWIDuX7GDZYGebN7LX
                    oGvjPo5YDqC2KN51ofLbO+n74iei5OaGN94Ap52vI7uzK2g/hQslOd0Avl2U1kwR
                    nnF0yzwbDzRrHqPCHUYxVp5nHdo+jHe1CNoa6gt0m6pn1StYcitSXKg2hTNjnes6
                    TQIDAQAB
                    -----END PUBLIC KEY-----
                """),
                'symmetric': textwrap.dedent("""\
                    -----BEGIN PUBLIC KEY-----
                    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxUEDI48g+Pk0izn9XydR
                    evJqtz4h8s4Sz63FvIZvmhdaZfVkmGBqQrBKPTFX6ksQM/gEq1y8nqtmSI6RqoMU
                    gV0UDqIPauyicMiKsfLLPH3ht8bjkeaMB330dxWKCTpJKv+6+LC73i3B1oavWMAA
                    v3is5aWTyyFB9rwjdxcSZ46DSKYaUo5KbWKZTxBNpCT/LqkhHxfbszq+LIWIvm+0
                    9GFpth6hBvDST1h7CHt4g9B1DmtY3I2nYDkPtnmvGo5XBODqTgzWMb0rLgloQGbI
                    eZygQPhhzsWDy4d2uIrE9zZB90q6kDOVg/hZ5YdhCr4X8FeHOfaCgGp+8ZPL3akd
                    uQIDAQAB
                    -----END PUBLIC KEY-----
                """),
            }

        def mock_download_batch_request(self, date_from, date_to, encryption_data, subject_type="Subject1"):
            return {
                'number': test.batch_number,
                'encryption_data': encryption_data,
                'date_from': fields.Datetime.to_string(date_from),
                'date_to': fields.Datetime.to_string(date_to),
            }

        def mock_download_batch_status(self, number, date_from, date_to, encryption_data):
            return {
                'number': number,
                'status': '100',
                'date_from': fields.Datetime.to_string(date_from),
                'date_to': fields.Datetime.to_string(date_to),
                'date_expiry': '2026-09-01 00:00:00',
                'parts': {
                    filename: {
                        'name': filename,
                        'url': f'https://www.odoo.com/ksef_downloads/{filename}',
                        'method': 'GET',
                        'number': idx,
                        'size': len(part_data['zipped_content']),
                        'unencrypted_size': len(part_data['content']),
                        'batch_number': number,
                    }
                    for idx, (filename, part_data) in enumerate(test.content_map[number].items(), 1)
                },
                'encryption_data': encryption_data,
            }

        self._ksef_set_bills_date_param('2026-01-01')
        self.assertFalse(self.env['ir.attachment']._l10n_pl_edi_get_batches())
        with (
            patch.object(KsefApiService, '_get_public_keys', autospec=True, side_effect=mock_get_public_keys),
            patch.object(KsefApiService, 'download_batch_request', autospec=True, side_effect=mock_download_batch_request),
            patch.object(KsefApiService, 'download_batch_status', autospec=True, side_effect=mock_download_batch_status),
            self.capture_triggers(),  # as capt,
        ):
            self.cron.method_direct_trigger()
        self.assertEqual(1, len(self.env['ir.attachment']._l10n_pl_edi_get_batches()))
        self.assertEqual(self._ksef_bills_date_param, '2026-06-07')

    # @freeze_time('2026-06-07')
    # def test_l10n_pl_edi_download_bill_retry_after(self):
    #     """Test that when a rate limit error occurs the progress is preserved and the cron is rescheduled."""

    #     def query_invoice_metadata(query_criteria, page_size=100, page_offset=0):
    #         return {
    #             'hasMore': False,
    #             'invoices': [
    #                 {
    #                     'ksefNumber': 'KSEF-BILL-001',
    #                 },
    #                 {
    #                     'ksefNumber': 'KSEF-BILL-002',
    #                 },
    #             ],
    #         }

    #     call_count = 0

    #     def get_invoice_by_ksef_number(ksef_number):
    #         nonlocal call_count
    #         call_count += 1
    #         if call_count == 1:
    #             path = 'l10n_pl_edi/tests/export_xmls/fa3_bill.xml'
    #             with tools.file_open(path, mode='rb') as file:
    #                 return {'xml_content': file.read()}
    #         return {'error': {'retry_after': 120, 'message': 'Too Many Requests'}}

    #     start = fields.Datetime.now()
    #     with (
    #         patch.object(KsefApiService, 'query_invoice_metadata', side_effect=query_invoice_metadata),
    #         patch.object(KsefApiService, 'get_invoice_by_ksef_number', side_effect=get_invoice_by_ksef_number),
    #         self.capture_triggers() as capt,
    #     ):
    #         cron_runs_before = len(capt.records)
    #         self.env['account.move'].with_company(self.company)._l10n_pl_edi_download_bills_from_ksef()

    #     bill_1 = self.env['account.move'].search([('l10n_pl_edi_status', '=', 'fetched')])
    #     self.assertTrue(bill_1)
    #     bill_1_attachment = self.env['ir.attachment'].search([
    #         ('res_model', '=', 'account.move'),
    #         ('res_id', '=', bill_1.id),
    #     ], limit=1)
    #     self.assertTrue(bill_1_attachment)
    #     with tools.file_open('l10n_pl_edi/tests/export_xmls/fa3_bill.xml', mode='rb') as file:
    #         self.assertEqual(bill_1_attachment.raw, file.read())

    #     bill_2 = self.env['account.move'].search([('l10n_pl_edi_status', '=', 'fetch_ready')])
    #     self.assertTrue(bill_2)

    #     self.assertEqual(len(capt.records), cron_runs_before + 1)
    #     self.assertGreaterEqual(capt.records[-1].call_at, start + timedelta(seconds=120))
    #     self.assertLessEqual(capt.records[-1].call_at, start + timedelta(seconds=240))
