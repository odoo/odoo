import base64
import io
import zipfile
from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiBatch(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.Batch = cls.env['l10n_pl_edi_batch.download']

    def _create_batch(self, name, content=None):
        return self.Batch.create({
            'name': name,
            'company_id': self.company.id,
            'date_from': '2026-11-01 00:00:00',
            'date_to': '2026-11-08 00:00:00',
            'content': content,
        })

    @freeze_time('2026-11-10 12:00:00')
    def test_date_expiry_from_content(self):
        requested_batch = self._create_batch('requested')
        ready_batch = self._create_batch('ready', {
            'status': {'code': 200},
            # Warsaw time (UTC+1): 13:00 UTC
            'packageExpirationDate': '2026-11-12T14:00:00+01:00',
        })
        expired_batch = self._create_batch('expired', {
            'status': {'code': 200},
            'packageExpirationDate': '2026-11-09T12:00:00+00:00',
        })
        rejected_batch = self._create_batch('rejected', {'status': {'code': 415}})

        self.assertFalse(requested_batch.date_expiry)
        self.assertFalse(requested_batch.is_expired)

        self.assertEqual(ready_batch.date_expiry, datetime(2026, 11, 12, 13, 0, 0))
        self.assertFalse(ready_batch.is_expired)

        self.assertTrue(expired_batch.is_expired)

        batches = requested_batch | ready_batch | expired_batch | rejected_batch
        self.assertEqual(self.Batch.search([('is_expired', '=', True)]) & batches, expired_batch)
        self.assertEqual(self.Batch.search([('is_expired', '=', False)]) & batches, requested_batch | ready_batch | rejected_batch)

    def test_errors_from_content(self):
        ready_batch = self._create_batch('ready', {
            'status': {'code': 200, 'description': "Eksport zakonczony"},
            'package': {'invoiceCount': 3},
        })
        rejected_batch = self._create_batch('rejected', {
            'status': {'code': 415, 'description': "Blad odszyfrowania", 'details': ["Bad key"]},
        })

        # KSeF's own errors come from its answer; a successful batch has none
        self.assertFalse(ready_batch.error)
        self.assertEqual(rejected_batch.error, "415: Blad odszyfrowania\nBad key")

        # Our own errors are written in the same place, with code 999, keeping the rest of the answer
        ready_batch._set_odoo_error("Corrupt ZIP")
        self.assertEqual(ready_batch.state, 'failed')
        self.assertEqual(ready_batch.error, "999: Odoo Error\nCorrupt ZIP")
        self.assertEqual(ready_batch.content['package'], {'invoiceCount': 3})

    def test_kind(self):
        # No frozen time: `create_date` comes from the database clock, which freeze_time doesn't change
        now = fields.Datetime.now()
        historic_batch = self.Batch.create({
            'name': 'historic',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=9),
            'date_to': now - timedelta(days=2),
        })
        today_batch = self.Batch.create({
            'name': 'today',
            'company_id': self.company.id,
            'date_from': now - timedelta(days=1),
            'date_to': now,
        })

        self.assertEqual(historic_batch.kind, 'historic')
        self.assertEqual(today_batch.kind, 'today')
        self.assertEqual(today_batch.retry_count, 0)
        batches = historic_batch | today_batch
        self.assertEqual(self.Batch.search([('kind', '=', 'historic')]) & batches, historic_batch)
        self.assertEqual(self.Batch.search([('kind', '!=', 'historic')]) & batches, today_batch)

    def _add_zip_parts(self, batch, zip_bytes, count=2):
        """ Cut the ZIP in `count` slices, as KSeF does, and store them as downloaded parts. """
        size = -(-len(zip_bytes) // count)
        return self.env['l10n_pl_edi_batch.part'].create([
            {
                'batch_id': batch.id,
                'part_number': number + 1,
                'download_method': 'GET',
                'download_url': f'https://ksef.test/{batch.name}-{number + 1:03}.zip.aes',
                'decrypted_file': base64.b64encode(zip_bytes[number * size:(number + 1) * size]),
            }
            for number in range(count)
        ])

    def test_parts_decrypted_file(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        Part = self.env['l10n_pl_edi_batch.part']
        first_part = self._add_part(ready_batch, 1, downloaded=True)
        second_part = self._add_part(ready_batch, 2, downloaded=False)

        # No attachment exists before the download
        part_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', Part._name),
            ('res_field', '=', 'decrypted_file'),
            ('res_id', 'in', (first_part | second_part).ids),
        ])
        self.assertEqual(len(part_attachments), 1)
        with self.assertRaises(UserError):
            ready_batch.import_bills()

        # The parts' files are attachments of the parts, deleted with them
        ready_batch.unlink()
        self.assertFalse(part_attachments.exists())

    def test_import_bills(self):
        with file_open('l10n_pl_edi/tests/import_xmls/fa3_standard_bill.xml', 'rb') as xml_file:
            xml_content = xml_file.read()
        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, 'w') as zip_file:
            zip_file.writestr('new-ksef-number.xml', xml_content)
            zip_file.writestr('known-ksef-number.xml', xml_content)
            zip_file.writestr('_metadata.json', '{}')

        known_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': self.company.id,
            'l10n_pl_edi_number': 'known-ksef-number',
        })
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, zip_stream.getvalue())
        self.assertEqual(ready_batch.state, 'downloaded')

        bills_before = self.env['account.move'].search([('move_type', '=', 'in_invoice')])
        ready_batch.import_bills()
        new_bill = self.env['account.move'].search([('move_type', '=', 'in_invoice')]) - bills_before

        # One bill for the new KSeF number, with its XML; the known one is skipped
        self.assertEqual(new_bill.l10n_pl_edi_number, 'new-ksef-number')
        self.assertEqual(new_bill.l10n_pl_edi_attachment_id.name, 'new-ksef-number.xml')
        self.assertEqual(new_bill.l10n_pl_edi_attachment_id.raw, xml_content)
        self.assertTrue(known_bill.exists())
        self.assertFalse(ready_batch.part_ids)
        self.assertEqual(ready_batch.state, 'done')

        # Nothing left to import: a second call does nothing
        ready_batch.import_bills()
        self.assertEqual(self.env['account.move'].search([('move_type', '=', 'in_invoice')]) - bills_before, new_bill)

    def test_import_bills_corrupt_zip(self):
        ready_batch = self._create_batch('ready', {'status': {'code': 200}})
        self._add_zip_parts(ready_batch, b'not a zip at all')
        ready_batch.import_bills()
        self.assertEqual(ready_batch.state, 'failed')
        self.assertTrue(ready_batch.error.startswith("999: Odoo Error\nThe KSeF batch ZIP is corrupt"))

    def _add_part(self, batch, number, downloaded):
        values = {
            'batch_id': batch.id,
            'part_number': number,
            'download_method': 'GET',
            'download_url': f'https://ksef.test/part-{number:03}.zip.aes',
        }
        if downloaded:
            values['decrypted_file'] = base64.b64encode(b'decrypted zip slice')
        return self.env['l10n_pl_edi_batch.part'].create(values)

    @freeze_time('2026-11-10 12:00:00')
    def test_state(self):
        ready = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-12T12:00:00+00:00'}
        expired = {'status': {'code': 200}, 'packageExpirationDate': '2026-11-09T12:00:00+00:00'}

        requested_batch = self._create_batch('requested')

        rejected_batch = self._create_batch('rejected', {'status': {'code': 415}})
        odoo_error_batch = self._create_batch('odoo_error', ready)
        odoo_error_batch._set_odoo_error("Corrupt ZIP")
        too_many_retries_batch = self._create_batch('too_many_retries')
        too_many_retries_batch.retry_count = 10
        expired_missing_part_batch = self._create_batch('expired_missing_part', expired)
        self._add_part(expired_missing_part_batch, 1, downloaded=False)

        downloading_batch = self._create_batch('downloading', ready)
        self._add_part(downloading_batch, 1, downloaded=True)
        self._add_part(downloading_batch, 2, downloaded=False)

        downloaded_batch = self._create_batch('downloaded', ready)
        self._add_part(downloaded_batch, 1, downloaded=True)
        # Expiry doesn't matter once all the parts are downloaded
        expired_downloaded_batch = self._create_batch('expired_downloaded', expired)
        self._add_part(expired_downloaded_batch, 1, downloaded=True)

        # Imported, or nothing to download: no parts left
        done_batch = self._create_batch('done', ready)
        empty_batch = self._create_batch('empty', {'status': {'code': 200}, 'package': {'invoiceCount': 0}})

        failed_batches = rejected_batch | odoo_error_batch | too_many_retries_batch | expired_missing_part_batch
        expected_states = {
            'requested': requested_batch,
            'failed': failed_batches,
            'downloading': downloading_batch,
            'downloaded': downloaded_batch | expired_downloaded_batch,
            'done': done_batch | empty_batch,
        }
        batches = self.Batch.union(*expected_states.values())
        for state, expected_batches in expected_states.items():
            for batch in expected_batches:
                self.assertEqual(batch.state, state, batch.name)
            self.assertEqual(self.Batch.search([('state', '=', state)]) & batches, expected_batches, state)
        self.assertEqual(self.Batch.search([('state', 'not in', ['done', 'failed'])]) & batches,
                         requested_batch | downloading_batch | downloaded_batch | expired_downloaded_batch)
