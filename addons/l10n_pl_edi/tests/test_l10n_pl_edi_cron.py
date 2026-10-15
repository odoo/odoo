import io
import json
import secrets
import textwrap
import zipfile
from base64 import b64encode as b64
from contextlib import contextmanager
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import ANY

from odoo import fields, tools
from odoo.tests import freeze_time, patch, tagged
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.l10n_pl_edi.models.account_move import AccountMove, KSEF_FIRST_DAY, KSEF_WINDOW
from odoo.addons.l10n_pl_edi.models.ir_attachment import IrAttachment
from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdi
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService, KSeFRateLimitError


def first_call_args(mock):
    return mock.call_args[0][-1]


def autospatch(*args, **kwargs):
    return patch.object(*args, **kwargs, autospec=True)


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiCron(TestL10nPlEdi, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = KsefApiService(cls.company)
        cls.historic_date_param_name = f'l10n_pl_edi.last_historic_date_{cls.company.id}'
        cls._ksef_set_bills_date_param('2026-06-07')
        cls.cron = cls.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

        key, iv = cls._create_encryption_pair()
        key64, iv64 = (b64(x) for x in (key, iv))
        cls.encryption_data = {'raw_symmetric_key': key64, 'raw_iv': iv64}
        cls.company.write({'l10n_pl_edi_session_key': key64, 'l10n_pl_edi_session_iv': iv64})
        cls.company_2.write({
            k: False
            for k in ('l10n_pl_edi_session_key', 'l10n_pl_edi_session_iv', 'l10n_pl_edi_access_token')
        })

        cls.batch_number = '10000009'

        path = 'l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml'
        with tools.file_open(path, mode='rb') as file:
            cls.xml_content = file.read()

        inner_zip_buffer = io.BytesIO()
        with zipfile.ZipFile(inner_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('fa3_standard_bill.xml', cls.xml_content)

        cls.unencrypted_zip_content = inner_zip_buffer.getvalue()
        cls.encrypted_payload = cls.service.aes_cbc_content(cls.unencrypted_zip_content, key, iv)
        cls.content_map = {cls.batch_number: cls._create_parts_dict(cls.encrypted_payload)}

    @classmethod
    def _create_encryption_pair(cls):
        return secrets.token_bytes(32), secrets.token_bytes(16)

    @classmethod
    def _create_parts_dict(cls, content, batch_number=None, is_encrypted=True):
        """Generates raw metadata dictionaries for mocking KSeF batch status payloads."""
        half_len = len(content) // 2
        batch_number = batch_number or cls.batch_number
        suffix = '.aes' if is_encrypted else ''

        return {
            f'{name}{suffix}': {
                'company_id': cls.company.id,
                'name': name,
                'raw': part_bytes,
                'content': part_bytes,
            }
            for idx, part_bytes in enumerate([content[:half_len], content[half_len:]], 1)
            if (name := f'{batch_number}_part_{idx:03}.zip')
        }

    def _create_part_attachments(self, content, batch_number=None, is_encrypted=True):
        """Creates actual ir.attachment records in the database from binary content."""
        parts_dict = self._create_parts_dict(content, batch_number=batch_number, is_encrypted=is_encrypted)
        orm_vals = [v for _k, v in parts_dict.items() if v.pop('content', True)]
        return self.env['ir.attachment'].create(orm_vals)

    def _create_batch(self, batch_number, batch_status):
        batch_status_json = json.dumps(batch_status, indent=4)
        return self.env['ir.attachment']._l10n_pl_edi_create_batch(batch_number, batch_status_json)

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

    def mock_get_public_keys(self, *args, **kwargs):
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

    def mock_download_batch_request(self, *args, **kwargs):
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        encryption_data = kwargs.get('encryption_data')
        return {
            'number': self.batch_number,
            'encryption_data': encryption_data,
            'date_from': fields.Datetime.to_string(date_from),
            'date_to': fields.Datetime.to_string(date_to),
        }

    def mock_download_batch_status(self, *args, **kwargs):
        _obj, company, number, date_from, date_to, encryption_data, *rest = args
        status = kwargs.get('status', 100) if not rest else rest[0]
        return {
            'number': number,
            'company_id': company.id,
            'status': status,
            'date_from': fields.Datetime.to_string(date_from),
            'date_to': fields.Datetime.to_string(date_to),
            'date_expiry': '2026-09-01 00:00:00',
            'parts': {
                filename: {
                    'name': filename,
                    'url': f'https://www.odoo.com/ksef_downloads/{filename}',
                    'method': 'GET',
                    'number': idx,
                    'size': len(part_data['raw']),
                    'unencrypted_size': len(part_data['content']),
                    'batch_number': number,
                    'company_id': company.id,
                }
                for idx, (filename, part_data) in enumerate(self.content_map[number].items(), 1)
            },
            'encryption_data': encryption_data,
        }

    @contextmanager
    def mock_all(self, status=100):
        def mock_status(*args, **kwargs):
            kwargs['status'] = status
            return self.mock_download_batch_status(*args, **kwargs)
        with (
            autospatch(KsefApiService, '_get_public_keys', side_effect=self.mock_get_public_keys),
            autospatch(KsefApiService, 'download_batch_request', side_effect=self.mock_download_batch_request),
            autospatch(KsefApiService, 'download_batch_status', side_effect=mock_status) as patched_status,
            patch('time.sleep') as patched_sleep,
            self.capture_triggers(),
        ):
            self.patched_status = patched_status
            self.patched_sleep = patched_sleep
            yield

    def test_ksef_daily_cron_pending(self):
        with self.mock_all():
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_bills()
            self.assertEqual(self.patched_status.call_count, 5)
            self.assertEqual(self.patched_sleep.call_count, 4)
            batches = self.env['ir.attachment'].search([('name', 'ilike', 'ksef_batch_%')])
            self.assertFalse(batches)

    def test_ksef_daily_cron_success(self):
        with (
            self.mock_all(status=200),
            autospatch(self.env.registry['account.move'], '_l10n_pl_edi_trigger') as mock_trigger,
        ):
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_bills()
            self.assertEqual(self.patched_status.call_count, 1)
            self.assertEqual(self.patched_sleep.call_count, 0)
            batch = self.env['ir.attachment'].search([('name', 'ilike', f'ksef_batch_{self.batch_number}%')])
            self.assertTrue(batch)
            mock_trigger.assert_called_once_with(ANY, 'l10n_pl_edi.cron_l10n_pl_edi_download_batches')

    def test_ksef_rate_limit_rescheduling(self):
        rate_limit_error = KSeFRateLimitError("Rate limited")
        rate_limit_error.retry_after = delay = 67
        with (
            autospatch(AccountMove, '_l10n_pl_edi_request_bills', side_effect=rate_limit_error),
            autospatch(AccountMove, '_l10n_pl_edi_trigger') as mock_trigger
        ):
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_bills()
            mock_trigger.assert_called_once_with(ANY, 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills', delay)

    @freeze_time('2026-06-07')
    def test_ksef_historic_cron_window(self):
        initial_date = fields.Date.from_string(self._ksef_bills_date_param)
        with (
            self.mock_all(status=200),
            autospatch(AccountMove, '_l10n_pl_edi_trigger') as mock_trigger,
        ):
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_historic_bills()
            new_date = fields.Date.from_string(self._ksef_bills_date_param)
            self.assertEqual(new_date, initial_date + relativedelta(days=-KSEF_WINDOW))
            self.assertTrue(self.env['ir.attachment'].search([
                ('name', 'ilike', f'ksef_batch_{self.batch_number}.json')
            ]))
            mock_trigger.assert_called_once_with(ANY, 'l10n_pl_edi.cron_l10n_pl_edi_download_batches')

    def test_ksef_historic_cron_limit(self):
        self._ksef_set_bills_date_param(KSEF_FIRST_DAY)
        with autospatch(AccountMove, '_l10n_pl_edi_request_bills') as mock_request:
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_historic_bills()
            mock_request.assert_not_called()

    @freeze_time('2026-06-07')
    def test_ksef_vacuum_expired_batches(self):
        expired, regular = [
            self._create_batch(name, {
                'number': name,
                'date_expiry': date_expiry,
                'date_to': '2026-05-20',
            })
            for name, date_expiry in [
                ('expired_123', '2026-06-01 00:00:00'),
                ('regular_124', '2026-10-10 00:00:00'),
            ]
        ]
        self.assertEqual(len((expired | regular).exists()), 2)
        with autospatch(AccountMove, '_l10n_pl_edi_request_bills'):
            self.env['account.move'].sudo()._cron_l10n_pl_edi_ksef_download_historic_bills()
        self.assertFalse(expired.exists())
        self.assertTrue(regular.exists())

    def test_ksef_download_batches_success(self):
        batch = self._create_batch('batch_to_download', {
            'number': 'batch_to_download',
            'date_to': '2026-06-01',
            'parts': {}
        })

        with (
            patch.object(IrAttachment, '_l10n_pl_edi_download_parts', autospec=True) as mock_download,
            patch.object(AccountMove, '_l10n_pl_edi_trigger', autospec=True) as mock_trigger,
        ):
            self.env['account.move'].sudo()._cron_l10n_pl_edi_download_batches()
            mock_download.assert_called_once()
            self.assertFalse(batch.exists())
            mock_trigger.assert_called_once_with(ANY, 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

    def test_ksef_batch_downloader_priority(self):
        batches = {
            name: self._create_batch(name, {'number': name, 'date_to': date_to, 'parts': {}})
            for name, date_to in [('batch_old', '2026-05-01'), ('batch_new', '2026-06-10'), ('batch_middle', '2026-06-01')]
        }
        with (
            autospatch(IrAttachment, '_l10n_pl_edi_download_parts') as mock_download,
            autospatch(AccountMove, '_l10n_pl_edi_trigger') as mock_trigger,
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_batches()
            for name, batch in batches.items():
                self.assertEqual(name != 'batch_new', bool(batch.exists()))
            self.assertEqual(first_call_args(mock_download)['number'], 'batch_new')
            mock_trigger.assert_called_once()
            self.assertEqual(first_call_args(mock_trigger), 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

    def test_ksef_batch_download_and_import(self):
        part_attachment, decompressed_attachment = self.env['ir.attachment'].create([{
            'name': '12345_part_001.zip.aes',
            'raw': b'dummy',
        }, {
            'name': 'invoice.xml',
            'raw': self.xml_content,
        }])
        with (
            autospatch(IrAttachment, '_l10n_pl_edi_get_parts', return_value={'12345': part_attachment}),
            autospatch(IrAttachment, '_l10n_pl_edi_decompress', return_value=decompressed_attachment),
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_batches()
            move = self.env['account.move'].browse(decompressed_attachment.res_id)
            self.assertTrue(move.exists())
            self.assertRecordValues(move, [{
                'company_id': self.company.id,
                'move_type': 'in_invoice',
                'l10n_pl_edi_attachment_id': decompressed_attachment.id,
            }])
            self.assertRecordValues(decompressed_attachment, [{
                'company_id': self.company.id,
                'description': 'KSeF Received Bill XML',
                'res_model': 'account.move',
                'res_id': move.id,
                'res_field': 'l10n_pl_edi_attachment_file',
            }])
            self.assertIn(decompressed_attachment, move.message_main_attachment_id | move.message_ids.attachment_ids)

    def test_ksef_import_waiting(self):
        self._create_batch('12345', {
            'number': '12345',
            'date_to': '2026-06-01',
            'parts': {}
        })
        part_attachment = self.env['ir.attachment'].create({
            'name': '12345_part_001.zip.aes',
            'raw': b'dummy',
        })
        moves_count_before = self._count_moves()
        with (
            autospatch(IrAttachment, '_l10n_pl_edi_download_parts'),
            autospatch(IrAttachment, '_l10n_pl_edi_get_parts', return_value={'12345': part_attachment}),
            autospatch(IrAttachment, '_l10n_pl_edi_decompress') as mock_decompress,
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_batches()
            mock_decompress.assert_not_called()
            self.assertEqual(self._count_moves(), moves_count_before)

    def _count_moves(self):
        move_domain = [('company_id', '=', self.company.id), ('move_type', '=', 'in_invoice')]
        return self.env['account.move'].search_count(move_domain)

    def test_ksef_duplicate_prevention(self):
        ksef_id = '1234567890-12345678-1234567-12'
        existing_move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': ksef_id,
        })
        existing_attachment = self.env['ir.attachment'].create({
            'name': f'{ksef_id}.xml',
            'raw': b'<xml></xml>',
            'company_id': self.company.id,
            'res_model': 'account.move',
            'res_id': existing_move.id,
        })
        existing_move.l10n_pl_edi_attachment_id = existing_attachment.id
        moves_count_before = self._count_moves()
        part_attachment = self.env['ir.attachment'].create({
            'name': '12345_part_001.zip.aes',
            'raw': b'dummy',
        })
        empty_attachment_recordset = self.env['ir.attachment']
        with (
            autospatch(IrAttachment, '_l10n_pl_edi_get_parts', return_value={'12345': part_attachment}),
            autospatch(IrAttachment, '_l10n_pl_edi_decompress', return_value=empty_attachment_recordset) as mock_decompress,
        ):
            self.env['account.move']._cron_l10n_pl_edi_download_batches()
            mock_decompress.assert_called_once()
            self.assertEqual(self._count_moves(), moves_count_before)

    def test_ksef_actual_decompression(self):
        single_zip_attachment = self.env['ir.attachment'].create({
            'name': f'{self.batch_number}_part_001.zip',
            'raw': self.unencrypted_zip_content,
            'company_id': self.company.id,
        })
        extracted_attachments = single_zip_attachment._l10n_pl_edi_decompress()
        self.assertTrue(extracted_attachments)
        self.assertEqual(len(extracted_attachments), 1)
        self.assertEqual(extracted_attachments.name, 'fa3_standard_bill.xml')
        self.assertEqual(extracted_attachments.raw, self.xml_content)

    def test_ksef_multipart_decompression(self):
        part_attachments = self._create_part_attachments(
            self.unencrypted_zip_content,
            is_encrypted=False,
        )
        self.assertEqual(len(part_attachments), 2)
        extracted_attachments = part_attachments._l10n_pl_edi_decompress()
        self.assertTrue(extracted_attachments)
        self.assertEqual(len(extracted_attachments), 1)
        self.assertRecordValues(extracted_attachments, [{
            'name': 'fa3_standard_bill.xml',
            'mimetype': 'application/xml',
            'company_id': self.company.id,
        }])
        self.assertEqual(extracted_attachments.raw, self.xml_content)
        self.assertFalse(part_attachments.exists())

    def test_ksef_download_decrypt_and_decompress(self):
        class MockResponseStream:
            def __init__(self, raw_data, chunk_size=128):
                self.raw_data = raw_data
                self.chunk_size = chunk_size

            def iter_content(self, chunk_size=None):
                size = chunk_size or self.chunk_size
                for i in range(0, len(self.raw_data), size):
                    yield self.raw_data[i:i + size]

        mock_stream = MockResponseStream(self.encrypted_payload)
        decrypted_bytes = b''.join(
            self.env['ir.attachment']._l10n_pl_edi_decrypt_stream(mock_stream, self.encryption_data)
        )
        part_attachments = self._create_part_attachments(decrypted_bytes, is_encrypted=False)
        extracted_attachments = part_attachments._l10n_pl_edi_decompress()
        self.assertRecordValues(extracted_attachments, [{'name': 'fa3_standard_bill.xml', 'raw': self.xml_content}])
        self.assertFalse(part_attachments.exists())
